from typing import Dict, Any, List
from langchain_core.prompts import PromptTemplate
from langchain_core.tracers.context import collect_runs
from .base import BaseService


class RestaurantService(BaseService):
    def __init__(self, use_reranker: bool = True, initial_k: int = 20, final_k: int = 20):
        """
        레스토랑 검색 서비스 초기화

        Args:
            use_reranker (bool): Reranker 사용 여부
            initial_k (int): 초기 검색 문서 수
            final_k (int): 최종 반환 문서 수
        """
        super().__init__(
            vectordb_name="restaurant_finder",
            use_reranker=use_reranker,
            initial_k=initial_k,
            final_k=final_k
        )

        self.template = """
        당신은 레스토랑 추천 AI입니다. 주어진 맥락을 바탕으로 사용자의 질문에 답변해주세요.

        다음은 레스토랑에 대한 정보입니다:
        {restaurant_info}

        사용자 질문: {user_request}

        다음 지침을 따라 답변해주세요:
        1. 조건에 맞는 식당을 2-3개 추천해주세요.
        2. 각 식당의 이름을 정확히 큰따옴표로 감싸서 언급해주세요. (예: "더밥하우스")
        3. 각 식당의 주요 특징을 간단히 설명해주세요.

        레스토랑 정보를 바탕으로 사용자의 질문에 답변해주세요.
        """
        self.prompt = PromptTemplate.from_template(self.template)

    def process_restaurant_response(self, docs, llm_response: str) -> Dict[str, Any]:
        """
        LLM 응답을 처리하여 언급된 레스토랑 ID를 추출합니다.
        
        Args:
            docs (List[Document]): 검색된 문서 목록
            llm_response (str): LLM 응답 텍스트
            
        Returns:
            Dict[str, Any]: LLM 응답과 레스토랑 ID 목록을 담은 딕셔너리
        """
        mentioned_restaurants = {}
        for doc in docs:
            content = doc.page_content
            rstr_id = doc.metadata["RSTR_ID"]

            for line in content.split("\n"):
                if line.startswith("# "):
                    restaurant_name = line.replace("# ", "").strip()
                    mentioned_restaurants[restaurant_name] = rstr_id
                    break

        response_restaurant_ids = []
        for restaurant_name in mentioned_restaurants.keys():
            if restaurant_name in llm_response:
                response_restaurant_ids.append(mentioned_restaurants[restaurant_name])

        return {"answer": llm_response, "restaurant_ids": response_restaurant_ids}

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
            # Advanced RAG 검색기로 관련 문서 검색 (Reranker 적용됨)
            docs = await self.retriever.aretrieve(query)

            # 검색된 문서 내용을 컨텍스트로 결합
            context = "\n\n".join([doc.page_content for doc in docs])

            # LLM에 프롬프트 입력
            chain_input = {"restaurant_info": context, "user_request": query}

            try:
                formatted_prompt = self.prompt.format(**chain_input)
                response = await self.llm.ainvoke(formatted_prompt)
                
                # 응답 처리 및 반환
                return self.process_restaurant_response(docs, response.content)
            except Exception as e:
                print(f"LLM 호출 중 오류 발생: {e}")
                # 오류 발생 시 기본 응답 반환
                return {"answer": f"죄송합니다. 요청을 처리하는 중 오류가 발생했습니다: {str(e)}", "restaurant_ids": []}