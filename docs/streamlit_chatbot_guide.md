# Streamlit 기반 부산 여행 AI 챗봇 UI 기술 가이드

## 1. 개요

본 문서는 부산 여행 정보를 제공하는 AI 챗봇의 사용자 인터페이스(UI)를 Streamlit을 사용하여 구축하는 방법에 대해 기술합니다. 이 Streamlit 앱은 기존에 구축된 백엔드 API (`ai-server`)와 연동하여 사용자에게 자연스러운 대화형 경험을 제공하는 것을 목표로 합니다.

사용자는 이 챗봇을 통해 부산의 관광 명소, 맛집 등에 대한 질문을 할 수 있으며, AI는 적절한 정보를 찾아 답변합니다.

## 2. 프로젝트 내 위치

Streamlit 챗봇 관련 파일들은 프로젝트 루트 디렉토리의 `streamlit-app` 폴더 내에 위치합니다.

```docs/streamlit_chatbot_guide.md
<code_block_to_apply_changes_from>
```

이러한 구조는 백엔드 API 로직과 프론트엔드 UI 로직을 명확하게 분리하여 프로젝트의 유지보수성과 확장성을 향상시킵니다.

## 3. 주요 파일 설명

### 3.1. `app.py`

Streamlit 애플리케이션의 핵심 로직을 담고 있는 Python 스크립트입니다. 주요 기능은 다음과 같습니다:

-   **UI 구성**: `st.set_page_config`, `st.title`, `st.chat_message`, `st.chat_input` 등을 사용하여 챗봇의 기본적인 화면을 구성합니다.
-   **대화 상태 관리**: `st.session_state`를 사용하여 사용자와 챗봇 간의 대화 기록을 저장하고 관리합니다. 이를 통해 사용자가 이전 대화 내용을 볼 수 있게 합니다.
-   **API 연동**: 사용자가 메시지를 입력하면, 해당 메시지와 이전 대화 기록을 백엔드 API (`ai-server`의 `/route-test` 엔드포인트)로 전송합니다. `requests` 라이브러리를 사용하여 HTTP POST 요청을 보냅니다.
-   **응답 처리**: API로부터 받은 응답(챗봇의 답변, 관련 정보 출처 등)을 파싱하여 화면에 표시합니다.
-   **오류 처리**: API 호출 중 발생할 수 있는 네트워크 오류, HTTP 오류, 타임아웃 등을 처리하여 사용자에게 적절한 메시지를 보여줍니다.

### 3.2. `Dockerfile`

Streamlit 애플리케이션을 Docker 컨테이너 환경에서 실행하기 위한 설정 파일입니다. 주요 내용은 다음과 같습니다:

-   **베이스 이미지**: `python:3.10-slim`을 사용하여 가볍고 안정적인 Python 실행 환경을 구성합니다.
-   **작업 디렉토리 설정**: 컨테이너 내 작업 디렉토리를 `/app`으로 설정합니다.
-   **의존성 설치**: `requirements.txt` 파일을 컨테이너에 복사하고, `pip install` 명령을 통해 필요한 Python 패키지를 설치합니다.
-   **애플리케이션 코드 복사**: `streamlit-app` 디렉토리 내의 모든 파일을 컨테이너의 작업 디렉토리로 복사합니다.
-   **포트 노출**: Streamlit의 기본 실행 포트인 `8501`을 외부로 노출합니다.
-   **실행 명령**: `ENTRYPOINT`를 사용하여 컨테이너 시작 시 `streamlit run app.py --server.port=8501 --server.address=0.0.0.0` 명령을 실행하여 Streamlit 앱을 시작합니다. `--server.address=0.0.0.0` 옵션은 컨테이너 외부에서도 접속 가능하도록 합니다.

### 3.3. `requirements.txt`

Streamlit 애플리케이션 실행에 필요한 Python 패키지와 그 버전 정보를 명시한 파일입니다.

```
streamlit==1.35.0
requests==2.31.0
```

-   `streamlit`: 챗봇 UI를 구축하기 위한 핵심 라이브러리입니다.
-   `requests`: 백엔드 API와 HTTP 통신을 하기 위한 라이브러리입니다.

## 4. 핵심 로직 (`app.py` 중심)

### 4.1. 초기 설정 및 UI
-   `st.set_page_config()`: 브라우저 탭의 제목과 페이지 레이아웃을 설정합니다.
-   `st.title()`: 페이지의 주 제목을 표시합니다.
-   대화 기록 초기화: `st.session_state.messages`가 없으면 어시스턴트의 초기 인사 메시지를 포함하여 리스트를 생성합니다.

### 4.2. 대화 기록 표시
-   `st.session_state.messages`에 저장된 각 메시지를 순회하며 `st.chat_message(role)` 컨텍스트 관리자를 사용하여 사용자 또는 어시스턴트의 메시지를 구분하여 표시합니다.
-   메시지 내용은 `st.markdown()`을 사용하여 렌더링합니다.

### 4.3. 사용자 입력 처리
-   `st.chat_input()`: 사용자로부터 메시지를 입력받는 위젯을 생성합니다.
-   사용자 입력이 발생하면:
    1.  사용자 메시지를 `st.session_state.messages`에 추가하고 화면에 즉시 표시합니다.
    2.  이전 대화 기록(`st.session_state.messages`의 마지막 사용자 입력 제외)을 API가 요구하는 형식 (`List[Tuple[str, str]]`)으로 변환합니다.
    3.  `requests.post()`를 사용하여 백엔드 API의 `/route-test` 엔드포인트로 사용자 질문(`query`)과 변환된 대화 기록(`chat_history`)을 JSON 형태로 전송합니다.
        -   API 호출 URL은 `API_BASE_URL` 환경 변수를 기반으로 동적으로 생성됩니다.

