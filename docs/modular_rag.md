# Modular RAG: 라우터 패턴 구현 문서

## 1. 개요

이 문서는 부산 여행 정보 AI 서버의 Modular RAG 아키텍처의 핵심 구성 요소인 **라우터 패턴(Router Pattern)** 구현에 대한 기술적 설명을 제공합니다. 라우터 패턴은 사용자의 다양한 질문 의도를 파악하여 가장 적합한 정보 소스(예: 식당 벡터DB, 관광지 벡터DB, 일반 대화 모델 등)로 요청을 전달하는 역할을 수행합니다. 이를 통해 시스템은 더욱 복잡하고 다양한 질문에 효과적으로 대응할 수 있습니다.

본 구현은 LLM(Large Language Model)을 활용하여 사용자 쿼리와 대화 기록을 분석하고, 질문의 주된 카테고리를 'restaurant', 'attraction', 'general' 중 하나로 분류합니다.

## 2. 라우터 패턴 아키텍처

구현된 라우터 패턴은 다음과 같은 주요 구성 요소로 이루어집니다.

```
+------------------+      +-------------------------+      +-----------------+
|                  |      |                         |      |                 |
|  사용자 쿼리     +----->+  QueryRouterService     +----->+  분류된 카테고리 |
| (+ 대화 기록)    |      |  (LLM 기반 분류)        |      |  (예: "restaurant")|
|                  |      |                         |      |                 |
+------------------+      +-------------------------+      +-----------------+
       ↑                          |
       |                          | (FastAPI Depends)
+------------------+              |
|  FastAPI 라우터  |<-------------+
| (/route-test)    |
+------------------+
```

-   **`QueryRouterService`**: 사용자 쿼리와 대화 기록을 입력받아 LLM을 통해 분석하고, 적절한 카테고리(문자열)를 반환하는 핵심 서비스 로직입니다. (`ai-server/project/app/services/query_router.py`)
-   **FastAPI 라우터 (`/route-test`)**: `QueryRouterService`의 기능을 테스트하기 위한 API 엔드포인트입니다. FastAPI의 의존성 주입(Dependency Injection) 기능을 사용하여 `QueryRouterService` 인스턴스를 관리합니다. (`ai-server/project/app/routers/query_router.py`)
-   **LLM (gpt-4o-mini)**: OpenAI의 언어 모델을 사용하여 실제 쿼리 분류 작업을 수행합니다.

## 3. 구현 세부 정보

### 3.1. `QueryRouterService`

-   **초기화 (`__init__`)**:
    -   `ChatOpenAI` 모델 (기본값: "gpt-4o-mini") 인스턴스를 생성합니다.
    -   쿼리 분류를 위한 프롬프트 템플릿(`PromptTemplate`)을 정의합니다.
    -   `LLMChain`을 생성하여 LLM과 프롬프트를 연결합니다.
-   **프롬프트 템플릿 (`_define_routing_prompt`)**:
    -   LLM에게 명확한 지침과 분류할 카테고리 옵션(restaurant, attraction, general)을 제공합니다.
    -   입력 변수로 `query`와 `chat_history`를 사용합니다.
    ```python
    template = """다음 사용자 질문을 분석하여 가장 적합한 카테고리 하나를 선택해주세요.
    사용자의 이전 대화 내용은 문맥 파악에 참고할 수 있습니다.

    [대화 기록]
    {chat_history}

    [사용자 질문]
    {query}

    [카테고리 옵션]
    - restaurant: 사용자가 식당, 맛집, 음식, 카페 등 먹는 것과 관련된 장소나 정보를 찾고 있을 때 선택합니다.
    - attraction: 사용자가 관광 명소, 여행지, 공원, 해변, 박물관 등 볼거리나 즐길 거리를 찾고 있을 때 선택합니다.
    - general: 사용자가 일반적인 대화, 인사, 날씨, 교통, 숙소 등 위 카테고리에 속하지 않는 질문을 할 때 선택합니다.

    가장 적합한 카테고리 하나만 정확히 적어주세요 (restaurant, attraction, general 중 하나):"""
    ```
