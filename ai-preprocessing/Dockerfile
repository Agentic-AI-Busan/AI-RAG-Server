# FROM jeongtj/langchain-rag
FROM python:3.11-slim

WORKDIR /project

COPY ./requirements.txt /project/

RUN pip install -r requirements.txt


CMD ["tail", "-f", "/dev/null"]
