.PHONY: run format lint test migrate makemigration install help routes devflow run-debug qdrant-start qdrant-stop qdrant-status

help:
	@echo "Available targets:"
	@echo "  install       - Install dependencies"
	@echo "  run           - Run the FastAPI development server"
	@echo "  run-debug     - Run the FastAPI server in debug mode (DEBUG=true)"
	@echo "  format        - Format code with black"
	@echo "  lint          - Lint code with ruff"
	@echo "  test          - Run tests"
	@echo "  migrate       - Run database migrations"
	@echo "  makemigration - Create a new database migration"
	@echo "  routes        - Audit routes against contract"
	@echo "  devflow       - Run end-to-end development flow"
	@echo "  qdrant-start  - Start Qdrant vector database (Docker)"
	@echo "  qdrant-stop   - Stop Qdrant vector database"
	@echo "  qdrant-status - Check if Qdrant is running"

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload --host $${HOST:-0.0.0.0} --port $${PORT:-8000}

run-debug:
	@if [ -f .env ]; then \
		export $$(grep -v '^#' .env | grep -E '^(HOST|PORT)=' | xargs); \
	fi; \
	DEBUG=true HOST=$${HOST:-127.0.0.1} PORT=$${PORT:-8000} uvicorn app.main:app --reload --host $${HOST:-127.0.0.1} --port $${PORT:-8000} --log-level debug

format:
	black app tests alembic
	ruff check --fix app tests alembic

lint:
	ruff check app tests alembic
	black --check app tests alembic

test:
	pytest tests/ -v

migrate:
	alembic upgrade head

makemigration:
	@echo "Usage: make makemigration MSG='your message'"
	@if [ -z "$(MSG)" ]; then \
		echo "Error: MSG parameter is required"; \
		exit 1; \
	fi
	alembic revision --autogenerate -m "$(MSG)"

# Example migration commands:
migrate-downgrade:
	@echo "Downgrading one revision..."
	alembic downgrade -1

migrate-history:
	@echo "Migration history:"
	alembic history

migrate-current:
	@echo "Current migration version:"
	alembic current

migrate-stamp:
	@echo "Usage: make migrate-stamp REV='revision_id'"
	@if [ -z "$(REV)" ]; then \
		echo "Error: REV parameter is required (e.g., 'head' or revision id)"; \
		exit 1; \
	fi
	alembic stamp "$(REV)"

routes:
	@echo "Auditing routes against contract..."
	@python3 app/scripts/route_audit.py || true

devflow:
	@echo "Running end-to-end development flow..."
	@echo "Make sure the server is running: make run"
	@python3 app/scripts/devflow_runner.py

# Qdrant Docker commands
qdrant-start:
	@echo "Starting Qdrant vector database..."
	@docker run -d \
		--name qdrant \
		-p 6333:6333 \
		-p 6334:6334 \
		-v $$(pwd)/qdrant_storage:/qdrant/storage \
		qdrant/qdrant:latest || \
		(docker start qdrant && echo "Qdrant container already exists, started existing container")
	@echo "✅ Qdrant started on http://localhost:6333"
	@echo "   Dashboard: http://localhost:6333/dashboard"

qdrant-stop:
	@echo "Stopping Qdrant..."
	@docker stop qdrant 2>/dev/null || echo "Qdrant container not running"
	@echo "✅ Qdrant stopped"

qdrant-status:
	@echo "Checking Qdrant status..."
	@if docker ps | grep -q qdrant; then \
		echo "✅ Qdrant is running"; \
		curl -s http://localhost:6333/health | python3 -m json.tool 2>/dev/null || echo "   (Health check failed)"; \
	else \
		echo "❌ Qdrant is not running"; \
		echo "   Run 'make qdrant-start' to start it"; \
	fi

