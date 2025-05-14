from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langchain.callbacks.tracers.langchain import wait_for_all_tracers
from app.utils.vectordb import load_vectordb
from app.utils.advanced_rag import create_advanced_rag_retriever
from app.utils.hybrid_search import create_hybrid_search
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
import traceback
from pydantic import Field


# 하이브리드 검색을 위한 래퍼 리트리버 클래스 (전역으로 정의)
class HybridSearchRetriever(BaseRetriever):
    """
    하이브리드 검색(벡터 + 키워드) 래퍼 리트리버
    """
    # Pydantic 모델에서는 모든 필드를 미리 선언해야 함
    hybrid_search_obj: Any = Field(default=None, description="하이브리드 검색 객체")
    hybrid_search: Any = Field(default=None, description="하이브리드 검색 호환성용 별칭")
    
    def __init__(self, hybrid_search_obj: Any, **kwargs):
        """
        하이브리드 검색 리트리버 초기화

        Args:
            hybrid_search_obj: 하이브리드 검색 객체
        """
        # 반드시 부모 클래스 초기화 먼저 수행
        super().__init__(**kwargs)
        
        try:
            # hybrid_search_obj는 이미 모델 필드로 선언되어 있으므로 안전하게 할당 가능
            self.hybrid_search_obj = hybrid_search_obj
            # 호환성을 위한 별칭 설정
            self.hybrid_search = hybrid_search_obj
            
            # 객체 검증
            print(f"하이브리드 검색 초기화: {hybrid_search_obj.__class__.__name__}")
                
        except Exception as e:
            print(f"하이브리드 검색 초기화 실패: {e}")
            print(f"스택 트레이스: {traceback.format_exc()}")
            raise
    
    def _get_relevant_documents(self, query: str) -> List[Document]:
        """
        주어진 쿼리에 대해 관련 문서를 검색합니다.

        Args:
            query (str): 검색 쿼리

        Returns:
            List[Document]: 관련 문서 리스트
        """
        try:
            print(f"하이브리드 검색 실행: 쿼리='{query}'")
            documents = self.hybrid_search_obj.search(query)
            print(f"하이브리드 검색 완료: {len(documents)}개 문서 발견")
            return documents
        except Exception as e:
            print(f"하이브리드 검색 중 오류 발생: {e}")
            print(f"스택 트레이스: {traceback.format_exc()}")
            # 실패 시 빈 목록 반환
            return []
    
    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        """
        주어진 쿼리에 대해 비동기적으로 관련 문서를 검색합니다.
        현재는 동기 메서드를 호출합니다.

        Args:
            query (str): 검색 쿼리

        Returns:
            List[Document]: 관련 문서 리스트
        """
        # 현재는 동기 메서드를 호출
        try:
            return self._get_relevant_documents(query)
        except Exception as e:
            print(f"스택 트레이스: {traceback.format_exc()}")
            # 실패 시 빈 목록 반환
            return []


