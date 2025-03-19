from typing import Dict, Any
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.callbacks.tracers.langchain import wait_for_all_tracers
from app.utils.vectordb import load_vectordb


class BaseService:
    def __init__(
        self, vectordb_name: str, model_name: str = "gpt-4o-mini", temperature: float = 0.2
    ):
        self.vectorstore = load_vectordb(vectordb_name)
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 20})
        self.llm = ChatOpenAI(model_name=model_name, temperature=temperature, max_tokens=8192)

    async def process_query(self, query: str, prompt_template: str) -> Dict[str, Any]:
        raise NotImplementedError
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # 비동기 컨텍스트 관리자 종료 시 모든 트레이서가 완료될 때까지 대기
        await wait_for_all_tracers()