-   **대화 기록 포맷팅 (`_format_chat_history`)**:
    -   LangChain `LLMChain`에 적합한 형식으로 대화 기록(Tuple 리스트)을 변환합니다. (예: "사용자: 질문\nAI: 답변")
-   **라우팅 실행 (`route`)**:
    -   비동기(`async`)로 LLMChain을 실행하여 쿼리 분류를 요청합니다.
    -   LLM의 응답(예상 카테고리)을 파싱하고 소문자로 변환합니다.
    -   결과가 유효한 카테고리 (`restaurant`, `attraction`, `general`) 중 하나인지 확인하고 반환합니다.
    -   유효하지 않거나 오류 발생 시 기본값으로 "general"을 반환합니다.

### 3.2. API 엔드포인트 (`/route-test`)

-   **경로 및 메서드**: `POST /route-test`
-   **요청 본문 (`RouteRequest`)**: `query` (문자열, 필수)와 `chat_history` (튜플 리스트, 선택)를 포함합니다.
-   **응답 본문 (`RouteResponse`)**: 입력 `query`, 분류된 `category`, `chat_history` 길이를 반환합니다.
-   **의존성 주입 (`Depends`)**:
    -   FastAPI의 `Depends`를 사용하여 `get_query_router_service` 함수를 통해 `QueryRouterService` 인스턴스를 주입받습니다.
    -   이를 통해 서비스 인스턴스 생성을 라우터 코드와 분리하고 테스트 용이성을 높입니다.
    ```python
    # ai-server/project/app/routers/query_router.py
    from fastapi import Depends

    def get_query_router_service() -> QueryRouterService:
        # ... 서비스 인스턴스 생성 로직 ...
        return service_instance

    @router.post("/route-test", response_model=RouteResponse)
    async def test_routing_post(
        request: RouteRequest,
        service: QueryRouterService = Depends(get_query_router_service) # 서비스 주입
    ):
        category = await service.route(query=request.query, chat_history=request.chat_history)
        # ... 응답 생성 ...
    ```

## 4. 작동 흐름

1.  클라이언트가 `/route-test` 엔드포인트로 `query`와 `chat_history`를 포함한 POST 요청을 보냅니다.
2.  FastAPI는 `Depends(get_query_router_service)`를 통해 `QueryRouterService` 인스턴스를 가져옵니다. (필요시 생성)
3.  `test_routing_post` 함수는 주입받은 `service` 객체의 `route` 메서드를 호출합니다.
4.  `QueryRouterService`는 `chat_history`를 포맷하고, LLM(`gpt-4o-mini`)에게 프롬프트와 함께 쿼리 분류를 요청합니다.
5.  LLM은 가장 적합한 카테고리(예: "restaurant")를 반환합니다.
6.  `QueryRouterService`는 LLM 응답을 검증하고 최종 카테고리를 `test_routing_post` 함수에 반환합니다.
7.  API는 `RouteResponse` 형식으로 분류된 카테고리와 함께 클라이언트에게 응답합니다.

## 5. 통합 및 향후 계획

현재 구현된 라우터는 Modular RAG 시스템의 첫 단계입니다.

-   **통합**: 추후 이 라우터의 분류 결과("restaurant", "attraction", "general")를 사용하여 실제 해당 도메인의 서비스(`RestaurantService`, `AttractionService` 등) 또는 일반 대화 처리 로직으로 요청을 전달하는 로직이 추가될 것입니다. `/route-test`는 테스트용이며, 실제 사용자 인터페이스(예: Streamlit 챗봇)와 연동될 때는 다른 방식으로 라우터 서비스가 사용될 수 있습니다.
-   **향후 계획**:
    -   더 많은 카테고리 추가 (예: "transportation", "accommodation")
    -   쿼리 분류 정확도 향상을 위한 프롬프트 엔지니어링 및 LLM 모델 튜닝
    -   분류 불확실성 처리 로직 개선
    -   각 서비스(`RestaurantService` 등) 내부에 라우터 결과에 따른 분기 로직 통합

## 6. 제한 사항

