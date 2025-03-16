#!/bin/bash

# 환경 변수에 따라 실행 모드 결정
echo $ENV
if [ "$ENV" = "test" ]; then
  echo "Running in TEST mode"

  # 백그라운드에서 uvicorn 실행
  uvicorn app.main:app --host 0.0.0.0 --port 8000 &
  UVICORN_PID=$!

  # 서버가 시작될 때까지 대기
  echo "Waiting for server to start..."
  sleep 5
  
  # 서버가 실행 중인지 확인
  if curl -s http://localhost:8000/health > /dev/null; then
    echo "Server is running correctly"
    # 서버 종료
    kill $UVICORN_PID
    exit 0
  else
    echo "Server failed to start properly"
    kill $UVICORN_PID
    exit 1
  fi
else
  # 프로덕션 모드 실행
  echo "Running in PRODUCTION mode"
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
fi