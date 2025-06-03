import pandas as pd
import networkx as nx
import os
import re
import math
import pickle

# --- Configuration ---
# 데이터 파일 경로 (컨테이너 /project 기준 상대 경로 - 볼륨 마운트 후)
ATTRACTION_DATA_PATH = "data/Attraction/M1_2_Trimmed.csv"
RESTAURANT_7B_DATA_PATH = "data/Restaurant/7B/7B_2_Trimmed.csv"
RESTAURANT_BFTS_DATA_PATH = "data/Restaurant/BFTS/BFTS_2_Trimmed.csv"

# 생성될 그래프 파일 저장 경로 (컨테이너 /project 기준 상대 경로)
GRAPH_OUTPUT_DIR = "graphdb" # /project/graphdb 에 저장
GRAPH_OUTPUT_FILENAME = "knowledge_graph.gpickle"
GRAPH_OUTPUT_PATH = os.path.join(GRAPH_OUTPUT_DIR, GRAPH_OUTPUT_FILENAME)

# --- Helper Functions ---

def normalize_text(text):
    """텍스트 정규화 (공백 제거, 소문자 변환 등)"""
    if isinstance(text, str):
        text = text.strip().lower()
        # 추가적인 정규화 규칙 필요시 여기에 추가
        text = re.sub(r'\s+', '', text) # 모든 공백 제거 (필요에 따라 조정)
        text = re.sub(r'[^\w\sㄱ-힣]', '', text) # 특수 문자 제거 (옵션)
    return text

def safe_get(data, key, default=None):
    """딕셔너리 또는 Series에서 안전하게 값 가져오기 (NaN 처리 포함)"""
    val = data.get(key, default)
    if isinstance(val, float) and math.isnan(val):
        return default
    if pd.isna(val):
        return default
    return val

def add_node_if_not_exists(graph, node_id, **attrs):
    """그래프에 노드가 없으면 추가"""
    if not graph.has_node(node_id):
        graph.add_node(node_id, **attrs)
        # print(f"Added node: {node_id} ({attrs.get('type', '')})") # 로그 출력 필요시 활성화
    # else:
        # print(f"Node already exists: {node_id}") # 로그 출력 필요시 활성화


def add_edge_if_not_exists(graph, u_of_edge, v_of_edge, **attrs):
    """그래프에 엣지가 없으면 추가"""
    if not graph.has_edge(u_of_edge, v_of_edge):
        graph.add_edge(u_of_edge, v_of_edge, **attrs)
        # print(f"Added edge: {u_of_edge} -> {v_of_edge} ({attrs.get('type', '')})") # 로그 출력 필요시 활성화
    # else:
        # print(f"Edge already exists: {u_of_edge} -> {v_of_edge}") # 로그 출력 필요시 활성화

# --- Main Script ---

print("Knowledge Graph 생성 시작...")

# 그래프 객체 생성 (방향성 그래프)
G = nx.DiGraph()

# 1. 관광지 데이터 처리
print(f"관광지 데이터 로딩: {ATTRACTION_DATA_PATH}")
try:
    # 다양한 인코딩 시도
    try:
        attraction_df = pd.read_csv(ATTRACTION_DATA_PATH, encoding='utf-8')
    except UnicodeDecodeError:
        attraction_df = pd.read_csv(ATTRACTION_DATA_PATH, encoding='cp949')

    print(f"관광지 데이터 {len(attraction_df)}개 처리 시작...")
    for index, row in attraction_df.iterrows():
        # 노드 ID 정의
        attraction_id = f"attraction_{safe_get(row, 'UC_SEQ')}"
        area_name = normalize_text(safe_get(row, 'GUGUN_NM'))
        area_id = f"area_{area_name}" if area_name else None

        # Attraction 노드 추가
        add_node_if_not_exists(G, attraction_id,
                               type='Attraction',
                               name=safe_get(row, 'MAIN_TITLE'),
                               address=safe_get(row, 'ADDR1'),
                               latitude=safe_get(row, 'LAT'),
                               longitude=safe_get(row, 'LNG'),
                               description=safe_get(row, 'ITEMCNTNTS'),
                               contact=safe_get(row, 'CNTCT_TEL'),
                               traffic_info=safe_get(row, 'TRFC_INFO'))

        # Area 노드 추가 및 엣지 연결
        if area_id:
            add_node_if_not_exists(G, area_id, type='Area', name=area_name)
            add_edge_if_not_exists(G, attraction_id, area_id, type='LOCATED_IN')

        # (향후 확장) Feature, Landmark 노드 및 엣지 추가 로직
        # 예: ITEMCNTNTS 파싱하여 관련 정보 추출

    print("관광지 데이터 처리 완료.")

except FileNotFoundError:
    print(f"오류: 관광지 데이터 파일을 찾을 수 없습니다 - {ATTRACTION_DATA_PATH}")
except Exception as e:
    print(f"오류: 관광지 데이터 처리 중 예외 발생 - {e}")


