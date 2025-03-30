from typing import Dict, Any, List
from langchain_core.prompts import PromptTemplate
from langchain_core.tracers.context import collect_runs
from .base import BaseService
import re

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from pydantic import BaseModel, Field
from typing import List


"""
    name: 장소 이름
    description: 장소에 대한설명
    index: 장소 인덱스
"""
class Recommendation(BaseModel):
    name: str
    description: str
    index: int

"""
    recommendations: 추천 장소에 대한 리스트
    restaurant_ids: 백엔드에서 요청하는 장소 ID
"""
class AttractionResponse(BaseModel):
    recommendations: List[Recommendation]
    restaurant_ids: List[int]

class RestaurantService(BaseService):
    def __init__(
        self, 
        use_reranker: bool = True, 
        use_hybrid: bool = True,
        hybrid_alpha: float = 0.8,
        initial_k: int = 20, 
        final_k: int = 20
    ):
        """
        레스토랑 검색 서비스 초기화

        Args:
            use_reranker (bool): Reranker 사용 여부
            use_hybrid (bool): 하이브리드 검색(TMM-CC) 사용 여부
            hybrid_alpha (float): 하이브리드 검색 알파 값 (0.0~1.0, 기본값 0.8)
            initial_k (int): 초기 검색 문서 수
            final_k (int): 최종 반환 문서 수
        """
        print(f"레스토랑 서비스 초기화: use_reranker={use_reranker}, use_hybrid={use_hybrid}, hybrid_alpha={hybrid_alpha}")
        super().__init__(
            vectordb_name="restaurant_finder",
            use_reranker=use_reranker,
            use_hybrid=use_hybrid,
            hybrid_alpha=hybrid_alpha,
            initial_k=initial_k,
            final_k=final_k
        )
        print(f"레스토랑 서비스 초기화 완료")

        # 반환받을 Json파서 설정
        self.parser = JsonOutputParser(pydantic_object=AttractionResponse)
        
        # 프롬프트 구성
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
            당신은 어트랙션 추천 AI입니다. 주어진 맥락을 바탕으로 사용자의 질문에 답변해주세요.
            
            다음 지침을 따라 답변해주세요:
            1. 각 문서 처음에 있는 대괄호 부분은 인덱스 번호 입니다.
            2. 사용자 질문에 맞는 어트랙션을 선택하여 name과 description과 index 형태로 제공해주세요.
            3. 선택한 어트랙션의 인덱스 번호를 restaurant_ids 리스트에 포함해주세요.
            4. 반드시 지정된 JSON 형식으로 응답해주세요.
            """),
            ("user", "어트랙션 정보: {restaurant_info}\n\n사용자 질문: {user_request}\n\n{format_instructions}")
        ])

        # 프롬프트에 형식 지침 추가 
        self.prompt = prompt.partial(format_instructions=self.parser.get_format_instructions())

        # 체인 구성
        self.chain = self.prompt | self.llm | self.parser

    def response_validation_check(self, docs, response):
        original_recommandations = response.get("recommendations", [])
        
        for rec in original_recommandations:
            index = rec.get("index", -1)
            if 0 <= index < len(docs):  # 인덱스 범위 확인
                markdown_content = docs[index].page_content
                splits = markdown_content.split('\n')
                head_line = ""
                for split in splits:
                    if split.startswith("# "):
                        head_line = split
                        break
                print(f"== {index}번쨰 데이터 유효성 검사 ==")
                print(f"VectorDB 문서 내용 : {head_line[2:]}")
                print(f"LLM 응답 내용      : {rec.get('name')}\n")

    async def search_restaurants(self, query: str) -> Dict[str, Any]:
        """
        사용자 쿼리를 받아 관련 레스토랑을 검색하고 추천합니다.
        
        Args:
            query (str): 사용자 검색 쿼리
            
        Returns:
            Dict[str, Any]: 답변 및 관련 레스토랑 ID 목록
        """
        # LangSmith 추적 시작 - 이 컨텍스트 매니저는 LangSmith에서 실행 추적을 위해 필요함
        with collect_runs():
            try:
                # Advanced RAG 검색기로 관련 문서 검색 (Reranker 적용됨)
                docs = await self.retriever.aretrieve(query)
                
                # 각 정보 앞에 docs의 순서에 맞는 인덱스 번호 부여
                context = ""
                for index, doc in enumerate(docs):
                    context += f"[{index}]: "
                    context += doc.page_content + "\n\n"
                
                # JsonParser체인에 요청
                response = await self.chain.ainvoke({"restaurant_info": context, "user_request": query})
                
                self.response_validation_check(docs, response)
                
                # index를 원래 데이터의 ID로 변경
                original_ids = response.get("restaurant_ids", [])
                content_ids = []
                
                # 인덱스를 content_id로 변환
                for index in original_ids:
                    if 0 <= index < len(docs):  # 인덱스 범위 확인
                        content_id = docs[index].metadata.get("RSTR_ID")
                        if content_id:
                            content_ids.append(content_id)
                
                # 변환된 content_ids로 업데이트
                response["restaurant_ids"] = content_ids  # 변환된 ID로 대체
                
                # return response
                # 응답 처리 및 반환
                return response
            except Exception as e:
                print(f"LLM 호출 중 오류 발생: {e}")
                # 오류 발생 시 기본 응답 반환
                return {"answer": f"죄송합니다. 요청을 처리하는 중 오류가 발생했습니다: {str(e)}", "restaurant_ids": []}