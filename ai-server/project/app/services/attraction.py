from typing import Dict, Any
from langchain_core.prompts import PromptTemplate
from langchain_core.tracers.context import collect_runs
from .base import BaseService

class AttractionService(BaseService):
    def __init__(self):
        super().__init__(vectordb_name="attraction_finder")

        self.template = """
        당신은 어트랙션 추천 AI입니다. 주어진 맥락을 바탕으로 사용자의 질문에 답변해주세요.

        다음은 어트랙션에 대한 정보입니다:
        {attraction_info}

        사용자 질문: {user_request}

        다음 지침을 따라 답변해주세요:
        1. 하나의 #문자 뒤에있는 부분에서 어트랙션의 이름 입니다.
        2. 꼭 해당부분줄의 "# " 을 제외한 모든 텍스트를 그대로 어트랙션 이름으로 써주세요. (예: # '모두를 위한 부산여행' -> "모두를 위한 부산여행")
        3. 각 어트랙션의 이름을 정확히 큰따옴표로 감싸서 언급해주세요. (예: "모두를 위한 부산여행")
        4. 각 어트랙션의 주요 특징을 간단히 설명해주세요.

        어트랙션 정보를 바탕으로 사용자의 질문에 답변해주세요.
        """
        self.prompt = PromptTemplate.from_template(self.template)

    def process_attraction_response(self, docs, llm_response: str) -> Dict[str, Any]:
        mentioned_attractions = {}

        for doc in docs:
            content = doc.page_content
            content_id = doc.metadata["content_id"]

            for line in content.split("\n"):
                if line.startswith("# "):
                    attraction_name = line.replace("# ", "").strip("'")
                    print(attraction_name)
                    mentioned_attractions[attraction_name] = content_id
                    break
        print(mentioned_attractions)
        print(llm_response)

        response_attraction_ids = []
        for attraction_name in mentioned_attractions.keys():
            print(f"attraction_name: '{attraction_name}'")
            print(attraction_name in llm_response)
            if attraction_name in llm_response:
                response_attraction_ids.append(mentioned_attractions[attraction_name])

        return {"answer": llm_response, "attraction_ids": response_attraction_ids}

    async def search_attractions(self, query: str) -> Dict[str, Any]:
        # LangSmith 추적 시작
        with collect_runs() as cb:
            docs = await self.retriever.ainvoke(query, config={"callbacks": cb})
            context = "\n\n".join([doc.page_content for doc in docs])

            chain_input = {"attraction_info": context, "user_request": query}

            response = await self.llm.ainvoke(self.prompt.format(**chain_input), config={"callbacks": cb})

            return self.process_attraction_response(docs, response.content)
