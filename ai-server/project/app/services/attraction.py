from typing import Dict, Any, List
from langchain_core.prompts import PromptTemplate
from langchain_core.tracers.context import collect_runs
from .base import BaseService
import re


class AttractionService(BaseService):
    def __init__(
        self,
        use_reranker: bool = True,
        use_hybrid: bool = True,
        hybrid_alpha: float = 0.8,
        initial_k: int = 20,
        final_k: int = 20
    ):
        """
        관광지 검색 서비스 초기화

        Args:
            use_reranker (bool): Reranker 사용 여부
            use_hybrid (bool): 하이브리드 검색(TMM-CC) 사용 여부
            hybrid_alpha (float): 하이브리드 검색 알파 값 (0.0~1.0, 기본값 0.8)
            initial_k (int): 초기 검색 문서 수
            final_k (int): 최종 반환 문서 수
        """
        print(f"관광지 서비스 초기화: use_reranker={use_reranker}, use_hybrid={use_hybrid}, hybrid_alpha={hybrid_alpha}")
        super().__init__(
            vectordb_name="attraction_finder",
            use_reranker=use_reranker,
            use_hybrid=use_hybrid,
            hybrid_alpha=hybrid_alpha,
            initial_k=initial_k,
            final_k=final_k
        )
        print(f"관광지 서비스 초기화 완료")

        self.template = """
        당신은 어트랙션 추천 AI입니다. 주어진 맥락을 바탕으로 사용자의 질문에 답변해주세요.

        다음은 어트랙션에 대한 정보입니다:
        {attraction_info}

        사용자 질문: {user_request}

        다음 지침을 따라 답변해주세요:
        1. 각 어트랙션의 이름을 정확히 큰따옴표로 감싸서 언급해주세요. (예: "모두를 위한 부산여행")
        2. 각 어트랙션의 주요 특징을 간단히 설명해주세요.
        3. 각 문서 처음에 있는 대괄호 부분은 인덱스 번호 입니다. (예: [11] -> 11번 인덱스)
        4. 꼭 언급한 어트랙션 이름에 해당하는 인덱스 번호를 마지막에만 추가로 언급해주세요, 하나의 인덱스 번호는 한번만 언급해주세요 (예: 추천드린 어트랙션의 인덱스 번호는 다음과 같습니다: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

        어트랙션 정보를 바탕으로 사용자의 질문에 답변해주세요.
        """
        self.prompt = PromptTemplate.from_template(self.template)

    def process_attraction_response(self, docs, llm_response: str) -> Dict[str, Any]:
        """
        LLM 응답을 처리하여 언급된 어트랙션 ID를 추출합니다.
        
        Args:
            docs (List[Document]): 검색된 문서 목록
            llm_response (str): LLM 응답 텍스트
            
        Returns:
            Dict[str, Any]: LLM 응답과 어트랙션 ID 목록을 담은 딕셔너리
        """
        # 텍스트를 줄 단위로 분할
        llm_lines = llm_response.strip().split('\n')
        # 마지막 줄 가져오기
        llm_last_line = llm_lines[-1]
        
        # 대괄호 안의 숫자 리스트를 찾기 위한 정규식 패턴
        pattern = r'\[([\d\s,]+)\]'

        # 패턴 찾기
        match = re.search(pattern, llm_last_line)

        numbers_str = match.group(1)
        # 문자열을 숫자 리스트로 변환
        indexs = [int(num.strip()) for num in numbers_str.split(',')]

        response_attraction_ids = []
        for index in indexs:
            # content = docs[index].page_content
            content_id = docs[index].metadata["content_id"]
            response_attraction_ids.append(content_id)

        return {"answer": llm_response, "attraction_ids": response_attraction_ids}

    async def search_attractions(self, query: str) -> Dict[str, Any]:
        """
        사용자 쿼리를 받아 관련 관광지를 검색하고 추천합니다.
        
        Args:
            query (str): 사용자 검색 쿼리
            
        Returns:
            Dict[str, Any]: 답변 및 관련 관광지 ID 목록
        """
        # LangSmith 추적 시작 - 이 컨텍스트 매니저는 LangSmith에서 실행 추적을 위해 필요함
        with collect_runs():
            # Advanced RAG 검색기로 관련 문서 검색 (Reranker 적용됨)
            docs = await self.retriever.aretrieve(query)
            
            # 각 정보 앞에 docs의 순서에 맞는 인덱스 번호 부여
            context = ""
            for index, doc in enumerate(docs):
                context += f"[{index}]: "
                context += doc.page_content + "\n\n"

            # LLM에 프롬프트 입력
            chain_input = {"attraction_info": context, "user_request": query}
            
            try:
                formatted_prompt = self.prompt.format(**chain_input)
                response = await self.llm.ainvoke(formatted_prompt)
                
                # 응답 처리 및 반환
                return self.process_attraction_response(docs, response.content)
            except Exception as e:
                print(f"LLM 호출 중 오류 발생: {e}")
                # 오류 발생 시 기본 응답 반환
                return {"answer": f"죄송합니다. 요청을 처리하는 중 오류가 발생했습니다: {str(e)}", "attraction_ids": []}