class BaseService:
    def __init__(
        self, 
        vectordb_name: str, 
        model_name: str = "gpt-4o-mini", 
        temperature: float = 0.2,
        use_reranker: bool = True,
        use_hybrid: bool = True,
        hybrid_alpha: float = 0.8,
        initial_k: int = 20,
        final_k: int = 20
    ):
        """
        기본 서비스 클래스 초기화
        
        Args:
            vectordb_name (str): 사용할 벡터 데이터베이스 이름
            model_name (str): 사용할 LLM 모델 이름
            temperature (float): LLM 생성 온도 (창의성 조절)
            use_reranker (bool): 리랭커 사용 여부
            use_hybrid (bool): 하이브리드 검색 사용 여부 (TMM-CC, alpha=0.8)
            hybrid_alpha (float): 하이브리드 검색의 벡터 검색 가중치 (0.0~1.0)
            initial_k (int): 초기 검색에서 가져올 문서 수
            final_k (int): 최종 반환할 문서 수
        """
        # 벡터 DB가 None인 경우 (일반 챗봇 등) 기본 검색기만 초기화
        if vectordb_name is None:
            self.vectorstore = None
            self.retriever = None
            self.llm = ChatOpenAI(model_name=model_name, temperature=temperature, max_tokens=8192)
            return

        # 벡터 DB가 있는 경우 기존 로직 실행
        self.vectorstore = load_vectordb(vectordb_name)
        
        # 기본 벡터 검색기 설정
        self.base_retriever = self.vectorstore.as_retriever(search_kwargs={"k": initial_k})

        # 검색기 설정: 하이브리드 검색 > 리랭커 > 기본 검색 순으로 시도
        if use_hybrid:
            try:
                # 벡터 DB에서 문서 추출
                docs = self.vectorstore.similarity_search(
                    query="", k=1000  # 모든 문서 가져오기 위해 빈 쿼리 사용
                )
                
                # 하이브리드 검색기 생성
                hybrid_search_obj = create_hybrid_search(
                    vectordb=self.vectorstore,
                    documents=docs,
                    alpha=hybrid_alpha,
                    top_k=initial_k
                )
                
                # 하이브리드 검색 래퍼 생성
                print(f"하이브리드 검색 래퍼 생성 시작")
                hybrid_retriever = HybridSearchRetriever(hybrid_search_obj=hybrid_search_obj)
                
                # 동작 확인
                print(f"하이브리드 래퍼 초기화 확인: {hasattr(hybrid_retriever, 'hybrid_search_obj')=}, {hasattr(hybrid_retriever, 'hybrid_search')=}")
                
                # 하이브리드 검색 결과를 리랭커로 추가 개선
                if use_reranker:
                    try:
                        # 리랭커 적용
                        self.retriever = create_advanced_rag_retriever(
                            base_retriever=hybrid_retriever,
                            initial_k=initial_k,
                            final_k=final_k
                        )
                        print(f"하이브리드 검색 + 리랭커가 성공적으로 초기화되었습니다: {vectordb_name}")
                    except Exception as e:
                        print(f"리랭커 초기화 실패, 하이브리드 검색만 사용합니다: {e}")
                        # 하이브리드 검색 결과를 직접 사용
                        self.retriever = hybrid_retriever
                else:
                    # 하이브리드 검색만 사용
                    self.retriever = hybrid_retriever
                    print(f"TMMCC 하이브리드 검색기(alpha={hybrid_alpha})가 성공적으로 초기화되었습니다: {vectordb_name}")
            except Exception as e:
                print(f"하이브리드 검색 초기화 실패: {e}")
                print(f"스택 트레이스: {traceback.format_exc()}")
                print(f"기본 검색 방법으로 대체합니다.")
                
                # 하이브리드 검색 실패 시 리랭커나 기본 검색기 사용
                if use_reranker:
                    try:
                        self.retriever = create_advanced_rag_retriever(
                            base_retriever=self.base_retriever,
                            initial_k=initial_k,
                            final_k=final_k
                        )
                        print(f"Advanced RAG 검색기가 성공적으로 초기화되었습니다: {vectordb_name}")
                    except Exception as e2:
                        print(f"리랭커 초기화도 실패: {e2}")
                        print(f"기본 벡터 검색기를 사용합니다.")
                        self.retriever = self.base_retriever
                else:
                    self.retriever = self.base_retriever
        # 하이브리드 검색을 사용하지 않고 리랭커만 사용하는 경우
        elif use_reranker:
            try:
                self.retriever = create_advanced_rag_retriever(
                    base_retriever=self.base_retriever,
                    initial_k=initial_k,
                    final_k=final_k
                )
                print(f"Advanced RAG 검색기가 성공적으로 초기화되었습니다: {vectordb_name}")
            except Exception as e:
                print(f"Advanced RAG 검색기 초기화 실패: {e}")
                print(f"기본 벡터 검색기를 대신 사용합니다.")
                # 오류 발생 시 기본 검색기 사용
                self.retriever = self.base_retriever
        else:
            self.retriever = self.base_retriever
        
        self.llm = ChatOpenAI(model_name=model_name, temperature=temperature, max_tokens=8192)

    async def process_query(self, query: str, prompt_template: str) -> Dict[str, Any]:
        raise NotImplementedError
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # 비동기 컨텍스트 관리자 종료 시 모든 트레이서가 완료될 때까지 대기
        await wait_for_all_tracers()
