from typing import Dict, Any
from langchain_core.prompts import PromptTemplate
from .base import BaseService


class RestaurantService(BaseService):
    def __init__(self):
        super().__init__(vectordb_name="restaurant_finder")

        self.template = """
        당신은 레스토랑 추천 AI입니다. 주어진 맥락을 바탕으로 사용자의 질문에 답변해주세요.

        다음은 레스토랑에 대한 정보입니다:
        {restaurant_info}

        사용자 질문: {user_request}

        다음 지침을 따라 답변해주세요:
        1. 조건에 맞는 식당을 2-3개 추천해주세요.
        2. 각 식당의 이름을 정확히 큰따옴표로 감싸서 언급해주세요. (예: "더밥하우스")
        3. 각 식당의 주요 특징을 간단히 설명해주세요.

        레스토랑 정보를 바탕으로 사용자의 질문에 답변해주세요.
        """
        self.prompt = PromptTemplate.from_template(self.template)

    def process_restaurant_response(self, docs, llm_response: str) -> Dict[str, Any]:
        mentioned_restaurants = {}
        for doc in docs:
            content = doc.page_content
            rstr_id = doc.metadata["RSTR_ID"]

            for line in content.split("\n"):
                if line.startswith("# "):
                    restaurant_name = line.replace("# ", "").strip()
                    mentioned_restaurants[restaurant_name] = rstr_id
                    break

        response_restaurant_ids = []
        for restaurant_name in mentioned_restaurants.keys():
            if restaurant_name in llm_response:
                response_restaurant_ids.append(mentioned_restaurants[restaurant_name])

        return {"answer": llm_response, "restaurant_ids": response_restaurant_ids}

    async def search_restaurants(self, query: str) -> Dict[str, Any]:
        docs = await self.retriever.ainvoke(query)
        context = "\n\n".join([doc.page_content for doc in docs])

        chain_input = {"restaurant_info": context, "user_request": query}

        response = await self.llm.ainvoke(self.prompt.format(**chain_input))

        return self.process_restaurant_response(docs, response.content)
