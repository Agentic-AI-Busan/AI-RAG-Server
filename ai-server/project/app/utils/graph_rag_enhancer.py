'''
지식 그래프를 활용하여 RAG 컨텍스트를 강화하는 유틸리티
'''
import networkx as nx
import logging
import re
from typing import List, Dict, Any, Optional, Tuple

from langchain_core.documents import Document
from .knowledge_graph_loader import get_knowledge_graph # 순환 참조를 피하기 위해 함수 임포트

logger = logging.getLogger(__name__)

class GraphRAGEnhancer:
    def __init__(self, graph: Optional[nx.DiGraph] = None):
        '''
        GraphRAGEnhancer 초기화.

        Args:
            graph (nx.DiGraph, optional): 사용할 지식 그래프 객체.
                                          None이면 get_knowledge_graph()를 통해 로드 시도.
        '''
        self._graph = graph if graph else get_knowledge_graph()
        if not self._graph:
            logger.warning("GraphRAGEnhancer 초기화: 지식 그래프가 로드되지 않았습니다. 기능이 제한될 수 있습니다.")

    def _normalize_text(self, text: Optional[str]) -> Optional[str]:
        '''텍스트 정규화 (공백 제거, 소문자 변환 등)'''
        if not text or not isinstance(text, str):
            return None
        # create_knowledge_graph.py의 정규화 방식과 유사하게 또는 더 간단하게 적용
        normalized = text.strip().lower()
        normalized = re.sub(r'\s+', '', normalized)  # 모든 공백 제거
        normalized = re.sub(r'[^\w\sㄱ-힣]', '', normalized) # 특수 문자 제거 (옵션)
        return normalized if normalized else None

    async def _extract_entities_from_docs(self, docs: List[Document]) -> List[Tuple[str, str, str, Dict[str, Any]]]:
        '''
        Document 리스트에서 주요 엔티티(장소 이름, 유형, 원본 ID) 및 원본 메타데이터를 추출합니다.
        초기 구현에서는 metadata의 특정 키를 사용합니다.

        Returns:
            List[Tuple[str, str, str, Dict[str, Any]]]: (추출된 엔티티 이름, 엔티티 유형, 원본 ID, 원본 문서 메타데이터) 리스트
                                                엔티티 유형은 'Attraction' 또는 'Restaurant' 등 그래프 노드 타입과 일치해야 함.
                                                원본 ID는 UC_SEQ 또는 RSTR_ID.
        '''
        entities = []
        if not self._graph: # 그래프 없으면 엔티티 추출 의미 없음
            logger.warning("그래프가 로드되지 않아 엔티티를 추출할 수 없습니다.")
            return entities
            
        for doc_idx, doc in enumerate(docs): # doc 인덱스 추가
            entity_name: Optional[str] = None
            entity_type: Optional[str] = None
            source_id: Optional[str] = None # RSTR_ID 또는 UC_SEQ
            
            # 로깅 추가: 메타데이터 전체 로깅
            logger.debug(f"[GraphRAGEnhancer] Doc {doc_idx} 메타데이터 검사 시작: {doc.metadata}")
            # 로깅 추가: page_content 일부 로깅 (백슬래시 문제 회피)
            page_content_preview = doc.page_content[:200].replace('\n', ' ') if doc.page_content else ""
            logger.debug(f"[GraphRAGEnhancer] Doc {doc_idx} page_content 시작: '{page_content_preview}...'")

            # 1. 메타데이터에서 ID 및 유형 우선 추출
            if doc.metadata:
                if doc.metadata.get('UC_SEQ') is not None:
                    source_id = str(doc.metadata.get('UC_SEQ'))
                    entity_type = 'Attraction'
                    logger.debug(f"[GraphRAGEnhancer] Doc {doc_idx}: 메타데이터에서 Attraction ID (UC_SEQ) 추출: '{source_id}'")
                elif doc.metadata.get('RSTR_ID') is not None:
                    source_id = str(doc.metadata.get('RSTR_ID'))
                    entity_type = 'Restaurant'
                    logger.debug(f"[GraphRAGEnhancer] Doc {doc_idx}: 메타데이터에서 Restaurant ID (RSTR_ID) 추출: '{source_id}'")
                elif doc.metadata.get('content_id') is not None: # UC_SEQ가 없고 content_id가 있는 경우 (Attraction 가능성)
                    # content_id를 source_id로 사용하고, 유형을 Attraction으로 가정
                    # 이 정보는 create_knowledge_graph.py의 Attraction 노드 ID 생성 방식과 일치해야 함 (attraction_{UC_SEQ})
                    # 만약 content_id가 UC_SEQ와 동일한 값을 가진다면 이 로직이 유효.
                    source_id = str(doc.metadata.get('content_id'))
                    entity_type = 'Attraction' # content_id가 있으면 Attraction으로 가정
                    logger.debug(f"[GraphRAGEnhancer] Doc {doc_idx}: 메타데이터에 UC_SEQ는 없지만 content_id ('{source_id}') 발견. Attraction으로 간주합니다.")


            # 2. page_content에서 엔티티 이름 추출 (Markdown 제목 형식, 예: "# 가게 이름")
            if doc.page_content:
                # 수정된 정규식: 문자열 시작(^) 조건 제거, 작은따옴표 처리 개선
                match = re.search(r"#\s*(?:\'([^\']+)\'|([^#\r\n]+))", doc.page_content)
                if match:
                    # 작은따옴표가 있는 경우 group(1), 없는 경우 group(2) 사용
                    entity_name_from_content = match.group(1) or match.group(2)
                    if entity_name_from_content:
                        entity_name_from_content = entity_name_from_content.strip()
                        logger.debug(f"[GraphRAGEnhancer] Doc {doc_idx}: page_content에서 정규식 매칭으로 이름 추출: '{entity_name_from_content}'")
                        if not entity_name: # 메타데이터에서 이름을 못찾았거나, page_content 이름 우선 시
                            entity_name = entity_name_from_content
                        
                        if not entity_type: # 메타데이터에서 유형을 못찾았고, 이름으로 추론 시도
                            if any(keyword in entity_name_from_content.lower() for keyword in ["맛집", "식당", "레스토랑", "카페"]):
                                entity_type = "Restaurant"
                            elif any(keyword in entity_name_from_content.lower() for keyword in ["관광", "명소", "해수욕장", "공원", "전망대", "타워", "다리", "문화마을"]):
                                entity_type = "Attraction"
                            logger.debug(f"[GraphRAGEnhancer] Doc {doc_idx}: page_content 이름 기반 entity_type 추론 결과: '{entity_type}'")
                else:
                    logger.debug(f"[GraphRAGEnhancer] Doc {doc_idx}: page_content에서 '# 이름' 패턴을 찾지 못했습니다.")
            
            # 메타데이터의 이름 필드도 확인 (백업)
            if not entity_name and doc.metadata: 
                logger.debug(f"[GraphRAGEnhancer] Doc {doc_idx}: page_content에서 이름 못찾음/추출 안됨. 메타데이터에서 이름 백업 시도. 현재 entity_type: '{entity_type}'")
                if entity_type == 'Attraction':
                    # Attraction의 경우 MAIN_TITLE, CONTENT_TITLE, TITLE 순으로 탐색
                    entity_name = doc.metadata.get('MAIN_TITLE', doc.metadata.get('CONTENT_TITLE', doc.metadata.get('TITLE')))
                    if not entity_name: # 추가적으로 일반 'name' 키도 확인
                        entity_name = doc.metadata.get('name')
                    logger.debug(f"[GraphRAGEnhancer] Doc {doc_idx}: 메타데이터에서 Attraction 이름 백업 추출 시도 결과: '{entity_name}'")
                elif entity_type == 'Restaurant' and 'RSTR_NM' in doc.metadata:
                    entity_name = doc.metadata.get('RSTR_NM')
                    if not entity_name: # 추가적으로 일반 'name' 키도 확인 (식당의 경우)
                        entity_name = doc.metadata.get('name')
                    logger.debug(f"[GraphRAGEnhancer] Doc {doc_idx}: 메타데이터에서 Restaurant 이름 백업 추출 (RSTR_NM 또는 name): '{entity_name}'")

            # 이름 최종 확인 및 page_content 로깅 (Attraction 타입이고 이름이 여전히 None일 때)
            if entity_type == 'Attraction' and not entity_name and doc.page_content:
                logger.warning(f"[GraphRAGEnhancer] Doc {doc_idx} (Attraction): 메타데이터와 정규식으로 이름을 추출하지 못했습니다. page_content 앞부분을 로깅합니다.")
                page_content_preview_for_name_debug = doc.page_content[:250].replace('\n', ' ')
                logger.warning(f"[GraphRAGEnhancer] Doc {doc_idx} page_content (first 250 chars for name debug): '{page_content_preview_for_name_debug}'")

            logger.debug(f"[GraphRAGEnhancer] Doc {doc_idx} (최종 후보): entity_name='{entity_name}', entity_type='{entity_type}', source_id='{source_id}'")
            if entity_name and entity_type and source_id:
                entities.append((str(entity_name), str(entity_type), str(source_id), doc.metadata))
                logger.info(f"[GraphRAGEnhancer] Doc {doc_idx}: 엔티티 추출 성공 - ('{entity_name}', '{entity_type}', '{source_id}')")
            else:
                # 모든 로깅 레벨을 debug로 변경했으므로, 실패 시 warning은 유지
                final_source_id_attempt = source_id if source_id else doc.metadata.get("content_id", doc.metadata.get("id", "ID_추출_실패")) if doc.metadata else "ID_추출_실패"
                final_entity_type_attempt = entity_type if entity_type else "Type_추출_실패"
                logger.warning(f"[GraphRAGEnhancer] Doc {doc_idx}: 엔티티 정보(이름, 유형, ID 중 하나 이상 누락)를 추출하지 못했습니다. 최종 값: name='{entity_name}', type='{final_entity_type_attempt}', id='{final_source_id_attempt}'. Metadata: {doc.metadata}")

        logger.debug(f"[GraphRAGEnhancer] 총 {len(entities)}개의 잠재적 엔티티 추출 완료.") # INFO에서 DEBUG로 변경
        return entities

    def _find_graph_node_for_entity(self, entity_name: str, entity_type: str, source_id: str) -> Optional[str]:
        '''
        추출된 엔티티 정보에 해당하는 그래프 노드 ID를 찾습니다.
        create_knowledge_graph.py에서 정의된 노드 ID 규칙을 따릅니다.
        '''
        if not self._graph:
            logger.warning("[GraphRAGEnhancer] 그래프가 로드되지 않아 노드 매칭을 수행할 수 없습니다.") # 로그 메시지 명확화
            return None
        
        logger.info(f"[GraphRAGEnhancer] 노드 매칭 시도: 이름='{entity_name}', 유형='{entity_type}', 원본ID='{source_id}'") # 추가된 로그
        node_id: Optional[str] = None
        if entity_type == 'Attraction':
            node_id = f"attraction_{source_id}"
        elif entity_type == 'Restaurant':
            # create_knowledge_graph.py에서는 RSTR_ID를 정수형으로 변환 후 사용했음
            # entity_source_id가 이미 문자열이므로, 필요시 정수 변환 후 다시 문자열화하거나, ID 생성 규칙 일관성 확인 필요
            try:
                node_id = f"restaurant_{int(float(source_id))}" # create_knowledge_graph.py와 일치시키기 위해 int(float()) 사용
            except ValueError:
                logger.warning(f"Restaurant source_id '{source_id}'를 정수로 변환하는데 실패했습니다.")
                node_id = f"restaurant_{source_id}" # 변환 실패 시 원본 사용 (일치하지 않을 수 있음)
            logger.info(f"[GraphRAGEnhancer] 생성된 Restaurant 노드 ID: '{node_id}'") # 추가된 로그

        if node_id and self._graph.has_node(node_id):
            logger.info(f"[GraphRAGEnhancer] 엔티티 '{entity_name}'({entity_type}, id:{source_id})에 대한 그래프 노드 '{node_id}' 찾음.") # 로그 메시지 명확화
            return node_id
        else:
            logger.warning(f"[GraphRAGEnhancer] 엔티티 '{entity_name}'({entity_type}, id:{source_id})에 대한 그래프 노드 ('{node_id}')를 찾을 수 없거나 node_id가 None입니다.") # 로그 메시지 명확화
            if node_id:
                 logger.warning(f"[GraphRAGEnhancer] 그래프에 실제로 노드 '{node_id}'가 있는지 확인: {self._graph.has_node(node_id)}") # 추가된 로그
            return None

    def _get_related_info_from_graph(self, node_id: str, query: Optional[str] = None) -> str:
        '''
        주어진 그래프 노드 ID에 대해 관련된 주요 정보를 추출하여 문자열로 반환합니다.
        query를 참고하여 관련성 높은 정보를 우선적으로 포함할 수 있습니다 (향후 확장).
        '''
        if not self._graph or not self._graph.has_node(node_id):
            return ""

        node_attrs = self._graph.nodes[node_id]
        node_name = node_attrs.get('name', node_id) # create_knowledge_graph.py에서 name 속성 사용
        node_type = node_attrs.get('type', '알 수 없음')
        
        info_parts = [f"['{node_name}' ({node_type}) 관련 추가 정보]"]

        # 관계 유형별 정보 추출 (Detail_Graph_RAG.md의 탐색 대상 및 프롬프트 통합 예시 참고)
        # out_edges로 해당 노드에서 나가는 관계만 탐색
        for _, neighbor_id, edge_data in self._graph.out_edges(node_id, data=True):
            edge_type = edge_data.get('type')
            neighbor_attrs = self._graph.nodes.get(neighbor_id, {})
            neighbor_name = neighbor_attrs.get('name', neighbor_id) # 연결된 노드의 이름
            neighbor_node_type = neighbor_attrs.get('type', '정보')

            formatted_info = None
            if edge_type == 'LOCATED_IN':
                formatted_info = f"  - 위치: {neighbor_name} ({neighbor_node_type})"
            elif edge_type == 'SERVES_MENU':
                price = edge_data.get('price')
                price_info = f" (가격: {price}원)" if price is not None and price != 'nan' and price != '' else ""
                menu_desc = neighbor_attrs.get('description', '')
                menu_desc_info = f" [{menu_desc}]" if menu_desc else ""
                formatted_info = f"  - 주요 메뉴: {neighbor_name}{menu_desc_info}{price_info}"
            elif edge_type == 'HAS_FEATURE':
                formatted_info = f"  - 특징: {neighbor_name}"
            elif edge_type == 'NEARBY_LANDMARK':
                distance = edge_data.get('distance')
                dist_info = f" (거리: 약 {float(distance):.0f}m)" if distance is not None and str(distance).lower() != 'nan' else ""
                formatted_info = f"  - 주변: {neighbor_name}{dist_info}"
            # 필요에 따라 다른 관계 유형에 대한 정보 추가 (예: Attraction의 contact, traffic_info 등은 노드 자체 속성)
            
            if formatted_info:
                info_parts.append(formatted_info)
        
        # 노드 자체의 추가 속성 (예: 설명, 연락처 등)
        if node_type == 'Attraction':
            description = node_attrs.get('description')
            contact = node_attrs.get('contact')
            traffic = node_attrs.get('traffic_info')
            if description and description not in ' '.join(info_parts): info_parts.append(f"  - 상세 설명: {description[:100]}...") # 너무 길면 일부만
            if contact: info_parts.append(f"  - 연락처: {contact}")
            if traffic: info_parts.append(f"  - 교통정보: {traffic}")
        elif node_type == 'Restaurant':
            description = node_attrs.get('description')
            hours = node_attrs.get('hours')
            closed_days = node_attrs.get('closed_days')
            if description and description not in ' '.join(info_parts): info_parts.append(f"  - 식당 소개: {description[:100]}...")
            if hours: info_parts.append(f"  - 영업시간: {hours}")
            if closed_days: info_parts.append(f"  - 휴무일: {closed_days}")
            
        if len(info_parts) == 1: # 추가된 정보가 없는 경우 (타이틀만 있는 경우)
            return f"'{node_name}'에 대한 그래프 추가 정보는 현재 없습니다."
            
        return "\n".join(info_parts)

    async def get_graph_context_for_docs(self, query: str, docs: List[Document]) -> str:
        '''
        사용자 쿼리와 검색된 Document 리스트를 기반으로 지식 그래프에서 추가 컨텍스트를 생성합니다.

        Args:
            query (str): 사용자 질문.
            docs (List[Document]): 벡터 검색 등을 통해 검색된 초기 문서 리스트.

        Returns:
            str: LLM 프롬프트에 추가될 그래프 기반 컨텍스트 문자열.
                 정보가 없거나 오류 발생 시 빈 문자열 반환.
        '''
        if not self._graph:
            logger.warning("지식 그래프가 로드되지 않아 컨텍스트 강화를 수행할 수 없습니다.")
            return ""

        extracted_entities = await self._extract_entities_from_docs(docs)
        if not extracted_entities:
            logger.info("문서에서 그래프와 연결할 엔티티를 추출하지 못했습니다.")
            return ""

        graph_contexts = []
        processed_node_ids = set() # 중복된 노드 정보 방지를 위해 처리된 노드 ID 저장

        for entity_name, entity_type, source_id, original_metadata in extracted_entities:
            node_id = self._find_graph_node_for_entity(entity_name, entity_type, source_id)
            if node_id and node_id not in processed_node_ids:
                related_info = self._get_related_info_from_graph(node_id, query) # query 전달은 향후 활용 가능성
                if related_info and "현재 없습니다" not in related_info:
                    graph_contexts.append(related_info)
                    processed_node_ids.add(node_id)
            elif node_id in processed_node_ids:
                 logger.debug(f"노드 '{node_id}'는 이미 처리되어 컨텍스트를 추가하지 않습니다.")

        if not graph_contexts:
            logger.info("추출된 엔티티에 대한 유의미한 그래프 정보를 찾지 못했습니다.")
            return ""
        
        final_context = "\n\n".join(graph_contexts)
        logger.info(f"그래프 기반 추가 컨텍스트 생성 완료 (일부):\n{final_context[:500]}...")
        return final_context

