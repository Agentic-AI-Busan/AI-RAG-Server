from typing import List, Dict, Any, Tuple, Union, Optional
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_community.retrievers import BM25Retriever
import numpy as np
import traceback


class TMMCC_HybridSearch:
    """
    TMM(Top-Min-Max) 정규화와 CC(Convex Combination) 방식의 하이브리드 검색 클래스.
    
    키워드 기반 검색(BM25)과 의미 기반 검색(벡터 검색)을 결합하여 
    더 관련성 높은 결과를 제공합니다.
    
    기본 alpha 값은 0.8로 설정되어 있어 벡터 검색에 80%, 키워드 검색에 20% 가중치를 부여합니다.
    """
    
    def __init__(
        self, 
        vectordb, 
        documents: List[Document], 
        alpha: float = 0.8,
        top_k: int = 20
    ):
        """
        TMMCC 하이브리드 검색기 초기화

        Args:
            vectordb: 벡터 검색을 위한 벡터 스토어 객체
            documents (List[Document]): 키워드 검색을 위한 문서 리스트
            alpha (float): 벡터 검색 가중치 (0.0~1.0, 기본값 0.8)
            top_k (int): 검색 결과 수 (기본값 20)
        """
        self.vectordb = vectordb
        self.bm25 = BM25Retriever.from_documents(documents)
        self.bm25.k = top_k
        self.alpha = alpha
        self.top_k = top_k
        self.normalize_scores = True
        print(f"TMMCC 하이브리드 검색기 초기화 완료: alpha={alpha}, top_k={top_k}, BM25 문서 수={len(documents)}")
    
    def search(self, query: str, limit: int = 20) -> List[Document]:
        """
        하이브리드 검색을 수행합니다.

        Args:
            query (str): 검색 쿼리
            limit (int): 반환할 최대 문서 수

        Returns:
            List[Document]: 하이브리드 검색 결과 문서 리스트
        """
        print(f"TMMCC 하이브리드 검색 시작: 쿼리='{query}', limit={limit}")
        try:
            # 벡터 검색 수행 (점수 포함)
            try:
                vector_results_with_scores = self.vectordb.similarity_search_with_score(query, k=limit)
                print(f"벡터 검색 완료: {len(vector_results_with_scores)}개 문서")
            except Exception as vec_error:
                print(f"벡터 검색(similarity_search_with_score) 중 오류 발생: {vec_error}")
                print(f"기본 similarity_search로 대체 시도...")
                try:
                    # 점수 없는 검색으로 대체
                    vector_docs = self.vectordb.similarity_search(query, k=limit)
                    # 임의 점수 할당 (역순위 기반)
                    vector_results_with_scores = [(doc, 1.0 - (i / len(vector_docs))) 
                                                 for i, doc in enumerate(vector_docs)]
                    print(f"대체 벡터 검색 완료: {len(vector_results_with_scores)}개 문서")
                except Exception as fallback_error:
                    print(f"대체 벡터 검색도 실패: {fallback_error}")
                    print(f"스택 트레이스: {traceback.format_exc()}")
                    vector_results_with_scores = []
            
            # 키워드 검색 수행
            try:
                keyword_results = self.bm25.get_relevant_documents(query)
                print(f"키워드 검색 완료: {len(keyword_results)}개 문서")
            except Exception as key_error:
                print(f"키워드 검색 중 오류 발생: {key_error}")
                print(f"스택 트레이스: {traceback.format_exc()}")
                keyword_results = []
            
            # 결과가 없는 경우 처리
            if not vector_results_with_scores and not keyword_results:
                print("벡터 검색과 키워드 검색 모두 결과 없음")
                return []
            
            # 벡터 검색 결과만 있는 경우
            if not keyword_results:
                print("키워드 검색 결과 없음, 벡터 검색 결과만 반환")
                vector_docs = [doc for doc, _ in vector_results_with_scores]
                return vector_docs[:limit]
            
            # 키워드 검색 결과만 있는 경우
            if not vector_results_with_scores:
                print("벡터 검색 결과 없음, 키워드 검색 결과만 반환")
                return keyword_results[:limit]
            
            # TMM-CC 하이브리드 검색 적용
            print(f"TMM-CC 하이브리드 검색 적용 중...")
            
            # 벡터 검색 결과와 점수 분리
            vector_docs = [doc for doc, _ in vector_results_with_scores]
            vector_scores = [float(score) for _, score in vector_results_with_scores]
            
            # 벡터 점수는 similarity_search_with_score에서 거리 값으로 반환될 수 있으므로
            # 거리가 작을수록 유사도가 높음을 고려해 변환 (필요 시 활성화)
            # 거리 기반 점수인 경우 역수를 취해 유사도로 변환 (-1을 곱하거나 역수를 취함)
            # vector_scores = [-score for score in vector_scores]  # 거리에 -1 곱하기
            
            # BM25 키워드 검색 점수 추정
            keyword_scores = self._estimate_bm25_scores(query, keyword_results)
            
            # TMM 정규화 적용
            normalized_vector_scores = self._tmm_normalize(vector_scores)
            normalized_keyword_scores = self._tmm_normalize(keyword_scores)
            
            # 하이브리드 점수 계산 (두 결과 집합 결합)
            combined_results = {}
            
            # 벡터 검색 결과 처리
            for i, doc in enumerate(vector_docs):
                doc_id = self._get_doc_id(doc)
                combined_results[doc_id] = {
                    "doc": doc, 
                    "vector_score": normalized_vector_scores[i],
                    "keyword_score": 0.0
                }
            
            # 키워드 검색 결과 처리
            for i, doc in enumerate(keyword_results):
                doc_id = self._get_doc_id(doc)
                if doc_id in combined_results:
                    combined_results[doc_id]["keyword_score"] = normalized_keyword_scores[i]
                else:
                    combined_results[doc_id] = {
                        "doc": doc,
                        "vector_score": 0.0,
                        "keyword_score": normalized_keyword_scores[i]
                    }
            
            # CC 가중치 적용 (H = αV + (1-α)K)
            final_results = []
            for doc_id, result in combined_results.items():
                hybrid_score = self.alpha * result["vector_score"] + (1 - self.alpha) * result["keyword_score"]
                final_results.append((result["doc"], hybrid_score))
            
            # 점수 기준 내림차순 정렬
            sorted_results = sorted(final_results, key=lambda x: x[1], reverse=True)
            
            # 상위 문서만 반환
            final_docs = [doc for doc, _ in sorted_results[:limit]]
            print(f"하이브리드 검색 완료: {len(final_docs)}개 문서 반환")
            
            return final_docs
            
        except Exception as e:
            print(f"하이브리드 검색 중 오류 발생: {e}")
            print(f"스택 트레이스: {traceback.format_exc()}")
            
            # 에러 시 가능한 결과 반환 시도
            try:
                if hasattr(self.vectordb, 'similarity_search'):
                    print("오류 복구: 벡터 검색 결과만 반환 시도")
                    return self.vectordb.similarity_search(query, k=limit)
                else:
                    return []
            except Exception as fallback_error:
                print(f"복구 시도 중 추가 오류 발생: {fallback_error}")
                return []
    
    def _combine_results(
        self, 
        query: str, 
        vector_results: List[Tuple[Document, float]],
        keyword_results: List[Document]
    ) -> List[Document]:
        """
        벡터 검색과 키워드 검색 결과를 TMM 정규화 및 CC 가중치로 결합합니다.

        Args:
            query (str): 검색 쿼리
            vector_results (List[Tuple[Document, float]]): 벡터 검색 결과와 점수
            keyword_results (List[Document]): 키워드 검색 결과

        Returns:
            List[Document]: 결합된 검색 결과 문서 리스트
        """
        # 결과를 ID로 매핑 (ID가 없는 경우 내용 앞 부분으로 대체)
        combined_results = {}
        
        # 벡터 검색 결과 처리
        vector_scores = [score for _, score in vector_results]
        normalized_vector_scores = self._tmm_normalize(vector_scores)
        
        for i, (doc, _) in enumerate(vector_results):
            doc_id = self._get_doc_id(doc)
            combined_results[doc_id] = {
                "doc": doc,
                "vector_score": normalized_vector_scores[i],
                "keyword_score": 0.0
            }
        
        # 키워드 검색 결과 처리 (BM25 점수 추정)
        keyword_scores = self._estimate_bm25_scores(query, keyword_results)
        normalized_keyword_scores = self._tmm_normalize(keyword_scores)
        
        for i, doc in enumerate(keyword_results):
            doc_id = self._get_doc_id(doc)
            if doc_id in combined_results:
                combined_results[doc_id]["keyword_score"] = normalized_keyword_scores[i]
            else:
                combined_results[doc_id] = {
                    "doc": doc,
                    "vector_score": 0.0,
                    "keyword_score": normalized_keyword_scores[i]
                }
        
        # CC 가중치 적용하여 최종 점수 계산 (alpha=0.8)
        # H = (1-α)K + αV 공식 적용
        final_results = []
        for doc_id, result in combined_results.items():
            final_score = (1 - self.alpha) * result["keyword_score"] + self.alpha * result["vector_score"]
            final_results.append((result["doc"], final_score))
        
        # 점수 기준 내림차순 정렬 후 문서만 반환
        sorted_results = sorted(final_results, key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in sorted_results[:self.top_k]]
    
    def _tmm_normalize(self, scores: List[float]) -> List[float]:
        """
        TMM (Top-Min-Max) 정규화를 수행합니다.
        상위 k개 점수의 평균을 최대값으로 설정하는 방식입니다.

        Args:
            scores (List[float]): 정규화할 점수 리스트

        Returns:
            List[float]: 정규화된 점수 리스트 (0~1 범위)
        """
        if not scores:
            return []
        
        # 최소값 찾기
        min_score = min(scores)
        
        # 상위 3개(또는 길이가 더 작으면 전체) 점수의 평균을 최대값으로 설정
        k = min(3, len(scores))
        sorted_scores = sorted(scores, reverse=True)
        max_score = sum(sorted_scores[:k]) / k
        
        # 최대값과 최소값이 같으면 모두 1로 설정
        if max_score == min_score:
            return [1.0] * len(scores)
        
        # TMM 정규화 적용
        normalized = [(s - min_score) / (max_score - min_score) for s in scores]
        
        # 0~1 범위 보장
        return [max(0.0, min(1.0, s)) for s in normalized]
    
    def _estimate_bm25_scores(self, query: str, docs: List[Document]) -> List[float]:
        """
        BM25 검색 결과의 점수를 추정합니다.
        정확한 BM25 점수를 얻기 어려운 경우 순위 기반 점수로 대체합니다.

        Args:
            query (str): 검색 쿼리
            docs (List[Document]): BM25 검색 결과 문서들

        Returns:
            List[float]: 추정된 BM25 점수 리스트
        """
        # BM25 결과는 관련성 순으로 정렬되어 있다고 가정
        # 1/rank 방식으로 점수 추정 (rank=1이 가장 높은 점수)
        scores = []
        for i, _ in enumerate(docs):
            rank = i + 1
            score = 1.0 / rank
            scores.append(score)
        return scores
    
    def _get_doc_id(self, doc: Document) -> str:
        """
        문서의 고유 ID를 가져옵니다. 메타데이터에 ID가 없으면 내용 앞부분을 사용합니다.

        Args:
            doc (Document): 문서 객체

        Returns:
            str: 문서 ID
        """
        # 메타데이터에 id가 있으면 사용
        if hasattr(doc, 'metadata') and doc.metadata and 'id' in doc.metadata:
            return str(doc.metadata['id'])
        
        # id가 없으면 내용 앞 부분 해시 사용
        return str(hash(doc.page_content[:100]))


def create_hybrid_search(
    vectordb, 
    documents: List[Document], 
    alpha: float = 0.8,
    top_k: int = 20
) -> TMMCC_HybridSearch:
    """
    TMMCC 하이브리드 검색기 생성 편의 함수

    Args:
        vectordb: 벡터 검색을 위한 벡터 스토어 객체
        documents (List[Document]): 키워드 검색을 위한 문서 리스트
        alpha (float): 벡터 검색 가중치 (0.0~1.0, 기본값 0.8)
        top_k (int): 검색 결과 수 (기본값 20)

    Returns:
        TMMCC_HybridSearch: 생성된 하이브리드 검색기
    """
    print(f"하이브리드 검색기 생성 시작: alpha={alpha}, top_k={top_k}, 문서 수={len(documents)}")
    return TMMCC_HybridSearch(
        vectordb=vectordb,
        documents=documents,
        alpha=alpha,
        top_k=top_k
    ) 