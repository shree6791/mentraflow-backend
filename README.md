# MentraFlow Backend

FastAPI backend application for MentraFlow.

## Quick Start

1. **Install dependencies:**
   ```bash
   make install
   ```

2. **Setup environment:**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Run migrations:**
   ```bash
   make migrate
   ```

4. **Start server:**
   ```bash
   make run
   ```

## Documentation

All documentation is available in the [`docs/`](./docs/) directory:

- **[API Routes](./docs/API_ROUTES.md)** - Complete API endpoint reference
- **[Document Upload Testing](./docs/DOCUMENT_UPLOAD_TESTING.md)** - Guide for testing document upload flow (includes automatic ingestion, summary, flashcards, and knowledge graph extraction)
- **[Agents Documentation](./docs/AGENTS.md)** - Agent architecture and implementation details
- **[OpenAI Setup Guide](./docs/OPENAI_SETUP_GUIDE.md)** - OpenAI API key and model configuration
- **[Alembic Migrations](./docs/alembic/README.md)** - Database migration guide

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
├── main.py              # FastAPI application entry point
├── api/                 # API routes (v1 endpoints)
├── core/                # Core configuration and utilities
├── infrastructure/      # Database and external service clients (PostgreSQL, Qdrant)
├── models/              # SQLAlchemy models
├── schemas/             # Pydantic schemas
├── services/            # Business logic services
├── agents/              # Agent implementations (LangGraph)
│   ├── graphs/          # Centralized LangGraph definitions
│   └── service_tools.py # Service wrappers for agents
├── tasks/               # Background tasks
└── utils/                # Utility functions

docs/                # Documentation
alembic/             # Database migrations
tests/               # Test files
```

