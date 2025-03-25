# Advanced RAG 구현 문서

## 개요

이 문서는 부산 여행 정보 AI 서버의 Advanced RAG(Retrieval-Augmented Generation) 시스템 구현에 대한 기술적 설명을 제공합니다. 기존의 Naive RAG 시스템에서 Reranker와 하이브리드 검색(TMM-CC)을 추가하여 성능을 개선한 내용을 중심으로 다룹니다.

## Advanced RAG 아키텍처

Advanced RAG 시스템은 Naive RAG의 한계를 극복하기 위해 다음과 같이 개선된 구조로 구현되었습니다:

```
+------------------+     +--------------------+     +------------------+     +------------------+
|                  |     |                    |     |                  |     |                  |
|  사용자 쿼리     +---->+ 하이브리드 검색    +---->+   리랭킹(Reranker) +---->+  LLM 응답 생성   |
|                  |     | (TMM-CC, α=0.8)    |     |                  |     |                  |
+------------------+     +--------------------+     +------------------+     +------------------+
```

### 주요 개선 사항

1. **하이브리드 검색(TMM-CC) 추가**: 키워드 검색(BM25)과 의미 검색(벡터 검색)을 결합하여 검색 성능 향상
2. **리랭킹(Reranking) 단계 적용**: 검색 결과를 관련성에 따라 재정렬하여 더 정확한 문서 선택
3. **검색 효율성 향상**: 초기에 더 많은 문서(initial_k)를 검색하고, 리랭킹 후 최종 결과(final_k)를 선별
4. **다국어 지원 Reranker**: 한국어 문서에 최적화된 리랭킹 모델 사용
5. **오류 처리 개선**: 각 단계에서의 예외 처리를 통해 시스템 안정성 증대

## TMM-CC 하이브리드 검색 구현

### 1. 하이브리드 검색의 필요성

기존의 단일 검색 방식은 특정 상황에서 한계를 가집니다:

- **벡터 검색(의미 검색)**: 의미적 유사성을 잘 포착하지만 정확한 키워드 매칭에 약할 수 있음
- **키워드 검색(BM25)**: 정확한 용어 매칭에 강하지만 유사 개념이나 의미론적 관계 파악에 제한적

이러한 한계를 극복하기 위해 두 검색 방법의 장점을 결합한 하이브리드 검색을 구현했습니다.

### 2. TMM 정규화 (Top-Min-Max Normalization)

서로 다른 검색 방법은 점수 분포와 범위가 달라 단순 결합이 어렵습니다. TMM 정규화는 이러한 문제를 해결하기 위한 방법으로, 다음과 같이 작동합니다:

1. 최소값(min_score)을 찾습니다.
2. 상위 k개(기본값 3) 점수의 평균을 최대값(max_score)으로 설정합니다.
3. 각 점수를 (score - min_score) / (max_score - min_score) 공식으로 정규화합니다.

이 방식은 이상치(outlier)의 영향을 줄이고 안정적인 정규화를 제공합니다.

### 3. CC (Convex Combination) 가중치 적용

정규화된 점수를 결합하기 위해 CC 방식을 사용합니다:

```
H = (1-α)K + αV
```

여기서:
- H: 최종 하이브리드 점수
- α: 벡터 검색 가중치 (0.0~1.0)
- K: 키워드 검색 점수
- V: 벡터 검색 점수

논문 연구 결과에 따라 α=0.8로 설정하여 벡터 검색에 80%, 키워드 검색에 20%의 가중치를 부여했습니다.

### 4. 구현 클래스: TMMCC_HybridSearch

`TMMCC_HybridSearch` 클래스는 다음과 같은 주요 메서드를 포함합니다:

- `__init__()`: 벡터 DB, 문서 리스트, 알파 값 등으로 검색기 초기화
- `search()`: 주어진 쿼리로 하이브리드 검색 수행
- `_combine_results()`: 벡터 검색과 키워드 검색 결과 결합
- `_tmm_normalize()`: TMM 정규화 적용
- `_estimate_bm25_scores()`: BM25 점수 추정 및 정규화

## Reranker 구현 및 작동 방식

### Reranker 개념

Reranker는 초기 검색 결과를 재평가하여 더 관련성이 높은 문서를 상위로 재정렬하는 컴포넌트입니다. 이를 통해 단순한 벡터 유사도 검색의 한계를 극복하고, 사용자 의도에 더 적합한 문서를 선택할 수 있습니다.

### KoreanReranker 클래스

부산 여행 정보 AI 서버에서는 한국어 문서에 최적화된 `KoreanReranker` 클래스를 구현하여 사용합니다:

```python
class KoreanReranker:
    """
    한국어 문서를 위한 리랭커 클래스.
    Jina AI의 다국어 Reranker 모델을 사용하여 검색 결과를 재정렬합니다.
    """
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", top_k: int = 5):
        # 모델 초기화 코드...
        
    def rerank(self, query: str, documents: List[Document]) -> List[Document]:
        # 리랭킹 로직...
```

