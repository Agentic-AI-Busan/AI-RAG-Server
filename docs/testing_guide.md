# AI-RAG-Server 테스트 가이드

이 문서는 AI-RAG-Server의 설치 및 테스트 방법을 안내합니다.

## 설치 준비

### Docker Desktop 설치
1. Docker Desktop을 설치합니다 (기본 설정으로 설치 권장)
2. 설치 후 Docker Desktop을 실행합니다

### 프로젝트 설정
1. 프로젝트를 clone합니다
2. `.env.local` 파일의 환경변수를 설정합니다
3. 설정 완료 후 `.env.local` 파일을 `.env`로 이름을 변경합니다

## 실행 방법

### Windows 환경
1. 명령 프롬프트(CMD) 또는 PowerShell을 실행합니다
2. `docker-compose.yml` 파일이 있는 디렉토리로 이동합니다
3. 다음 명령어를 실행합니다:
   ```
   docker compose up --build -d
   ```

### Mac 환경
1. 터미널을 실행합니다
2. `docker-compose.yml` 파일이 있는 디렉토리로 이동합니다
3. 다음 명령어를 실행합니다:
   ```
   make
   ```

## 실행 확인
- 모든 설치가 완료되면 서버가 실행됩니다
- 실행이 안 되는 경우, 80번 포트의 사용 여부를 확인 후 재시도합니다

## API 테스트 방법

1. 웹 브라우저에서 `localhost:80`으로 접속합니다
2. API 문서 확인:
   - `localhost:80/redoc`으로 접속하여 API 예시를 확인할 수 있습니다
   - `localhost:80/docs`로 접속하여 API를 확인하고 테스트할 수 있습니다

3. API 요청 테스트:
   - 브라우저 주소창에 다음과 같이 입력하여 직접 API를 테스트할 수 있습니다:
     ```
     localhost:80/api/v1/restaurants/search?query="부산고기맛집 추천"
     ```
   - 정상적으로 작동하면 응답 JSON 데이터가 브라우저에 표시됩니다

## 문제 해결
- 서버가 실행되지 않는 경우 80번 포트가 이미 사용 중인지 확인합니다
- Docker 컨테이너가 정상적으로 실행되었는지 Docker Desktop에서 확인합니다 