# 스크립트 직접 실행 시 테스트용 (예시)
if __name__ == '__main__':
    import asyncio
    logging.basicConfig(level=logging.INFO)
    logger.info("GraphRAGEnhancer 테스트 시작...")

    sample_docs_data = [
        {'page_content': '해운대 해수욕장은 부산의 대표적인 여름 피서지입니다.', 'metadata': {'MAIN_TITLE': '해운대해수욕장', 'UC_SEQ': '26'}},
        {'page_content': '자갈치시장은 신선한 해산물을 맛볼 수 있는 곳입니다.', 'metadata': {'MAIN_TITLE': '자갈치시장', 'UC_SEQ': '27'}},
        {'page_content': '해운대암소갈비집은 유명한 갈비 맛집입니다.', 'metadata': {'RSTR_NM': '해운대암소갈비집', 'RSTR_ID': '1241'}},
        {'page_content': '더미 문서입니다.', 'metadata': {}},
        {'page_content': '초량이바구길은 역사적인 장소입니다.', 'metadata': {'MAIN_TITLE': '초량이바구길', 'UC_SEQ': '58'}},
    ]
    sample_docs = [Document(page_content=d['page_content'], metadata=d['metadata']) for d in sample_docs_data]

    enhancer = GraphRAGEnhancer()

    async def main_test():
        if not enhancer._graph:
            logger.error("테스트 중단: 지식 그래프 로드 실패.")
            return

        test_query = "부산 맛집과 관광지 추천해줘"
        graph_context = await enhancer.get_graph_context_for_docs(test_query, sample_docs)
        
        print("--- 생성된 그래프 컨텍스트 ---")
        if graph_context:
            print(graph_context)
        else:
            print("생성된 그래프 컨텍스트가 없습니다.")
        print("---------------------------")

    asyncio.run(main_test())
    logger.info("GraphRAGEnhancer 테스트 종료.") 