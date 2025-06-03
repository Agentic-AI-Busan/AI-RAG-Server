import os
from typing import List, Tuple
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

class QueryRouterService:
    """
    사용자 쿼리를 분석하여 적절한 도메인으로 라우팅하는 서비스.
    """
    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0.0):
        """
        QueryRouterService 초기화.

        Args:
            model_name (str): 사용할 LLM 모델 이름.
            temperature (float): LLM의 temperature 값.
        """
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        # 라우팅을 위한 프롬프트 템플릿 정의
        self._define_routing_prompt()
        # self.routing_chain = LLMChain(llm=self.llm, prompt=self.routing_prompt)
        self.routing_chain = self.routing_prompt | self.llm
        print("QueryRouterService 초기화 완료")

    def _define_routing_prompt(self):
        """라우팅 결정을 위한 LLM 프롬프트를 정의합니다."""
        template = """
        다음 사용자 질문을 분석하여 가장 적합한 카테고리 하나를 선택해주세요.
        사용자의 이전 대화 내용은 문맥 파악에 참고할 수 있습니다.
        
        [대화 기록]
        {chat_history}
        
        [사용자 질문]
        {query}
        
        [카테고리 옵션]
        - restaurant: 사용자가 식당, 맛집, 음식, 카페 등 먹는 것과 관련된 장소나 정보를 찾고 있을 때 선택합니다.
        - attraction: 사용자가 관광 명소, 여행지, 공원, 해변, 박물관 등 볼거리나 즐길 거리를 찾고 있을 때 선택합니다.
        - general: 사용자가 일반적인 대화, 인사, 날씨, 교통, 숙소 등 위 카테고리에 속하지 않는 질문을 할 때 선택합니다.
        
        가장 적합한 카테고리 하나만 정확히 적어주세요 (restaurant, attraction, general 중 하나):
        """
        self.routing_prompt = PromptTemplate(
            input_variables=["query", "chat_history"],
            template=template
        )

    def _format_chat_history(self, chat_history: List[Tuple[str, str]]) -> str:
        """대화 기록을 LLM 프롬프트에 적합한 형식으로 변환합니다."""
        if not chat_history:
            return "이전 대화 없음"
        formatted_history = "\n".join([f"사용자: {q}\nAI: {a}" for q, a in chat_history])
        return formatted_history

    async def route(self, query: str, chat_history: List[Tuple[str, str]] = None) -> str:
        """
        사용자 쿼리를 분석하여 라우팅 결정을 내립니다.

        Args:
            query (str): 사용자 질문.
            chat_history (List[Tuple[str, str]]): 이전 대화 기록 ([(사용자 질문, AI 답변), ...]).

        Returns:
            str: 결정된 라우팅 카테고리 ('restaurant', 'attraction', 'general').
            분류에 실패하거나 예상치 못한 응답일 경우 'general'을 기본값으로 반환.
        """
        chat_history = chat_history or []
        formatted_history = self._format_chat_history(chat_history)
        
        print(f"라우팅 분석 시작: query='{query}', history_len={len(chat_history)}")

        try:
            # LLMChain 실행 (비동기 실행 고려)
            # response = await self.routing_chain.arun(query=query, chat_history=formatted_history)
            response = await self.routing_chain.ainvoke({
                                                            "query": query,
                                                            "chat_history": formatted_history
                                                        })
            # LLM 응답에서 카테고리 추출 (소문자 변환 및 공백 제거)
            print(f"response: {response}")
            predicted_category = response.content.strip().lower()
            print(f"LLM 라우팅 결과: '{predicted_category}'")

            # 유효한 카테고리인지 확인
            valid_categories = ["restaurant", "attraction", "general"]
            if predicted_category in valid_categories:
                return predicted_category
            else:
                print(f"경고: LLM이 유효하지 않은 카테고리 반환 ('{predicted_category}'). 'general'로 처리합니다.")
                return "general" # 예상치 못한 응답 처리

        except Exception as e:
            print(f"오류: 라우팅 처리 중 예외 발생 - {e}")
            return "general" # 오류 발생 시 기본값 반환