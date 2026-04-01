.PHONY: up down restart logs seed test lint

up:
	docker compose up --build -d

down:
	docker compose down

restart:
	docker compose down && docker compose up --build -d

logs:
	docker compose logs -f app

seed:
	docker compose exec app python -m scripts.seed_db

test:
	docker compose exec app pytest tests/ -v --tb=short

lint:
	docker compose exec app python -m py_compile app/main.py

clean:
	docker compose down -v
