.PHONY: run format lint test migrate makemigration install help routes devflow run-debug

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