-   **LLM 의존성**: 쿼리 분류 성능은 전적으로 LLM의 능력과 프롬프트 품질에 의존합니다. LLM이 잘못된 카테고리를 반환할 수 있습니다.
-   **제한된 카테고리**: 현재는 3개의 주요 카테고리만 지원합니다.
-   **테스트 API**: `/route-test`는 기능 테스트 목적이며, 실제 서비스 플로우와는 다를 수 있습니다.
-   **상태 비저장**: 현재 서비스 자체는 상태를 저장하지 않지만, 의존성 주입 방식을 사용함으로써 향후 상태 관리 필요시 유연하게 대처할 수 있습니다.

---

## 7. Graph RAG 구현

라우터 패턴 외에 Modular RAG 시스템의 또 다른 핵심 구성 요소는 **Graph RAG**입니다. Graph RAG는 지식 그래프(Knowledge Graph)를 활용하여 검색된 정보의 컨텍스트를 더욱 풍부하게 하고, 이를 통해 LLM의 응답 품질을 향상시키는 것을 목표로 합니다.

### 7.1. 개요

기존의 벡터 검색 기반 RAG는 문서 자체의 정보만을 활용하는 반면, Graph RAG는 문서 내의 주요 엔티티(장소, 인물, 개념 등)를 식별하고, 이 엔티티들이 지식 그래프 상에서 어떻게 연결되어 있는지를 파악하여 추가적인 관계 정보를 컨텍스트로 활용합니다. 예를 들어, 특정 식당을 검색했을 때 해당 식당이 어떤 지역에 있는지, 주변에 어떤 관광지가 있는지, 어떤 메뉴가 유명한지 등의 정보를 지식 그래프로부터 얻어 LLM에게 제공함으로써 더욱 깊이 있고 유용한 답변을 생성할 수 있도록 돕습니다.

### 7.2. Graph RAG 아키텍처

Graph RAG 시스템의 주요 구성 요소와 데이터 흐름은 다음과 같습니다.

```
+-----------------+     +-----------------+     +-----------------------+     +---------------------+     +-----------------+
|                 |     |                 |     |                       |     |                     |     |                 |
|  사용자 쿼리    +---->+  벡터 검색      +---->+  GraphRAGEnhancer     +---->+  LLM (컨텍스트 강화)  +---->+  최종 응답      |
| (챗봇/API)      |     | (기존 Retriever)|     | (엔티티추출, 그래프탐색)|     |                     |     |                 |
+-----------------+     +-----------------+     +-----------------------+     +---------------------+     +-----------------+
                                                       ↑
                                                       | (지식 그래프 로드)
                                             +-------------------------+
                                             |  KnowledgeGraphLoader   |
                                             | (knowledge_graph.gpickle)|
                                             +-------------------------+
```

-   **지식 그래프 생성 (`ai-preprocessing`)**:
    -   스크립트: `ai-preprocessing/project/script/create_knowledge_graph.py`
    -   데이터 소스: 정제된 관광지(`Attraction`), 식당(`Restaurant 7B`, `Restaurant BFTS`) CSV 파일 등 다양한 CSV 파일.
    -   결과: `ai-server/project/graphdb/knowledge_graph.gpickle` (NetworkX 그래프 객체를 직렬화한 파일)
-   **지식 그래프 로딩 (`KnowledgeGraphLoader`)**:
    -   모듈: `ai-server/project/app/utils/knowledge_graph_loader.py`
    -   역할: FastAPI 애플리케이션 시작 시 또는 필요에 따라 `knowledge_graph.gpickle` 파일을 로드하여 그래프 객체를 메모리에 적재하고, 애플리케이션 전역에서 접근 가능하도록 제공합니다.
-   **컨텍스트 강화 (`GraphRAGEnhancer`)**:
    -   모듈: `ai-server/project/app/utils/graph_rag_enhancer.py`
    -   역할:
        1.  벡터 검색을 통해 얻은 문서들에서 주요 엔티티(장소 이름, 유형 등)를 추출합니다.
        2.  추출된 엔티티를 `KnowledgeGraphLoader`를 통해 로드된 지식 그래프의 노드와 매핑합니다.
        3.  매핑된 노드를 중심으로 그래프를 탐색하여 관련된 추가 정보(예: 위치, 관계, 속성)를 수집합니다.
        4.  수집된 그래프 정보를 텍스트 형태의 컨텍스트로 가공합니다.
