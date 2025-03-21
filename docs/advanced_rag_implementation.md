# Advanced RAG 구현 문서

## 개요

이 문서는 부산 여행 정보 AI 서버의 Advanced RAG(Retrieval-Augmented Generation) 시스템 구현에 대한 기술적 설명을 제공합니다. 기존의 Naive RAG 시스템에서 Reranker를 추가하여 성능을 개선한 내용을 중심으로 다룹니다.

## Advanced RAG 아키텍처

Advanced RAG 시스템은 Naive RAG의 한계를 극복하기 위해 다음과 같이 개선된 구조로 구현되었습니다:

```
+------------------+     +------------------+     +------------------+     +------------------+
|                  |     |                  |     |                  |     |                  |
|  사용자 쿼리     +---->+ 벡터 검색 (FAISS) +---->+   리랭킹(Reranker) +---->+  LLM 응답 생성   |
|                  |     |                  |     |                  |     |                  |
+------------------+     +------------------+     +------------------+     +------------------+
```

### 주요 개선 사항

1. **리랭킹(Reranking) 단계 추가**: 초기 벡터 검색 결과를 관련성에 따라 재정렬하여 더 정확한 문서 선택
2. **검색 효율성 향상**: 초기에 더 많은 문서(initial_k)를 검색하고, 리랭킹 후 최종 결과(final_k)를 선별
3. **다국어 지원 Reranker**: 한국어 문서에 최적화된 리랭킹 모델 사용
4. **오류 처리 개선**: 리랭커 로드 실패 시 대체 모델 시도 및 예외 처리 강화

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

## AdvancedRAGRetriever 구현

AdvancedRAGRetriever 클래스는 기본 검색과 리랭킹을 결합한 향상된 검색 기능을 제공합니다:

```python
class AdvancedRAGRetriever:
    """
    Reranker를 활용한 향상된 RAG 검색 클래스.
    초기 벡터 검색 결과를 한국어 Reranker로 재정렬하여 더 관련성 높은 문서를 반환합니다.
    """
    
    def __init__(self, base_retriever, reranker=None, initial_k=20, final_k=20):
        # 초기화 코드...
    
    async def aretrieve(self, query: str) -> List[Document]:
        # 비동기 검색 및 리랭킹 코드...
    
    def retrieve(self, query: str) -> List[Document]:
        # 동기식 검색 및 리랭킹 코드...
```

### 주요 기능

1. **초기 검색**: 기본 벡터 검색기를 통해 initial_k개의 문서 검색
2. **리랭킹**: 검색된 문서를 Reranker를 통해 재정렬
3. **결과 정제**: 상위 final_k개 문서만 최종 반환
4. **오류 처리**: 검색 또는 리랭킹 단계에서 오류 발생 시 기본 검색 결과 반환

## 서비스 계층 통합

이 개선된 검색 기능은 BaseService 클래스에 통합되어 모든 서비스에서 활용할 수 있습니다:

```python
class BaseService:
    def __init__(
        self, 
        vectordb_name: str, 
        model_name: str = "gpt-4o-mini", 
        temperature: float = 0.2,
        use_reranker: bool = True,
        initial_k: int = 20,
        final_k: int = 20
    ):
        # BaseService 초기화 코드...
        
        # Reranker 사용 여부에 따라 검색기 설정
        if use_reranker:
            try:
                self.retriever = create_advanced_rag_retriever(
                    base_retriever=self.base_retriever,
                    initial_k=initial_k,
                    final_k=final_k
                )
                # 성공 로그...
            except Exception as e:
                # 실패 시 기본 검색기 사용...
        else:
            self.retriever = self.base_retriever
```

## 성능 개선 효과

Advanced RAG 구현을 통해 얻은 주요 개선 효과는 다음과 같습니다:

1. **검색 정확도 향상**: 단순 벡터 유사도 검색보다 의미론적으로 더 관련된 문서 선택
2. **응답 품질 개선**: LLM에 더 관련성 높은 컨텍스트 제공으로 생성된 응답의 품질 향상
3. **오류 복원력 강화**: 각 단계에서의 예외 처리를 통해 시스템 안정성 증대
4. **유연한 구성**: 초기 검색 수와 최종 반환 수를 조절할 수 있는 유연한 설계

## 코드 변경 사항

### 새로 추가된 파일

- `app/utils/advanced_rag.py`: Advanced RAG 검색 클래스 및 유틸리티 함수
- `app/utils/reranker.py`: 한국어 문서 리랭킹을 위한 KoreanReranker 클래스

### 수정된 파일

- `app/services/base.py`: Reranker 통합 지원을 위한 BaseService 클래스 수정
- `app/services/restaurant.py`: Advanced RAG 활용을 위한 서비스 로직 수정
- `app/services/attraction.py`: Advanced RAG 활용을 위한 서비스 로직 수정
- `Dockerfile`: Hugging Face 모델 캐시 경로 설정 추가
- `requirements.txt`: sentence-transformers 의존성 추가

## 향후 개선 방향

현재 구현된 Advanced RAG 시스템의 다음 단계 개선 계획:

1. **하이브리드 검색 구현**: 키워드 검색과 의미론적 검색을 결합한 하이브리드 검색 방식 도입
2. **의미론적 쿼리 확장**: 사용자 쿼리를 확장하여 검색 범위 개선
3. **다중 벡터 스토어 통합**: 식당, 관광지, 숙소 등 도메인별 특화된 벡터 DB 구현
4. **에이전트 시스템 구현**: 외부 API 통합 및 LangChain 에이전트 활용

이러한 개선 사항들은 `Upgrade Plan.md`에 명시된 로드맵에 따라 단계적으로 구현될 예정입니다. 