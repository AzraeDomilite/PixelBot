.PHONY: build up down logs restart clean test lint format test-watch test-failed

build:
	docker-compose -f docker/docker-compose.yml build

up:
	docker-compose -f docker/docker-compose.yml up -d

down:
	docker-compose -f docker/docker-compose.yml down

logs:
	docker-compose -f docker/docker-compose.yml logs -f

re: down up

clean:
	docker-compose -f docker/docker-compose.yml down -v
	docker volume rm docker_postgres_data

lint:
	flake8 src/ tests/

format:
	black src/ tests/

test:
	docker-compose -f docker/docker-compose.yml exec -T bot python -m pytest tests/ -v --cov=src --cov-report=term-missing
	docker-compose -f docker/docker-compose.yml exec -T bot find . -type d -name "__pycache__" -exec rm -r {} +
	docker-compose -f docker/docker-compose.yml exec -T bot find . -type d -name ".pytest_cache" -exec rm -r {} +
	docker-compose -f docker/docker-compose.yml exec -T bot find . -type f -name "*.pyc" -delete

test-watch:
	docker-compose -f docker/docker-compose.yml exec -T bot python -m pytest tests/ -v --cov=src --cov-report=term-missing -f

test-failed:
	docker-compose -f docker/docker-compose.yml exec -T bot python -m pytest tests/ -v --cov=src --cov-report=term-missing --last-failed
