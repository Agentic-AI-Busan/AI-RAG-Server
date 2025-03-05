from typing import Dict, Any
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from app.utils.vectordb import load_vectordb


class BaseService:
    def __init__(
        self, vectordb_name: str, model_name: str = "gpt-4", temperature: float = 0.2
    ):
        self.vectorstore = load_vectordb(vectordb_name)
        self.retriever = self.vectorstore.as_retriever()
        self.llm = ChatOpenAI(model_name=model_name, temperature=temperature)

    async def process_query(self, query: str, prompt_template: str) -> Dict[str, Any]:
        raise NotImplementedError
