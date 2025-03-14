# FROM jeongtj/langchain-rag
FROM python:3.11-slim

WORKDIR /project

COPY ./requirements.txt /project/
COPY ./entrypoint.sh /home/entrypoint.sh

RUN sed -i 's/\r//' /home/entrypoint.sh

RUN pip install -r requirements.txt
RUN chmod +x /home/entrypoint.sh

# 컨테이너의 8000 포트를 외부에 노출
EXPOSE 8000

ENTRYPOINT [ "/home/entrypoint.sh" ]