### 모델 선택 및 로딩 전략

KoreanReranker는 다음과 같은 특성을 갖습니다:

1. **다국어 지원 모델 우선 시도**: 기본값으로 `cross-encoder/ms-marco-MiniLM-L-6-v2` 모델 사용
2. **순차적 대체 모델 시도**: 기본 모델 로드 실패 시 더 가벼운 `cross-encoder/ms-marco-MiniLM-L-4-v2` 모델 시도
3. **Graceful Fallback**: 모든 모델 로드 실패 시 초기 검색 결과를 그대로 사용하는 안전 메커니즘

### 리랭킹 프로세스

1. 사용자 쿼리와 각 문서 페어 생성
2. CrossEncoder 모델을 통해 각 페어의 관련성 점수 계산
3. 점수에 따라 문서 내림차순 정렬
4. 상위 k개 문서만 선택하여 반환

## 하이브리드 검색과 리랭커의 통합

하이브리드 검색과 리랭커를 결합하여 최상의 검색 결과를 얻기 위해 다음과 같은 단계로 처리합니다:

1. 하이브리드 검색(TMM-CC)으로 초기 검색 결과 얻기
2. 검색 결과를 리랭커로 재정렬
3. 최종 결과를 LLM에 전달하여 응답 생성

이러한 통합 검색 프로세스는 `BaseService` 클래스에 구현되어 모든 서비스에서 활용할 수 있습니다.

## 하이브리드 검색 구현 상세

### 클래스 계층 구조와 래퍼 패턴

하이브리드 검색은 다음과 같은 구성 요소로 이루어져 있습니다:

1. **TMMCC_HybridSearch**: 핵심 하이브리드 검색 알고리즘 구현 (벡터 검색 + 키워드 검색)
2. **HybridSearchRetriever**: LangChain의 `BaseRetriever` 인터페이스를 준수하는 래퍼 클래스
3. **AdvancedRAGRetriever**: 하이브리드 검색 결과를 Reranker로 추가 개선하는 고급 리트리버

이러한 계층적 구조를 통해 기존 코드와의 호환성을 유지하면서 검색 기능을 확장할 수 있습니다.

### HybridSearchRetriever 래퍼

`HybridSearchRetriever` 클래스는 `TMMCC_HybridSearch` 객체를 래핑하여 LangChain 리트리버 인터페이스를 제공합니다:

```python
class HybridSearchRetriever(BaseRetriever):
    """
    하이브리드 검색(벡터 + 키워드) 래퍼 리트리버
    """
    # Pydantic 모델에서는 모든 필드를 미리 선언해야 함
    hybrid_search_obj: Any = Field(default=None, description="하이브리드 검색 객체")
    hybrid_search: Any = Field(default=None, description="하이브리드 검색 호환성용 별칭")
    
    def __init__(self, hybrid_search_obj: Any, **kwargs):
        # 초기화 코드...
    
    def _get_relevant_documents(self, query: str) -> List[Document]:
        # 문서 검색 로직...
    
    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        # 비동기 문서 검색 로직...
```

이 래퍼 클래스는 `hybrid_search_obj` 및 `hybrid_search` 필드를 Pydantic 모델에 명시적으로 선언하여 초기화 시 호환성 문제를 방지합니다.

### TMMCC_HybridSearch 구현

핵심 하이브리드 검색 알고리즘은, `TMMCC_HybridSearch` 클래스에 구현되어 있습니다:

```python
class TMMCC_HybridSearch:
    """
    TMM(Top-Min-Max) 정규화와 CC(Convex Combination) 방식의 하이브리드 검색 클래스.
    """
    
    def __init__(self, vectordb, documents: List[Document], alpha: float = 0.8, top_k: int = 20):
        self.vectordb = vectordb
        self.bm25 = BM25Retriever.from_documents(documents)
        self.alpha = alpha
        self.top_k = top_k
        # 초기화 코드...
    
    def search(self, query: str, limit: int = 20) -> List[Document]:
        # 하이브리드 검색 로직...
```

이 클래스는 다음 단계로 검색을 수행합니다:

1. 벡터 검색 (의미적 유사성 기반)과 키워드 검색(BM25) 각각 실행
2. 각 검색 결과를 문서 ID 기준으로 매핑
3. 두 검색 결과의 점수를 순위 기반으로 정규화
4. α=0.8 가중치로 두 점수를 결합 (벡터 80%, 키워드 20%)
5. 최종 점수에 따라 정렬 및 상위 문서 반환

### 오류 처리 및 Graceful Fallback

하이브리드 검색 구현에서는 다양한 예외 상황에 대비한 오류 처리 메커니즘을 제공합니다:

