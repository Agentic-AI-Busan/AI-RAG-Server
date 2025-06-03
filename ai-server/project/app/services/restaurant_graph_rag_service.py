from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.tracers.context import collect_runs

from app.services.base import BaseService # BaseService는 그대로 사용
from app.services.restaurant import Recommendation, RestaurantResponse # 스키마를 기존 서비스 파일에서 가져옴
from app.utils.graph_rag_enhancer import GraphRAGEnhancer

class RestaurantGraphRAGService(BaseService):
    def __init__(
        self, 
        use_reranker: bool = True, 
        use_hybrid: bool = True,
        hybrid_alpha: float = 0.8,
        initial_k: int = 20, 
        final_k: int = 20
    ):
        super().__init__(
            vectordb_name="restaurant_finder", # 기존과 동일한 벡터DB 사용
            use_reranker=use_reranker,
            use_hybrid=use_hybrid,
            hybrid_alpha=hybrid_alpha,
            initial_k=initial_k,
            final_k=final_k
        )
        print(f"RestaurantGraphRAGService 초기화 시작")
        self.graph_rag_enhancer = GraphRAGEnhancer()
        
        # JSON 파서 설정 (기존 RestaurantService와 동일한 응답 스키마 사용)
        self.parser = JsonOutputParser(pydantic_object=RestaurantResponse)
        
        # 프롬프트 템플릿 정의 (그래프 정보 활용하도록 수정)
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
            당신은 식당 추천 AI입니다. 주어진 맥락 정보를 바탕으로 사용자의 질문에 답변해야 합니다.
            
            다음 지침을 반드시 엄격하게 따라 답변해주세요:
            1.  "검색된 식당 정보 목록"은 당신이 사용자에게 추천할 수 있는 식당 후보들의 주요 정보입니다. 각 식당은 대괄호 안의 번호(index)로 식별됩니다.
            2.  "지식 그래프 추가 정보"는 "검색된 식당 정보 목록"에 있는 각 식당에 대한 보충 설명입니다. 이 정보를 활용하여 식당을 더 자세히 설명하거나, 사용자의 특정 요구사항(예: 주차, 특정 메뉴, 분위기, 위치)과 관련된 부가 정보를 제공해주세요.
            3.  사용자의 질문에 가장 적합하다고 판단되는 식당들을 "검색된 식당 정보 목록"에서 선택하여 추천해야 합니다.
            4.  추천하는 각 식당에 대해, 해당 식당이 "검색된 식당 정보 목록"의 몇 번째 항목인지 그 번호를 `index` 필드에 정확히 기재해야 합니다.
            5.  선택한 식당들의 `index` 번호들을 `restaurant_ids` 리스트에 순서대로 포함해야 합니다. (실제 ID가 아닌, "검색된 식당 정보 목록"에서의 순번 index)
            6.  `name` 필드에는 식당의 전체 이름을, `description` 필드에는 사용자의 질문과 맥락을 고려한 추천 이유 및 상세 설명을 자유롭게 작성해주세요. "지식 그래프 추가 정보"를 적극 활용하여 설명을 풍부하게 만드세요.
            7.  반드시 지정된 JSON 형식으로만 응답해야 하며, 다른 어떤 설명도 추가하지 마세요.
            """),
            ("user", """
            [검색된 식당 정보 목록]
            {restaurant_info}

            [위 식당들에 대한 지식 그래프 추가 정보]
            {graph_context}

            [사용자 질문]
            {user_request}

            {format_instructions}
            """)
        ])

        self.prompt = prompt.partial(format_instructions=self.parser.get_format_instructions())
        self.chain = self.prompt | self.llm | self.parser
        print(f"RestaurantGraphRAGService 초기화 완료: GraphRAGEnhancer 및 수정된 프롬프트 통합됨")

    def response_validation_check(self, docs: List[Any], response: Dict[str, Any]):
        """LLM 응답의 유효성 검사 (기존 로직과 유사하게 유지)"""
        original_recommendations = response.get("recommendations", [])
        print(f"[GraphRAG Validation] LLM 응답 recommendations 수: {len(original_recommendations)}")
        for rec_idx, rec in enumerate(original_recommendations):
            index = rec.get("index", -1)
            if 0 <= index < len(docs):
                doc_content = docs[index].page_content
                # 마크다운 제목에서 이름 추출 (GraphRAGEnhancer와 유사한 방식)
                match = re.search(r"^#\s*(.+?)$", doc_content, re.MULTILINE)
                doc_name_from_content = match.group(1).strip() if match else "이름 추출 실패"
                print(f"== [GraphRAG Validation] {rec_idx}번째 추천 (index: {index}) 유효성 검사 ==")
                print(f"  - VectorDB 문서 이름 (내용 기반): '{doc_name_from_content}'")
                print(f"  - LLM 응답 추천 이름: '{rec.get('name')}'")
                # print(f"  - LLM 응답 설명: {rec.get('description')[:100]}...") # 필요시 활성화
            else:
                print(f"== [GraphRAG Validation] {rec_idx}번째 추천 (index: {index}) 유효하지 않은 인덱스 ==")
        
        response_ids = response.get("restaurant_ids", [])
        print(f"[GraphRAG Validation] LLM 응답 restaurant_ids (인덱스 리스트): {response_ids}")

    async def search_restaurants_with_graph_rag(self, query: str) -> Dict[str, Any]:
        """
        사용자 쿼리를 받아 관련 레스토랑을 검색하고, 그래프 정보로 강화하여 추천합니다.
        """
        print(f"[RestaurantGraphRAGService] search_restaurants_with_graph_rag 호출: query='{query}'")
        with collect_runs(): # LangSmith 추적
            try:
                # 1. 초기 문서 검색 (기존 BaseService의 retriever 사용)
                docs = await self.retriever.aretrieve(query)
                print(f"[RestaurantGraphRAGService] 초기 문서 검색 완료: {len(docs)}개 문서")
                
                # 2. 기존 컨텍스트 생성 (인덱스 번호 부여)
                original_docs_context = ""
                for index, doc in enumerate(docs):
                    original_docs_context += f"[{index}]: "
                    original_docs_context += doc.page_content + "\n\n"
                
                # 3. 그래프 컨텍스트 생성 (GraphRAGEnhancer 사용)
                graph_context_str = "제공된 추가 정보 없음"
                if self.graph_rag_enhancer and self.graph_rag_enhancer._graph:
                    print(f"[RestaurantGraphRAGService] GraphRAGEnhancer로 그래프 컨텍스트 생성 시도")
                    graph_context_str = await self.graph_rag_enhancer.get_graph_context_for_docs(query, docs)
                    if not graph_context_str: # 만약 enhancer가 빈 문자열을 반환했다면
                        graph_context_str = "지식 그래프에서 관련된 추가 정보를 찾지 못했습니다."
                else:
                    print("[RestaurantGraphRAGService] 경고: GraphRAGEnhancer 또는 내부 그래프가 초기화되지 않았습니다.")
                print(f"[RestaurantGraphRAGService] 그래프 컨텍스트 생성 완료 (일부): {graph_context_str[:200]}...")

                # 4. LLM 체인 호출 (강화된 프롬프트 사용)
                print(f"[RestaurantGraphRAGService] LLM 체인 호출 시작")
                llm_response = await self.chain.ainvoke({
                    "restaurant_info": original_docs_context,
                    "graph_context": graph_context_str,
                    "user_request": query
                })
                print(f"[RestaurantGraphRAGService] LLM 체인 호출 완료")
                
                # 5. 응답 유효성 검사 (개발/디버깅 목적)
                self.response_validation_check(docs, llm_response)
                
                # 6. restaurant_ids를 실제 RSTR_ID로 변환 (기존 로직 유지)
                # LLM은 "검색된 식당 정보 목록"의 index를 반환하도록 프롬프트에서 지시했으므로,
                # llm_response["restaurant_ids"]는 RSTR_ID가 아닌 index 리스트임.
                llm_indexes = llm_response.get("restaurant_ids", [])
                content_ids = []
                for index in llm_indexes:
                    if 0 <= index < len(docs):
                        # RestaurantService에서는 metadata key가 'RSTR_ID' 였음
                        content_id = docs[index].metadata.get("RSTR_ID") 
                        if content_id:
                            content_ids.append(content_id)
                        else:
                            print(f"[RestaurantGraphRAGService] 경고: docs[{index}]에서 RSTR_ID를 찾을 수 없습니다. 메타데이터: {docs[index].metadata}")
                    else:
                        print(f"[RestaurantGraphRAGService] 경고: LLM이 반환한 잘못된 인덱스({index})는 무시합니다.")
                
                # 최종 응답 객체에 실제 RSTR_ID 리스트로 업데이트
                final_response = llm_response.copy() # 원본 llm_response는 유지
                final_response["restaurant_ids"] = content_ids
                print(f"[RestaurantGraphRAGService] 최종 반환 restaurant_ids (RSTR_ID 리스트): {content_ids}")
                
                return final_response

            except Exception as e:
                print(f"[RestaurantGraphRAGService] search_restaurants_with_graph_rag API 오류: {e}")
                import traceback
                traceback.print_exc()
                # 기존 API와 동일한 오류 응답 형식 유지 시도
                return {"recommendations": [], "restaurant_ids": [], "error_message": f"죄송합니다. 요청을 처리하는 중 오류가 발생했습니다: {str(e)}"}

# re 모듈 임포트 (response_validation_check 내부에서 사용)
import re 