-   **LLM 응답 생성**:
    -   기존 검색 문서 내용과 `GraphRAGEnhancer`가 생성한 그래프 기반 컨텍스트를 함께 LLM 프롬프트에 포함시켜 질문에 대한 답변을 생성합니다.

### 7.3. 구현 세부 정보

#### 7.3.1. `ai-preprocessing/project/script/create_knowledge_graph.py`

-   **입력 데이터**: 부산 관광 정보(`Attraction`), 식당 정보(`7B_restaurants_STD.csv`, `BFTS_restaurants_STD.csv`) 등 다양한 CSV 파일.
-   **노드 유형**:
    -   `Attraction`: 관광지 (예: 해운대 해수욕장) - `id` (PREFIX_UC_SEQ), `name`, `type`, `description` 등 속성.
    -   `Restaurant`: 식당 (예: 개미집 본점) - `id` (PREFIX_RSTR_ID), `name`, `cuisine_type`, `description` 등 속성.
    -   `Area`: 지역 (예: 해운대구, 남포동)
    -   `Menu`: 메뉴 (예: 낙곱새)
    -   `Feature`: 특징 (예: "오션뷰", "애견동반가능")
    -   (필요에 따라 추가 노드 유형 정의)
-   **관계 유형**:
    -   `LOCATED_IN`: (Attraction/Restaurant) -[LOCATED_IN]-> (Area)
    -   `SERVES_MENU`: (Restaurant) -[SERVES_MENU]-> (Menu)
    -   `HAS_FEATURE`: (Attraction/Restaurant) -[HAS_FEATURE]-> (Feature)
    -   `NEARBY`: (Attraction) -[NEARBY]-> (Attraction), (Restaurant) -[NEARBY]-> (Restaurant), (Attraction) -[NEARBY]-> (Restaurant)
    -   (필요에 따라 추가 관계 유형 정의)
-   **구현**:
    -   `pandas`로 CSV 데이터를 읽고 전처리합니다.
    -   `networkx` 라이브러리를 사용하여 그래프 객체를 생성하고, 노드와 엣지를 추가합니다.
    -   각 노드와 엣지에는 분석에 필요한 속성들을 저장합니다.
    -   최종적으로 생성된 `networkx.Graph` 객체를 `pickle`을 사용하여 `ai-server/project/graphdb/knowledge_graph.gpickle` 파일로 저장합니다.

#### 7.3.2. `ai-server/project/app/utils/knowledge_graph_loader.py`

-   **`KnowledgeGraphLoader` 클래스**:
    -   `__init__(self, graph_path: str)`: 지식 그래프 파일 경로를 입력받습니다.
    -   `load_knowledge_graph(self) -> Optional[nx.Graph]`: 지정된 경로에서 `.gpickle` 파일을 로드하여 `networkx.Graph` 객체를 반환합니다. 파일이 없거나 로드에 실패하면 `None`을 반환하고 경고 로그를 남깁니다.
    -   `get_graph(self) -> Optional[nx.Graph]`: 로드된 그래프 객체를 반환하는 메서드. 그래프가 로드되지 않았으면 로드를 시도합니다. (싱글턴 패턴 또는 전역 변수를 활용하여 앱 전체에서 단일 인스턴스 유지)

#### 7.3.3. `ai-server/project/app/utils/graph_rag_enhancer.py`

