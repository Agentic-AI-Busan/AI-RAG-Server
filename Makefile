all: up

up:
	docker-compose up --build -d

down:
	docker-compose down

exec:
	docker exec -it $(CONT) bash

restart:
	docker-compose restart

re:
	make down
	make up

freeze:
	docker exec ai-server pip freeze > ./srcs/ai-server/requirements.txt.local

rebuild-service:
	docker-compose build $(SVC)
	docker-compose up -d $(SVC)

rebuild-ai:
	make rebuild-service SVC=ai-server