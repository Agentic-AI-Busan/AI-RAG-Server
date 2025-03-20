# Naive RAG 구현 문서

## 개요

이 문서는 부산 여행 정보 AI 서버의 Naive RAG(Retrieval-Augmented Generation) 시스템 구현에 대한 기술적 설명을 제공합니다. 현재 시스템은 기본적인 RAG 아키텍처를 활용하여 사용자의 텍스트 쿼리에 맞는 부산 관련 정보를 검색하고 응답합니다.

## 현재 시스템 아키텍처

현재 구현된 Naive RAG 시스템은 다음과 같은 구조로 되어 있습니다:

```
+------------------+     +------------------+     +------------------+
|                  |     |                  |     |                  |
|  사용자 쿼리     +---->+  벡터 검색 (FAISS) +---->+  LLM 응답 생성   |
|                  |     |                  |     |                  |
+------------------+     +------------------+     +------------------+
```

### 주요 구성 요소

1. **FastAPI 서버**: 백엔드 API 서버로 사용자 요청을 처리합니다.
2. **벡터 데이터베이스(FAISS)**: 정제된 부산 여행 정보를 임베딩 벡터로 저장합니다.
3. **LLM(Large Language Model)**: 검색된 정보를 바탕으로 자연어 응답을 생성합니다.

## 데이터 흐름

1. **데이터 준비 및 전처리 (ai-preprocessing)**:
   - 음식테마거리 데이터를 요약 및 마크다운 형식으로 정제하여 CSV 파일로 저장
   - `ai-preprocessing/project/script/create_restaurant_vectordb.py`를 통해 벡터DB 생성
   - 생성된 벡터DB(FAISS 인덱스)는 `ai-server/project/vectordb/restaurant_finder`로 이동

2. **API 요청 처리 (ai-server)**:
   - 사용자가 `/api/v1/restaurants/search?query="부산고기맛집 추천"` 형식으로 요청
   - `ai-server/project/app/routers/restaurant.py`에서 요청을 받아 서비스 레이어로 전달

3. **검색 및 응답 생성 (ai-server)**:
   - `ai-server/project/app/services/restaurant.py`에서 벡터DB를 활용해 관련 정보 검색
   - 검색된 정보와 사용자 쿼리를 기반으로 LLM을 통해 응답 생성
   - JSON 형태로 결과 반환

## 코드 구조 및 주요 모듈

### 라우터(Routers)
`ai-server/project/app/routers/restaurant.py`에서 API 엔드포인트를 정의하여 URL을 설정합니다.

```python
@router.get("/search")
async def search_restaurants(query: str):
    return await restaurant_service.search_restaurants(query)
```

### 서비스(Services)
`ai-server/project/app/services/base.py`와 `ai-server/project/app/services/restaurant.py`에서 핵심 RAG 로직을 구현합니다.

- `base.py`: 모든 서비스의 기본 클래스 정의, 벡터DB 로드 기능 포함
  ```python
  class BaseService:
      def __init__(self, vectordb_name):
          self.vectorstore = load_vectordb(vectordb_name)
  ```

- `restaurant.py`: 레스토랑 검색 및 응답 생성 로직
  ```python
  class RestaurantService(BaseService):
      def __init__(self):
          super().__init__(vectordb_name="restaurant_finder")
      
      async def search_restaurants(self, query: str):
          # 벡터 DB 검색 수행
          docs = self.vectorstore.similarity_search(query)
          
          # 프롬프트 구성 및 LLM 요청
          prompt = self._create_prompt(query, docs)
          response = self.llm(prompt)
          
          return response
  ```

### 유틸리티(Utils)
`ai-server/project/app/utils/vectordb.py`에서 벡터DB 접근 및 관리 기능을 제공합니다.

```python
def load_vectordb(index_name: str):
    vectorstore = FAISS.load_local(
        f"vectordb/{index_name}",
        embeddings=OpenAIEmbeddings()
    )
    return vectorstore
```

## 프로젝트 구조

프로젝트는 크게 두 부분으로 나뉩니다:

1. **ai-preprocessing**: 데이터 전처리 및 벡터 DB 생성
   - `Dockerfile`: 전처리 환경을 위한 Docker 설정
   - `requirements.txt`: 필요한 Python 패키지
   - `project/script/create_restaurant_vectordb.py`: 레스토랑 벡터 DB 생성 스크립트

2. **ai-server**: 실제 API 서비스 제공
   - `Dockerfile` 및 `entrypoint.sh`: 서버 환경 설정
   - `requirements.txt`: 필요한 Python 패키지
   - `project/app`: API 서버 코드 (FastAPI)
   - `project/vectordb`: 생성된 벡터 DB 저장 위치

## 현재 데이터 상태

- 현재는 음식테마거리 데이터만 정제되어 벡터DB로 구축됨
- 원본 데이터는 전처리 과정을 통해 정제됨
- 벡터DB는 `ai-server/project/vectordb/restaurant_finder/`에 `index.faiss` 및 `index.pkl` 파일로 저장됨
- `ai-preprocessing`에서 생성된 벡터DB를 `ai-server`로 가져와 실제 추론에 사용

## Naive RAG의 제한사항

현재 구현된 Naive RAG 방식은 다음과 같은 제한사항이 있습니다:

1. **단순 검색**: 기본적인 유사도 기반 검색만 수행하여 최적의 문서를 찾지 못할 수 있음
2. **단일 도메인**: 현재는 레스토랑 정보만 제공하며 다양한 여행 정보를 통합하지 못함
3. **정적 프롬프트**: 고정된 프롬프트 템플릿을 사용하여 다양한 쿼리 유형에 유연하게 대응하지 못함
4. **대화 컨텍스트 부재**: 이전 대화 기록을 기억하지 못하는 무상태(stateless) 방식으로 구현됨

## 향후 업그레이드 방향

Naive RAG에서 다음 단계로 발전하기 위한 계획:

1. **Advanced RAG**: 재순위화, 하이브리드 검색, 의미론적 쿼리 확장, 응답 품질 개선 등
2. **Modular RAG**: 다중 벡터 스토어 통합, 라우터 패턴 구현, 그래프 기반 RAG 등
3. **에이전트 시스템**: 외부 API 통합, LangChain 에이전트 구현, 여행 계획 생성 기능 등

이러한 업그레이드는 `Upgrade Plan.md`에 자세히 명시되어 있으며, 단계적으로 구현할 예정입니다. 