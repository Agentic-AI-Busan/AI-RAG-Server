# AI-RAG-Server
AI RAG서버용 리포지토리입니다.

- 깃허브 readme에 테스트 방법 작성
    1. [`https://app.docker.com/auth/desktop/redirect?code=zFNfmkeLy5_7-sb7gVnSh_42TJEd98tuGFwmmGHMH_bD4&state=B_I9FtCHqcoV3XqY-a5lZGAxdhRqKJuMaDNWlTVr86E`](https://app.docker.com/auth/desktop/redirect?code=zFNfmkeLy5_7-sb7gVnSh_42TJEd98tuGFwmmGHMH_bD4&state=B_I9FtCHqcoV3XqY-a5lZGAxdhRqKJuMaDNWlTVr86E) 링크에 들어가서 Docker Desktop 기본 설정으로 설치
    2. Docker Desktop 실행 
    3. 프로젝트 clone 한 뒤 .env.local에 있는 환경변수 설정 후 .env로 파일이름 변경 
    4. 실행
        1. in Window
            1. docker-compose.yml파일이 있는 디렉토리로 이돔
            2. `docker compose up --build -d` 명령어 실행
        2. in Mac
            1. docker-compose.yml파일이 있는 디렉토리로 이돔
            2. `make` 명령어 실행
    5. 모든 설치가 완료되면 실행 완료.
    6. 실행이 안되면 8000포트가 사용중인지 확인 후 재시도.
- 개발 현황
    - 데이터
        - 음식테마거리 데이터 정제 (요약 + 마크다운형식) 후 `data/food/음식테마거리`에 CSV 형태로 저장
        - `scripts/create_restaurant_vectordb.py`로 `vectordb/restaurant finder`에 벡터DB 저장
    - 라우팅 설정
        - `routers/restaurant.py`에서 API 통신을 위한 URL을 설정
    - 특정 벡터DB와 프롬프트 사용
        - 벡터DB 로드를 위해 정의했던 `utils/vectordb.py`를 `services/base.py`에서 Import하여 RAG 준비
        - `services/restaurant.py`에서 `services/base.py`를 Import하고 디자인한 프롬프트를 적용하여 벡엔드로 보낼 데이터를 생성
    - 테스트
        1. 웹 브라우저의 [`localhost:8000`](http://localhost:8000) 포트로 이동
        2. `localhost:8000/redoc`으로 API예시 확인 가능
           ![capston-3](https://github.com/user-attachments/assets/846c4b7a-c5c7-4525-a15c-184b888f5684)
        4. `localhost:8000/docs`로 API확인 가능
           ![capston-2](https://github.com/user-attachments/assets/69d4217f-34b1-44e2-a547-f158cc11722f)
        5. `localhost:8000/api/v1/restaurants/search?query="부산고기맛집 추천"` 같이 query로 요청을 작성 후 이동
           ![capston-1](https://github.com/user-attachments/assets/8926c8e5-a74e-4ec4-a554-48ce82fb9bec)
        6. 응답 json데이터가 브라우저에 나타남.
        7. 추후 API통신을 위한 URI. 
- 개발 계획
    - 서버
        - 두가지 방법
            1. 두 개의 서로 다른 AWS 인스턴스로 AI, 벡엔드 서버를 각 각 구축 후 통신
            2. 하나의 AWS 인스턴스로 AI서비스는 Localhost에서 실행 & 벡엔드 서버로 사용
    - 데이터
        - 다른 domain의 데이터도 {요약 + 마크다운} 형식 데이터로 정제하여 벡터DB 생성 및 서비스 구축
    - 서비스
        - 퍼블리싱 작업물 확인 후 서비스 FLOW를 다시 분석하며, AI가 사용되는 부분을 정리
        - 사용되어야하는 데이터와 프롬프트 정리하면서 서비스 구축
