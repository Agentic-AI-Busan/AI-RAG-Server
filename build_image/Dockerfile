# 베이스 이미지로 python:3.11-slim 사용
FROM python:3.11-slim

RUN apt-get update && apt-get install -y build-essential
RUN pip install --upgrade pip
RUN pip install -r https://raw.githubusercontent.com/teddylee777/langchain-kr/main/requirements.txt

