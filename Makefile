all: up

up:
	docker compose up --build -d

down:
	docker compose down

exec:
	docker exec -it $(CONT) bash

restart:
	docker compose restart

re:
	make down
	make up

freeze:
	docker exec ai-server pip freeze > ./srcs/ai-server/requirements.txt.local
