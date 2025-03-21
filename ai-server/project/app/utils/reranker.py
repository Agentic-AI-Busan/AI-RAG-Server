from typing import List, Dict, Any
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder


class KoreanReranker:
    """
    한국어 문서를 위한 리랭커 클래스.
    Jina AI의 다국어 Reranker 모델을 사용하여 검색 결과를 재정렬합니다.
    """
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", top_k: int = 5):
        """
        리랭커 초기화

        Args:
            model_name (str): 사용할 리랭커 모델 이름
            top_k (int): 리랭킹 후 반환할 문서 수
        """
        self.model_loaded = False
        self.top_k = top_k
        
        # 모델 로드 시도 순서 (실패 시 다음 모델로 시도)
        models_to_try = [
            model_name,  # 첫 번째: 지정된 모델 (default: 다국어 지원 일반 모델)
            "cross-encoder/ms-marco-MiniLM-L-4-v2"   # 두 번째: 더 가벼운 모델
        ]
        
        # 모델 순차적으로 로드 시도
        for model_id in models_to_try:
            try:
                print(f"리랭커 모델 로드 시도: {model_id}")
                self.model = CrossEncoder(model_id, max_length=512)
                self.model_loaded = True
                print(f"리랭커 모델 로드 성공: {model_id}")
                break  # 성공하면 루프 종료
            except Exception as e:
                print(f"모델 {model_id} 로드 실패: {e}")
                continue
        
        if not self.model_loaded:
            print("모든 리랭커 모델 로드 실패. 기본 정렬 사용")
    
    def rerank(self, query: str, documents: List[Document]) -> List[Document]:
        """
        쿼리와 문서 리스트를 받아 관련성에 따라 문서를 재정렬합니다.

        Args:
            query (str): 사용자 쿼리
            documents (List[Document]): 재정렬할 문서 리스트

        Returns:
            List[Document]: 재정렬된 문서 리스트 (상위 top_k개)
        """
        if not documents:
            return []
        
        # 모델 로드 실패 시 원본 문서 그대로 반환 (top_k 개수만큼)
        if not self.model_loaded:
            return documents[:self.top_k]
        
        try:
            # 쿼리와 문서 페어 생성
            pairs = [[query, doc.page_content] for doc in documents]
            
            # 관련성 점수 계산
            scores = self.model.predict(pairs)
            
            # 문서와 점수를 함께 정렬
            scored_documents = list(zip(documents, scores))
            ranked_documents = sorted(scored_documents, key=lambda x: x[1], reverse=True)
            
            # 상위 k개 문서만 반환
            result_documents = [doc for doc, _ in ranked_documents[:self.top_k]]
            
            return result_documents
        except Exception as e:
            print(f"리랭킹 과정 중 오류 발생: {e}")
            return documents[:self.top_k]  # 오류 시 기본 정렬 사용


def create_korean_reranker(top_k: int = 5) -> KoreanReranker:
    """
    한국어 리랭커 생성 편의 함수

    Args:
        top_k (int): 리랭킹 후 반환할 문서 수

    Returns:
        KoreanReranker: 생성된 리랭커 객체
    """
    return KoreanReranker(top_k=top_k) 