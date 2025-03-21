from typing import List, Dict, Any
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from .reranker import KoreanReranker, create_korean_reranker


class AdvancedRAGRetriever:
    """
    Reranker를 활용한 향상된 RAG 검색 클래스.
    초기 벡터 검색 결과를 한국어 Reranker로 재정렬하여 더 관련성 높은 문서를 반환합니다.
    """
    
    def __init__(
        self, 
        base_retriever: BaseRetriever, 
        reranker: KoreanReranker = None,
        initial_k: int = 20,
        final_k: int = 20
    ):
        """
        Advanced RAG 검색기 초기화

        Args:
            base_retriever (BaseRetriever): 기본 벡터 검색기
            reranker (KoreanReranker, optional): 한국어 리랭커. None이면 자동 생성
            initial_k (int): 초기 검색에서 가져올 문서 수
            final_k (int): 최종 반환할 문서 수
        """
        self.base_retriever = base_retriever
        self.initial_k = initial_k
        self.final_k = final_k
        
        # 리랭커가 제공되지 않으면 기본값으로 생성
        if reranker is None:
            self.reranker = create_korean_reranker(top_k=final_k)
        else:
            self.reranker = reranker
    
    async def aretrieve(self, query: str) -> List[Document]:
        """
        비동기 검색 메서드. 쿼리를 받아 관련 문서를 검색 후 리랭킹하여 반환합니다.

        Args:
            query (str): 사용자 쿼리

        Returns:
            List[Document]: 리랭킹된 관련 문서 리스트
        """
        try:
            # 초기 검색 수행
            initial_docs = await self.base_retriever.ainvoke(query)
            
            # 리랭킹 수행
            reranked_docs = self.reranker.rerank(query, initial_docs)
            
            return reranked_docs
        except Exception as e:
            print(f"Advanced RAG 검색 중 오류 발생: {e}")
            # 오류 발생 시 초기 검색 결과 그대로 반환 (final_k 개수만큼)
            initial_docs = await self.base_retriever.ainvoke(query)
            return initial_docs[:self.final_k]
    
    def retrieve(self, query: str) -> List[Document]:
        """
        동기식 검색 메서드. 쿼리를 받아 관련 문서를 검색 후 리랭킹하여 반환합니다.

        Args:
            query (str): 사용자 쿼리

        Returns:
            List[Document]: 리랭킹된 관련 문서 리스트
        """
        try:
            # 초기 검색 수행
            initial_docs = self.base_retriever.invoke(query)
            
            # 리랭킹 수행
            reranked_docs = self.reranker.rerank(query, initial_docs)
            
            return reranked_docs
        except Exception as e:
            print(f"Advanced RAG 검색 중 오류 발생: {e}")
            # 오류 발생 시 초기 검색 결과 그대로 반환 (final_k 개수만큼)
            initial_docs = self.base_retriever.invoke(query)
            return initial_docs[:self.final_k]


def create_advanced_rag_retriever(
    base_retriever: BaseRetriever,
    initial_k: int = 20,
    final_k: int = 20
) -> AdvancedRAGRetriever:
    """
    Advanced RAG 검색기 생성 편의 함수

    Args:
        base_retriever (BaseRetriever): 기본 벡터 검색기
        initial_k (int): 초기 검색에서 가져올 문서 수
        final_k (int): 최종 반환할 문서 수

    Returns:
        AdvancedRAGRetriever: 생성된 Advanced RAG 검색기
    """
    # 초기 검색에 사용할 검색기 설정 (k값 변경)
    if hasattr(base_retriever, "search_kwargs"):
        base_retriever.search_kwargs["k"] = initial_k
    
    # 한국어 리랭커 생성
    reranker = create_korean_reranker(top_k=final_k)
    
    # 고급 검색기 생성 및 반환
    return AdvancedRAGRetriever(
        base_retriever=base_retriever,
        reranker=reranker,
        initial_k=initial_k,
        final_k=final_k
    ) 