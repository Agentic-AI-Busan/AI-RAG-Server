'''
Knowledge Graph 로딩 및 접근 유틸리티
'''
import pickle
import networkx as nx
from pathlib import Path
import logging

# 로거 설정
logger = logging.getLogger(__name__)

# 그래프 파일 경로 (ai-server/project 기준)
# create_knowledge_graph.py 에서 저장한 경로와 일치해야 합니다.
GRAPH_FILE_PATH = Path(__file__).parent.parent.parent / "graphdb" / "knowledge_graph.gpickle"

_graph_instance: nx.DiGraph | None = None
_graph_load_attempted: bool = False

def load_knowledge_graph() -> nx.DiGraph | None:
    '''
    knowledge_graph.gpickle 파일을 로드하여 networkx.DiGraph 객체를 반환합니다.
    파일이 없거나 오류 발생 시 None을 반환하고 오류를 로깅합니다.
    '''
    global _graph_load_attempted
    _graph_load_attempted = True

    logger.info(f"지식 그래프 로드 시도. 경로: {GRAPH_FILE_PATH}")

    if not GRAPH_FILE_PATH.exists():
        logger.error(f"지식 그래프 파일을 찾을 수 없습니다: {GRAPH_FILE_PATH}")
        return None

    try:
        logger.info(f"파일 존재 확인: {GRAPH_FILE_PATH}")
        with open(GRAPH_FILE_PATH, 'rb') as f:
            logger.info(f"파일 열기 성공: {GRAPH_FILE_PATH}")
            graph = pickle.load(f)
            logger.info(f"pickle.load 성공: {GRAPH_FILE_PATH}")
        logger.info(f"지식 그래프 로드 성공: {GRAPH_FILE_PATH} (노드: {graph.number_of_nodes()}, 엣지: {graph.number_of_edges()})")
        return graph
    except FileNotFoundError:
        logger.error(f"지식 그래프 파일을 찾을 수 없습니다 (FileNotFoundError): {GRAPH_FILE_PATH}")
        return None
    except pickle.UnpicklingError as e:
        logger.error(f"지식 그래프 파일 디코딩(pickle) 오류: {GRAPH_FILE_PATH} - {e}")
        return None
    except Exception as e:
        logger.error(f"지식 그래프 로드 중 알 수 없는 오류 발생: {GRAPH_FILE_PATH} - {e}")
        return None

def get_knowledge_graph() -> nx.DiGraph | None:
    '''
    로드된 지식 그래프 인스턴스를 반환합니다.
    그래프가 아직 로드되지 않았다면 로드를 시도합니다.
    FastAPI 의존성 주입 등으로 사용될 수 있습니다.
    '''
    global _graph_instance
    global _graph_load_attempted

    if _graph_instance is None and not _graph_load_attempted:
        _graph_instance = load_knowledge_graph()
    
    if _graph_instance is None and _graph_load_attempted:
        logger.warning("get_knowledge_graph 호출1: 이전에 그래프 로드에 실패했거나 시도되지 않았습니다. 다시 로드를 시도하지 않습니다.")
        
    return _graph_instance

# FastAPI 애플리케이션 시작 시 그래프를 로드하도록 설정할 수 있습니다.
# 예를 들어, main.py의 startup 이벤트 핸들러에서 load_knowledge_graph()를 호출할 수 있습니다.
# 현재는 get_knowledge_graph()가 처음 호출될 때 로드하도록 되어 있습니다.

if __name__ == '__main__':
    # 스크립트 직접 실행 시 테스트 로직
    logging.basicConfig(level=logging.INFO)
    print("지식 그래프 로더 테스트 시작...")
    graph = get_knowledge_graph()
    if graph:
        print(f"테스트: 그래프 로드 성공. 노드 수: {graph.number_of_nodes()}, 엣지 수: {graph.number_of_edges()}")
        # 예시 노드 및 엣지 정보 출력
        sample_node_ids = list(graph.nodes)[:5]
        for node_id in sample_node_ids:
            print(f"  샘플 노드: {node_id}, 속성: {graph.nodes[node_id]}")
        
        sample_edge_data = list(graph.edges(data=True))[:5]
        for u, v, data in sample_edge_data:
            print(f"  샘플 엣지: ({u}) -> ({v}), 속성: {data}")
            
    else:
        print("테스트: 그래프 로드 실패.")
    print("지식 그래프 로더 테스트 종료.") 