# FROM jeongtj/langchain-rag
FROM python:3.11-slim

WORKDIR /project

RUN apt update && apt install -y curl

COPY ./requirements.txt /project/
COPY ./entrypoint.sh /home/entrypoint.sh

RUN sed -i 's/\r//' /home/entrypoint.sh

RUN pip install -r requirements.txt
RUN chmod +x /home/entrypoint.sh

# Hugging Face 관련 설정
ENV TRANSFORMERS_CACHE=/project/model_cache
ENV HF_HOME=/project/model_cache
ENV HF_DATASETS_CACHE=/project/model_cache
ENV SENTENCE_TRANSFORMERS_HOME=/project/model_cache

# 모델 캐시 디렉토리 생성
RUN mkdir -p /project/model_cache

# 컨테이너의 8000 포트를 외부에 노출
EXPOSE 8000

ENTRYPOINT [ "/home/entrypoint.sh" ]
