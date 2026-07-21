.PHONY: help up up-proxy down dev build test

help:
	@echo "Available commands:"
	@echo "  make up          - Start backend and frontend"
	@echo "  make up-proxy    - Start backend, frontend, and proxy collector"
	@echo "  make down        - Stop all services"
	@echo "  make dev         - Run locally for development"
	@echo "  make build       - Build docker images"
	@echo "  make test        - Run tests"

up:
	docker compose up -d

up-proxy:
	docker compose --profile proxy up -d

down:
	docker compose --profile proxy down

build:
	docker compose build

dev:
	@echo "Starting development servers..."
	@cd backend && uvicorn app.main:app --reload &
	@cd frontend && npm run dev &

test:
	@cd backend && pytest
