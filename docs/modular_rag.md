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