### 4.4. API 응답 및 오류 처리
-   API 호출은 `try-except` 블록으로 감싸 다양한 예외 상황(타임아웃, HTTP 오류, 네트워크 오류 등)을 처리합니다.
-   요청 성공 시:
    -   `response.json()`으로 JSON 응답을 파싱합니다.
    -   챗봇 답변(`data["response"]`)과 출처 정보(`data["sources"]`)를 추출합니다.
    -   답변을 `message_placeholder.markdown()`을 통해 화면에 표시합니다.
    -   AI의 응답을 (출처 정보 포함하여) `st.session_state.messages`에 추가합니다.
-   오류 발생 시:
    -   적절한 오류 메시지를 `message_placeholder.error()`를 통해 화면에 표시합니다.
    -   오류 메시지를 `st.session_state.messages`에 추가합니다.

## 5. 환경 변수

### `API_BASE_URL`

Streamlit 앱이 호출해야 할 백엔드 API 서버의 기본 URL을 지정합니다.

-   **로컬 개발 환경에서 `app.py` 직접 실행 시**:
    -   `ai-server`가 Docker 컨테이너로 실행되고 호스트의 특정 포트(예: 80번)로 매핑된 경우, `app.py` 내의 기본값 `http://localhost:80` (또는 해당 포트)을 사용합니다.
    -   만약 `ai-server`도 로컬에서 직접 실행 중이라면 해당 주소 (예: `http://localhost:8000`)로 변경해야 할 수 있습니다.
-   **Docker Compose 환경에서 실행 시**:
    -   `docker-compose.yml` 파일 내 `streamlit_app` 서비스의 `environment` 섹션에 `API_BASE_URL=http://ai-server:8000`과 같이 설정됩니다.
    -   여기서 `ai-server`는 `docker-compose.yml`에 정의된 백엔드 API 서비스의 이름이며, `8000`은 해당 서비스 컨테이너가 내부적으로 사용하는 포트입니다. `app.py`는 `os.getenv("API_BASE_URL", "기본값")`을 통해 이 값을 읽어옵니다.

## 6. 실행 방법

### 6.1. 로컬 개발 환경에서 실행 (Anaconda 사용)

1.  **Anaconda Prompt (또는 터미널) 실행.**
2.  **Conda 가상환경 생성 및 활성화:**
    ```bash
    conda create -n streamlit_env python=3.10
    conda activate streamlit_env
    ```
3.  **`streamlit-app` 디렉토리로 이동:**
    ```bash
    cd path/to/Agentic-AI-Busan/streamlit-app
    ```
4.  **필요한 라이브러리 설치:**
    ```bash
    pip install -r requirements.txt
    ```
5.  **백엔드 API 서버 실행:**
    -   로컬에서 `ai-server`를 Docker 컨테이너로 실행하거나 (예: `docker-compose up ai-server`) 또는 직접 FastAPI 서버를 실행합니다.
    -   `app.py`의 `API_BASE_URL` 기본값이 로컬에서 실행 중인 `ai-server` 주소와 일치하는지 확인합니다. (기본값은 `http://localhost:80`으로, `ai-server`가 Docker로 실행되어 호스트 80번 포트에 연결된 경우를 가정)
6.  **Streamlit 앱 실행:**
    ```bash
    streamlit run app.py
    ```
    실행 후 터미널에 나타나는 Local URL (예: `http://localhost:8501`)로 웹 브라우저에서 접속합니다.

### 6.2. Docker Compose를 이용한 전체 시스템 실행

1.  **Docker Desktop이 실행 중인지 확인합니다.**
2.  **터미널을 열고 프로젝트 루트 디렉토리로 이동합니다:**
    ```bash
    cd path/to/Agentic-AI-Busan
    ```
3.  **(선택 사항) 기존 컨테이너 정리:**
    ```bash
    docker-compose down --remove-orphans
    ```
4.  **모든 서비스 빌드 및 실행 (백그라운드):**
    ```bash
    docker-compose up --build -d
    ```
    -   특정 서비스(예: `streamlit_app`)만 다시 빌드하려면:
        ```bash
        docker-compose up --build streamlit_app -d
        ```
5.  **Streamlit 챗봇 접속:**
    웹 브라우저를 열고 `http://localhost:8501` 주소로 접속합니다.

## 7. 참고 사항 및 트러블슈팅

-   **API 연동 문제**:
    -   Streamlit 앱 실행 시 API 호출 관련 오류가 발생하면 다음을 확인합니다:
        -   `ai-server` (백엔드 API)가 정상적으로 실행 중인지 확인합니다. (`docker-compose logs -f ai-server` 등)
        -   `API_BASE_URL` 환경 변수 또는 `app.py` 내의 기본값이 올바른 `ai-server` 주소 및 포트를 가리키고 있는지 확인합니다.
        -   `ai-server`의 API 엔드포인트 경로(`app.py`에서 호출하는 경로와 `main.py` 또는 각 라우터 파일에 정의된 경로)가 일치하는지 확인합니다.
-   **포트 충돌**: 로컬에서 다른 서비스가 `8501` (Streamlit) 또는 `80` (ai-server의 호스트 포트) 등을 사용 중이라면 포트 충돌이 발생할 수 있습니다. `docker-compose.yml`이나 `streamlit run` 명령어에서 포트 번호를 변경해야 할 수 있습니다.
-   **Docker 빌드 오류**: `Dockerfile` 또는 `requirements.txt` 파일에 문제가 있거나 네트워크 문제로 인해 패키지 다운로드에 실패하면 빌드 오류가 발생할 수 있습니다. 오류 메시지를 잘 확인하여 문제를 해결합니다. 