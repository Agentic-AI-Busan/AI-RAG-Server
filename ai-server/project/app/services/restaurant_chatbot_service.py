from typing import Dict, Any, List, Tuple
from .base import BaseService
from ..utils.graph_rag_enhancer import GraphRAGEnhancer

class RestaurantChatbotService(BaseService):
    """
    음식점 관련 챗봇 서비스
    사용자의 음식점 관련 질문에 대해 자연스러운 대화형 응답을 제공합니다.
    지식 그래프 정보를 활용하여 답변을 강화합니다.
    """
    def __init__(
        self, 
        use_reranker: bool = True, 
        use_hybrid: bool = True,
        hybrid_alpha: float = 0.8,
        initial_k: int = 20, 
        final_k: int = 20
    ):
        super().__init__(
            vectordb_name="restaurant_finder",
            use_reranker=use_reranker,
            use_hybrid=use_hybrid,
            hybrid_alpha=hybrid_alpha,
            initial_k=initial_k,
            final_k=final_k
        )
        self._define_prompt_template()
        self.graph_rag_enhancer = GraphRAGEnhancer()
        print("RestaurantChatbotService 초기화 완료: GraphRAGEnhancer 통합됨")

    def _define_prompt_template(self):
        """음식점 관련 챗봇 프롬프트 템플릿을 정의합니다."""
        self.prompt_template = """
        당신은 음식점 추천 전문가이자 친절한 대화 상대입니다. 사용자의 질문에 대해 자연스럽고 도움이 되는 답변을 제공해주세요.
        
        [검색된 음식점 정보 목록]
        {context}
        
        [위 음식점들에 대한 지식 그래프 추가 정보]
        {graph_context}
        
        [사용자 질문]
        {query}
        
        [이전 대화]
        {chat_history}
        
        다음 지침을 따라 답변해주세요:
        1. 사용자의 질문에 직접적으로 답변하되, 자연스러운 대화체를 유지해주세요.
        2. 주요 추천 대상은 "검색된 음식점 정보 목록"에서 선택해주세요.
        3. "지식 그래프 추가 정보"는 음식점을 더 자세히 설명하거나, 사용자의 특정 요구사항(예: 주차, 특정 메뉴)과 관련된 부가 정보를 제공하는 데 활용해주세요.
        4. 음식점 추천 시 사용자의 선호도, 예산, 위치 등을 고려해주세요.
        5. 메뉴, 가격, 분위기, 평점 등 구체적인 정보를 포함해주세요.
        6. 필요한 경우 추가 질문을 통해 사용자의 선호도를 파악해주세요.
        7. 친절하고 공감하는 태도로 응답해주세요.
        
        답변:
        """

    async def process_query(
        self,
        query: str,
        chat_history: List[Tuple[str, str]] = None
    ) -> Dict[str, Any]:
        """
        음식점 관련 쿼리를 처리하고 자연스러운 대화형 응답을 제공합니다.

        Args:
            query (str): 사용자 질문
            chat_history (List[Tuple[str, str]], optional): 이전 대화 기록

        Returns:
            Dict[str, Any]: 처리 결과
        """
        try:
            # 1. 관련 문서 검색 (기존 방식)
            docs = await self.retriever.aretrieve(query)
            # print(f"docs[0]: {docs[0] if docs else 'No docs found'}") # 디버깅용 로그
            original_docs_context = "\n\n".join([doc.page_content for doc in docs])
            
            # 2. 그래프 컨텍스트 생성 (GraphRAGEnhancer 사용)
            graph_context_str = ""
            if self.graph_rag_enhancer and self.graph_rag_enhancer._graph: # Enhancer와 그래프가 로드되었는지 확인
                graph_context_str = await self.graph_rag_enhancer.get_graph_context_for_docs(query, docs)
            else:
                print("경고: GraphRAGEnhancer 또는 내부 그래프가 초기화되지 않았습니다. 그래프 컨텍스트 없이 진행합니다.")

            # 대화 기록 포맷팅
            formatted_history = self._format_chat_history(chat_history or [])

            # LLM에 프롬프트 전달
            response = await self.llm.ainvoke(
                self.prompt_template.format(
                    context=original_docs_context,
                    graph_context=graph_context_str if graph_context_str else "제공된 추가 정보 없음", # 빈 문자열 대신 명시적 메시지
                    query=query,
                    chat_history=formatted_history
                )
            )

            return {
                "response": response.content,
                "sources": [doc.metadata for doc in docs], # 소스는 기존 문서 메타데이터 유지
                "category": "restaurant_chat"
            }

        except Exception as e:
            print(f"음식점 챗봇 처리 중 오류 발생: {e}")
            # 스택 트레이스 로깅 추가
            import traceback
            traceback.print_exc()
            return {
                "response": "죄송합니다. 대화를 처리하는 중에 오류가 발생했습니다. 다시 한번 말씀해 주시겠어요?",
                "sources": [],
                "category": "restaurant_chat"
            }

    def _format_chat_history(self, chat_history: List[Tuple[str, str]]) -> str:
        """대화 기록을 포맷팅합니다."""
        if not chat_history:
            return "이전 대화 없음"
        return "\n".join([f"사용자: {q}\nAI: {a}" for q, a in chat_history])
