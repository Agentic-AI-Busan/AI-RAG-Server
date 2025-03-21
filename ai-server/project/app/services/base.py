from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langchain.callbacks.tracers.langchain import wait_for_all_tracers
from app.utils.vectordb import load_vectordb
from app.utils.advanced_rag import create_advanced_rag_retriever


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
        """
        기본 서비스 클래스 초기화
        
        Args:
            vectordb_name (str): 사용할 벡터 데이터베이스 이름
            model_name (str): 사용할 LLM 모델 이름
            temperature (float): LLM 생성 온도 (창의성 조절)
            use_reranker (bool): 리랭커 사용 여부
            initial_k (int): 초기 검색에서 가져올 문서 수
            final_k (int): 최종 반환할 문서 수
        """
        self.vectorstore = load_vectordb(vectordb_name)
        
        # 기본 벡터 검색기 설정
        self.base_retriever = self.vectorstore.as_retriever(search_kwargs={"k": initial_k})
        
        # Reranker 사용 여부에 따라 검색기 설정
        if use_reranker:
            try:
                self.retriever = create_advanced_rag_retriever(
                    base_retriever=self.base_retriever,
                    initial_k=initial_k,
                    final_k=final_k
                )
                print(f"Advanced RAG 검색기가 성공적으로: {vectordb_name} 초기화되었습니다.")
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
