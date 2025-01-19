.PHONY: build up down logs restart clean test lint format

build:
	docker-compose -f docker/docker-compose.yml build

up:
	docker-compose -f docker/docker-compose.yml up -d

down:
	docker-compose -f docker/docker-compose.yml down

logs:
	docker-compose -f docker/docker-compose.yml logs -f

restart: down up

clean:
	docker-compose -f docker/docker-compose.yml down -v

test:
	pytest tests/

lint:
	flake8 src/
	
format:
	black src/
	isort src/