# 2. 식당 데이터 처리 (공통 함수)
def process_restaurant_data(graph, file_path):
    print(f"식당 데이터 로딩: {file_path}")
    try:
        # 다양한 인코딩 시도
        try:
            df = pd.read_csv(file_path, encoding='utf-8', low_memory=False)
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding='cp949', low_memory=False)

        print(f"식당 데이터 {len(df)}개 처리 시작...")
        for index, row in df.iterrows():
            # 기본 정보 추출 및 ID 정의
            rstr_id_val = safe_get(row, 'RSTR_ID')
            if rstr_id_val is None: continue # 식당 ID 없으면 건너뛰기
            restaurant_id = f"restaurant_{int(rstr_id_val)}" # ID는 정수형으로 변환 후 사용

            raw_area_name = safe_get(row, 'AREA_NM')
            # '부산광역시 ' 제거 및 정규화
            cleaned_area_name = raw_area_name.replace('부산광역시', '').strip() if isinstance(raw_area_name, str) else None
            normalized_area_name = normalize_text(cleaned_area_name)
            area_id = f"area_{normalized_area_name}" if normalized_area_name else None

            raw_menu_name = safe_get(row, 'MENU_NM')
            normalized_menu_name = normalize_text(raw_menu_name)
            menu_id = f"menu_{normalized_menu_name}" if normalized_menu_name else None

            raw_landmark_name = safe_get(row, 'CRCMF_LDMARK_NM')
            normalized_landmark_name = normalize_text(raw_landmark_name)
            landmark_id = f"landmark_{normalized_landmark_name}" if normalized_landmark_name else None

            # Restaurant 노드 추가
            add_node_if_not_exists(graph, restaurant_id,
                                   type='Restaurant',
                                   name=safe_get(row, 'RSTR_NM'),
                                   address=safe_get(row, 'RSTR_RDNMADR'),
                                   category=safe_get(row, 'BSNS_STATM_BZCND_NM'),
                                   rating=safe_get(row, 'NAVER_GRAD'),
                                   description=safe_get(row, 'RSTR_INTRCN_CONT'),
                                   hours=safe_get(row, 'BSNS_TM_CN'),
                                   closed_days=safe_get(row, 'RESTDY_INFO_CN'))

            # Area 노드 추가 및 엣지 연결
            if area_id:
                add_node_if_not_exists(graph, area_id, type='Area', name=cleaned_area_name) # 정규화 전 이름 저장
                add_edge_if_not_exists(graph, restaurant_id, area_id, type='LOCATED_IN')

            # Menu 노드 추가 및 엣지 연결
            if menu_id:
                add_node_if_not_exists(graph, menu_id,
                                       type='Menu',
                                       name=raw_menu_name, # 정규화 전 이름 저장
                                       category=safe_get(row, 'MENU_CTGRY_LCLAS_NM'),
                                       sub_category=safe_get(row, 'MENU_CTGRY_SCLAS_NM'),
                                       description=safe_get(row, 'MENU_DSCRN'))
                add_edge_if_not_exists(graph, restaurant_id, menu_id,
                                       type='SERVES_MENU',
                                       price=safe_get(row, 'MENU_PRICE'))

            # Landmark 노드 추가 및 엣지 연결
            if landmark_id:
                add_node_if_not_exists(graph, landmark_id, type='Landmark', name=raw_landmark_name) # 정규화 전 이름 저장
                add_edge_if_not_exists(graph, restaurant_id, landmark_id,
                                       type='NEARBY_LANDMARK',
                                       distance=safe_get(row, 'CRCMF_LDMARK_DIST'))

            # Feature 노드 추가 및 엣지 연결
            features = {
                '주차가능': safe_get(row, 'PRKG_POS_YN') == 'Y',
                '와이파이가능': safe_get(row, 'WIFI_OFR_YN') == 'Y',
                '애견동반가능': safe_get(row, 'PET_ENTRN_POSBL_YN') == 'Y',
                # 필요시 다른 Feature 추가 (예: DCRN_YN - 장애인 편의시설)
            }
            for feature_name, has_feature in features.items():
                if has_feature:
                    feature_id = f"feature_{normalize_text(feature_name)}"
                    add_node_if_not_exists(graph, feature_id, type='Feature', name=feature_name)
                    add_edge_if_not_exists(graph, restaurant_id, feature_id, type='HAS_FEATURE')

        print(f"{os.path.basename(file_path)} 처리 완료.")

    except FileNotFoundError:
        print(f"오류: 식당 데이터 파일을 찾을 수 없습니다 - {file_path}")
    except Exception as e:
        print(f"오류: 식당 데이터 처리 중 예외 발생 ({os.path.basename(file_path)}) - {e}")


# 식당 데이터 파일 처리 실행
process_restaurant_data(G, RESTAURANT_7B_DATA_PATH)
process_restaurant_data(G, RESTAURANT_BFTS_DATA_PATH)


# 3. 그래프 저장
print("그래프 파일 저장 시작...")
try:
    # 저장 디렉토리 생성 (없으면)
    os.makedirs(GRAPH_OUTPUT_DIR, exist_ok=True)
    # nx.write_gpickle(G, GRAPH_OUTPUT_PATH) # 제거된 함수
    """
    - NetworkX 3.0 이상에서는 그래프 객체를 파일로 저장하고 읽기 위해 Python의 내장 pickle 모듈을 사용
        - 저장 : nx.write_gpickle(G, path) 대신 pickle.dump(G, open(path, 'wb')) 사용
        - 읽기 : nx.read_gpickle(path) 대신 pickle.load(open(path, 'rb')) 사용
    """
    with open(GRAPH_OUTPUT_PATH, 'wb') as f:
        pickle.dump(G, f, pickle.HIGHEST_PROTOCOL)
    print(f"그래프 저장 완료: {GRAPH_OUTPUT_PATH}")
    print(f"  - 노드 수: {G.number_of_nodes()}")
    print(f"  - 엣지 수: {G.number_of_edges()}")
except Exception as e:
    print(f"오류: 그래프 파일 저장 중 예외 발생 - {e}")

print("Knowledge Graph 생성 완료.")
