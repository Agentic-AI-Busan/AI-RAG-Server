from typing import Dict, Any
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from app.utils.vectordb import load_vectordb


class BaseService:
    def __init__(
        model_name: str = "gpt-4o-mini", temperature: float = 0.2
    ):
        self.restaurant_vectorstore = load_vectordb("merge_restaurant_finder")
        self.attraction_vectorstore = load_vectordb("attraction_finder")
        self.restaurant_retriever = self.restaurant_vectorstore.as_retriever(search_kwargs={"k": 20})
        self.attraction_retriever = self.attraction_vectorstore.as_retriever(search_kwargs={"k": 20})
        self.llm = ChatOpenAI(model_name=model_name, temperature=temperature, max_tokens=8192)

    async def process_query(self, query: str, prompt_template: str) -> Dict[str, Any]:
        raise NotImplementedError
