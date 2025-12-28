# MentraFlow Backend

FastAPI backend application for MentraFlow.

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   make install
   # or
   pip install -r requirements.txt
   ```

3. Copy environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Run database migrations:
   ```bash
   make migrate
   ```

5. Start the development server:
   ```bash
   make run
   ```

## Available Make Targets

- `make install` - Install dependencies
- `make run` - Run the FastAPI development server
- `make format` - Format code with black and ruff
- `make lint` - Lint code with ruff and black
- `make test` - Run tests
- `make migrate` - Run database migrations
- `make makemigration MSG='message'` - Create a new database migration

## Project Structure

```
app/
├── main.py          # FastAPI application entry point
├── api/             # API routes
│   └── v1/          # API version 1
├── core/            # Core configuration and utilities
├── db/              # Database utilities
├── models/          # SQLAlchemy models
├── schemas/         # Pydantic schemas
├── services/        # Business logic services
├── agents/          # Agent implementations
├── tasks/           # Background tasks
└── utils/           # Utility functions

alembic/             # Database migrations
tests/               # Test files
```

## Pre-commit Hooks

Install pre-commit hooks:
```bash
pre-commit install
```

This will automatically run black and ruff on commit.