-   **`GraphRAGEnhancer` 클래스**:
    -   `__init__(self, graph: Optional[nx.Graph])`: `KnowledgeGraphLoader`를 통해 얻은 `networkx.Graph` 객체를 주입받습니다.
    -   `async _extract_entities_from_docs(self, docs: List[Document]) -> List[Tuple[str, str, str, Dict[str, Any]]]`
        -   입력: LangChain `Document` 객체 리스트.
        -   처리: 각 문서의 메타데이터 (`UC_SEQ`, `RSTR_ID`, `content_id`, `MAIN_TITLE`, `TITLE`, `RSTR_NM`, `name` 등)와 `page_content` (정규식을 사용하여 `# 장소이름` 패턴 등)를 분석하여 엔티티 이름, 엔티티 유형 (`Attraction` 또는 `Restaurant`), 원본 ID (그래프 노드 ID와 매칭될 수 있는 ID)를 추출합니다.
        -   출력: `(엔티티_이름, 엔티티_유형, 원본_ID, 원본_문서_메타데이터)` 튜플 리스트.
    -   `_find_graph_node_for_entity(self, entity_name: str, entity_type: str, source_id: str) -> Optional[str]`
        -   입력: 추출된 엔티티 정보.
        -   처리: `source_id`를 기반으로 지식 그래프에서 해당 엔티티에 대응하는 노드 ID를 찾습니다. (예: `attraction_{UC_SEQ}`, `restaurant_{RSTR_ID}`). 이름과 유형도 보조적으로 활용할 수 있습니다.
        -   출력: 그래프 노드 ID (문자열) 또는 `None`.
    -   `_get_related_info_from_graph(self, node_id: str, depth: int = 1) -> str`
        -   입력: 그래프 노드 ID, 탐색 깊이.
        -   처리: 해당 노드와 지정된 깊이까지 연결된 이웃 노드들 및 관계 정보를 조회합니다. (예: "해운대 해수욕장 (관광지)은 해운대구에 위치하며, 근처에는 동백섬이 있습니다.")
        -   출력: 텍스트 형태로 요약된 관련 정보 문자열.
    -   `async get_graph_context_for_docs(self, docs: List[Document]) -> str`
        -   입력: 벡터 검색 결과 문서 리스트.
        -   처리: `_extract_entities_from_docs`로 엔티티를 추출하고, 각 엔티티에 대해 `_find_graph_node_for_entity`로 그래프 노드를 찾은 후, `_get_related_info_from_graph`로 관련 정보를 모아 하나의 통합된 그래프 컨텍스트 문자열을 생성합니다.
        -   출력: 최종 그래프 기반 컨텍스트 문자열.

#### 7.3.4. 서비스 레이어 통합 (`*ChatbotService.py`, `*GraphRAGService.py`)

-   **챗봇 서비스 (`RestaurantChatbotService`, `AttractionChatbotService`)**:
    -   기존 벡터 검색 후, `GraphRAGEnhancer`의 `get_graph_context_for_docs`를 호출하여 그래프 컨텍스트를 얻습니다.
    -   프롬프트 템플릿을 수정하여, 기존의 문서 기반 컨텍스트와 함께 그래프 컨텍스트를 LLM에게 제공합니다.
        ```python
        # 예시 프롬프트 일부
        # ...
        # 다음은 검색된 문서 내용입니다:
        # {retrieved_documents_context}
        #
        # 다음은 문서 내용과 관련된 추가적인 지식 그래프 정보입니다:
        # {graph_context}
        #
        # 위의 정보를 바탕으로 사용자의 질문에 답변해주세요.
        # ...
        ```
-   **Graph RAG API 서비스 (`RestaurantGraphRAGService`, `AttractionGraphRAGService`)**:
    -   기존 운영 API(`ai-server/project/app/services/restaurant.py`, `attraction.py`)와 동일한 입력/출력 스키마를 유지합니다.
    -   내부적으로 `GraphRAGEnhancer`를 사용하여 그래프 컨텍스트를 생성하고, 이를 LLM 프롬프트에 포함시켜 JSON 응답을 생성합니다.
    -   예를 들어, `RestaurantGraphRAGService`는 `search` 메서드 내에서 벡터 검색 결과와 함께 그래프 컨텍스트를 생성하여 LLM에게 전달하고, LLM은 이를 바탕으로 `RestaurantResponse` 스키마에 맞는 JSON 응답을 생성합니다.

### 7.4. 작동 흐름

1.  **사용자 요청**: 사용자가 챗봇 인터페이스를 통해 질문하거나, 클라이언트가 Graph RAG API 엔드포인트 (예: `POST /api/v1/restaurant_graph_rag/search`)로 요청을 보냅니다.
2.  **라우팅 (챗봇의 경우)**: `ai-server/project/app/routers/query_router.py`의 `/route-test` 엔드포인트는 `QueryRouterService`를 통해 요청을 적절한 챗봇 서비스(`RestaurantChatbotService` 또는 `AttractionChatbotService`)로 전달합니다.
3.  **벡터 검색**: 해당 서비스는 기존의 벡터 검색기(예: FAISS 기반 Retriever, Advanced RAG Retriever)를 사용하여 사용자 쿼리와 관련된 문서를 검색합니다.
4.  **엔티티 추출 및 그래프 탐색**: 서비스는 `GraphRAGEnhancer` 인스턴스의 `get_graph_context_for_docs` 메서드를 호출하여 검색된 문서들로부터 그래프 기반 컨텍스트를 생성합니다.
    -   `GraphRAGEnhancer`는 내부적으로 `KnowledgeGraphLoader`를 통해 로드된 지식 그래프를 사용합니다.
