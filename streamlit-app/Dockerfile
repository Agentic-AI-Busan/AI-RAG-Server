# Python 베이스 이미지 사용
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 경우 시스템 라이브러리 설치 (예: 특정 폰트나 빌드 도구)
# RUN apt-get update && apt-get install -y ...

# requirements.txt 복사 및 패키지 설치
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 나머지 애플리케이션 코드 복사
COPY . .

# Streamlit 기본 포트 노출
EXPOSE 8501

# 컨테이너 상태 확인용
HEALTHCHECK CMD streamlit healthcheck

# 앱 실행 (0.0.0.0으로 모든 인터페이스에서 접속 허용)
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
