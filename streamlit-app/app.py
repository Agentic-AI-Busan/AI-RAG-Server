import streamlit as st
import requests
import os

# API 기본 URL 설정
# 로컬에서 Streamlit 앱을 실행하고 Docker로 실행 중인 ai-server에 접속할 경우 localhost 사용
# Docker Compose 내부에서 streamlit_app 컨테이너가 ai_server 컨테이너를 호출할 때는 서비스 이름(예: http://ai_server:8000) 사용
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:80") # 로컬 테스트 시 Docker ai-server가 80포트에 연결된 경우

st.set_page_config(page_title="Agentic AI Busan", layout="centered")
st.title("Agentic AI Busan 🌊")

# 세션 상태에 대화 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 부산 여행에 대해 무엇이든 물어보세요."}]

# 이전 대화 내용 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 입력 처리
if prompt := st.chat_input("부산 여행에 대해 질문해주세요..."):
    # 사용자 메시지를 대화 기록에 추가하고 화면에 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 이전 대화 기록을 API 형식에 맞게 변환
    # API는 List[Tuple[str, str]] 형식의 chat_history를 기대 ([(사용자 질문, AI 답변), ...])
    api_chat_history = []
    # st.session_state.messages에는 현재 사용자의 입력까지 포함되어 있으므로, API에 보낼 때는 이를 제외하고 이전까지의 기록을 사용
    # 또한, 가장 최근 메시지부터 짝을 맞추거나, 전체 기록을 순서대로 짝지어 보낼 수 있음.
    # 여기서는 Streamlit.md 계획대로 전체 기록에서 사용자-AI 짝을 만듦.
    
    # 직전 메시지까지 (현재 사용자 입력 제외)
    history_to_convert = st.session_state.messages[:-1]
    user_q = None
    for msg in history_to_convert:
        if msg["role"] == "user":
            user_q = msg["content"]
        elif msg["role"] == "assistant" and user_q is not None:
            api_chat_history.append((user_q, msg["content"]))
            user_q = None # 다음 짝을 위해 초기화

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("응답을 생성 중입니다...")
        try:
            # API 호출 (Query Router 사용)
            response = requests.post(
                f"{API_BASE_URL}/chatbot",
                json={"query": prompt, "chat_history": api_chat_history},
                timeout=180 # 타임아웃 시간 증가 (LLM 응답이 길어질 수 있으므로)
            )
            response.raise_for_status() # 오류 발생 시 HTTPError 예외 발생
            data = response.json()
            
            ai_content = data.get("response", "죄송합니다, 답변을 생성하지 못했습니다.")
            ai_sources = data.get("sources", []) # API 응답에서 sources 필드 가져오기

            message_placeholder.markdown(ai_content)
            
            # AI 응답을 대화 기록에 추가 (소스 정보 포함)
            assistant_message = {"role": "assistant", "content": ai_content, "sources": ai_sources}
            st.session_state.messages.append(assistant_message)

        except requests.exceptions.Timeout:
            error_message = "API 호출 시간 초과입니다. 잠시 후 다시 시도해주세요."
            message_placeholder.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message, "sources": []})
        except requests.exceptions.HTTPError as http_err:
            error_message = f"API 서버 오류가 발생했습니다: {http_err.response.status_code} - {http_err.response.text}"
            message_placeholder.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message, "sources": []})
        except requests.exceptions.RequestException as e:
            error_message = f"API 호출 중 네트워크 오류가 발생했습니다: {e}"
            message_placeholder.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message, "sources": []})
        except Exception as e: # 그 외 예외 처리
            error_message = f"챗봇 처리 중 알 수 없는 오류가 발생했습니다: {e}"
            message_placeholder.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message, "sources": []})
