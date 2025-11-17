.PHONY: build up down restart logs help

help:
	@echo "Доступные команды:"
	@echo "  make build   - Собрать Docker контейнер"
	@echo "  make up      - Запустить контейнер"
	@echo "  make down    - Остановить контейнер"
	@echo "  make restart - Перезапустить контейнер"
	@echo "  make logs    - Посмотреть логи"

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f