5.  **프롬프트 구성**: 서비스는 검색된 문서의 내용과 `GraphRAGEnhancer`가 생성한 그래프 컨텍스트를 결합하여 LLM에게 전달할 프롬프트를 구성합니다.
6.  **LLM 응답 생성**: LLM은 강화된 컨텍스트를 바탕으로 사용자의 질문에 대한 답변을 생성합니다.
    -   챗봇 서비스의 경우: 자연어 텍스트 응답 및 출처 정보.
    -   Graph RAG API 서비스의 경우: 기존 API와 동일한 JSON 형식의 응답.
7.  **응답 반환**: 생성된 응답이 사용자 또는 클라이언트에게 반환됩니다.

### 7.5. 통합 및 향후 계획

-   **현재 상태**:
    -   `RestaurantChatbotService`와 `AttractionChatbotService`에 Graph RAG 기능이 통합되어 챗봇 응답 품질 개선에 활용됩니다.
    -   기존 운영 API(`restaurant.py`, `attraction.py`)를 대체하기 위한 새로운 Graph RAG API 라우터(`restaurant_graph_rag_router.py`, `attraction_graph_rag_router.py`) 및 서비스(`restaurant_graph_rag_service.py`, `attraction_graph_rag_service.py`)가 개발되어 동일한 입출력 형식으로 더 풍부한 컨텍스트 기반의 응답을 제공합니다.
    -   `ai-server/project/app/main.py`에 신규 Graph RAG 라우터들이 등록되어 API로 접근 가능합니다.
-   **향후 계획**:
    -   **지식 그래프 확장**: 더 다양한 데이터 소스(예: 숙박, 교통 정보)를 통합하여 지식 그래프의 커버리지를 넓힙니다.
    -   **그래프 업데이트 자동화**: 주기적으로 원본 데이터를 반영하여 지식 그래프를 자동으로 업데이트하는 파이프라인 구축.
    -   **엔티티 추출 및 매핑 정확도 개선**: NER(Named Entity Recognition) 모델 개선, 동의어 처리, 모호성 해결 로직 강화 등을 통해 엔티티 추출 및 그래프 노드 매핑 정확도를 높입니다.
    -   **고급 그래프 탐색 전략**: 단순한 이웃 노드 탐색을 넘어, 다중 홉(multi-hop) 추론, 경로 탐색 등 고급 그래프 탐색 알고리즘을 적용하여 더 복잡한 질문에 답할 수 있도록 합니다.
    -   **사용자 피드백 반영**: 사용자의 피드백을 수집하여 지식 그래프의 정확성을 검증하고 개선합니다.

### 7.6. 제한 사항

-   **데이터 의존성**: 지식 그래프의 품질과 최신성은 Graph RAG 성능에 직접적인 영향을 미칩니다. 부정확하거나 오래된 정보는 잘못된 컨텍스트를 제공할 수 있습니다.
-   **엔티티 추출의 한계**: 문서에서 엔티티를 정확하게 추출하고 그래프 노드와 올바르게 매핑하는 것은 어려운 작업이며, 오류가 발생할 수 있습니다.
-   **관계 표현의 복잡성**: 현실 세계의 복잡한 관계를 지식 그래프로 모두 표현하는 데에는 한계가 있을 수 있습니다.
-   **계산 비용**: 그래프 탐색 및 컨텍스트 생성 과정에서 추가적인 계산 비용이 발생할 수 있습니다.
-   **콜드 스타트 문제**: 지식 그래프에 정보가 거의 없는 새로운 엔티티에 대해서는 Graph RAG의 효과가 미미할 수 있습니다.