1. **벡터 검색만 실패**: 키워드 검색 결과만 반환
2. **키워드 검색만 실패**: 벡터 검색 결과만 반환
3. **모든 검색 실패**: 안전하게 빈 결과 반환
4. **하이브리드 점수 계산 실패**: 기본 벡터 검색 결과 반환 시도

이러한 강화된 오류 처리는 시스템 안정성을 높이고 사용자에게 일관된 경험을 제공합니다.

### 통합 검색 흐름

전체 검색 프로세스는 다음과 같은 순서로 진행됩니다:

1. `BaseService` 클래스 초기화 시 하이브리드 검색과 리랭커 설정
2. 사용자 쿼리 수신 시 하이브리드 검색 수행 (`HybridSearchRetriever` 통해)
3. 하이브리드 검색 결과를 리랭커로 추가 개선 (`AdvancedRAGRetriever` 통해)
4. 최종 검색 결과를 LLM에 컨텍스트로 제공하여 응답 생성

## 성능 개선 효과

Advanced RAG 구현을 통해 얻은 주요 개선 효과는 다음과 같습니다:

1. **키워드 검색 강화**: 정확한 용어 매칭이 중요한 쿼리(주소, 식당명 등)에 더 정확한 결과 제공
2. **의미 검색 보완**: 유사 개념이나 의미적 관계가 중요한 쿼리에 더 관련성 높은 결과 제공
3. **검색 다양성 향상**: 서로 다른 검색 방식의 결합으로 다양한 관점의 결과 제공
4. **오류 복원력 강화**: 각 단계에서의 예외 처리를 통해 시스템 안정성 증대
5. **응답 품질 개선**: LLM에 더 관련성 높은 컨텍스트 제공으로 생성된 응답의 품질 향상

## 구현 과정에서의 문제 해결

하이브리드 검색 구현 과정에서 다음과 같은 기술적 문제들을 해결했습니다:

1. **Pydantic 모델 호환성**: `BaseRetriever`가 Pydantic 모델을 사용하기 때문에 필드 선언이 필요했습니다. 명시적으로 `hybrid_search_obj`와 `hybrid_search` 필드를 선언하여 초기화 오류를 해결했습니다.

2. **다양한 인터페이스 지원**: 리트리버의 다양한 인터페이스(`invoke`, `get_relevant_documents`, `ainvoke`, `aget_relevant_documents`)를 모두 지원하도록 구현했습니다.

3. **래퍼 클래스 구조**: 복잡한 검색 로직을 캡슐화하여 `BaseRetriever` 인터페이스를 준수하는 래퍼 클래스를 구현했습니다.

### 하이브리드 검색 알파 값(0.8) 선택 근거

현재 구현에서는 α=0.8로 설정하여 벡터 검색에 80%, 키워드 검색에 20%의 가중치를 부여하고 있습니다. 이 값의 선택 근거는 다음과 같습니다:

1. **문헌 참고**: TMM-CC 관련 논문과 연구에서는 대부분의 일반적 사용 사례에서 α=0.8 범위가 최적임을 확인


## 다중 도메인 지원

현재 Advanced RAG 시스템은 다음 도메인을 지원합니다:

1. **레스토랑 도메인 (RestaurantService)**:
   - 부산 지역 레스토랑 및 음식점 정보 검색
   - 음식테마거리 정보 제공

2. **관광지 도메인 (AttractionService)**:
   - 부산 지역 관광지 및 명소 정보 검색
   - 인기 방문 장소 추천

각 도메인별 서비스는 동일한 Advanced RAG 아키텍처를 공유하지만, 특화된 벡터 DB와 프롬프트 템플릿을 사용합니다. 하이브리드 검색과 리랭킹은 모든 도메인에서 일관되게 적용되어 검색 품질을 향상시킵니다.

## 결론 및 평가

하이브리드 검색(TMM-CC)과 리랭커의 추가로 Advanced RAG 시스템은 다음과 같은 성과를 보여줍니다:

1. **검색 정확도 향상**: 의미적 유사성과 키워드 매칭을 균형 있게 고려하여 더 관련성 높은 문서 검색
2. **다양성 제공**: 다양한 검색 방식의 결합으로 단일 검색 방식에서 놓칠 수 있는 관련 문서까지 포함
3. **시스템 안정성**: 다양한 오류 처리 메커니즘 구현으로 시스템 견고성 향상
4. **다중 도메인 지원**: 동일한 검색 아키텍처를 다양한 도메인에 적용

Advanced RAG 시스템 개발을 통해 단순 벡터 검색의 한계를 넘어 보다 지능적인 정보 검색 시스템을 구현했으며, 이는 부산 여행 정보 제공의 품질을 크게 향상시켰습니다. 추후 업그레이드 계획에 따라 의미론적 쿼리 확장 및 에이전트 시스템 구현 등을 통해 더욱 발전된 시스템으로 확장할 예정입니다. 