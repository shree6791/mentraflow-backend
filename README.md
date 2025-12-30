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
- **[UI Readiness Assessment](./docs/UI_READINESS_ASSESSMENT.md)** - What's ready for frontend development and what can be built now
- **[Document Upload Testing](./docs/DOCUMENT_UPLOAD_TESTING.md)** - Guide for testing document upload flow (includes automatic ingestion, summary, flashcards, and knowledge graph extraction)
- **[Agents Documentation](./docs/AGENTS.md)** - Agent architecture and implementation details
- **[Personalization & Optimization](./docs/PERSONALIZATION_AND_OPTIMIZATION.md)** - Personalization requirements, spaced repetition, and when to use QLoRA/LoRA/MMR
- **[OpenAI Setup Guide](./docs/OPENAI_SETUP_GUIDE.md)** - OpenAI API key and model configuration
- **[Database Fields Explanation](./docs/DATABASE_FIELDS_EXPLANATION.md)** - Why we need `steps`, `metadata` fields in tables
- **[Droplet Deployment Guide](./docs/DEPLOYMENT_DROPLET.md)** - **Complete guide for Droplet (VPS) deployment** ⭐
- **[Updating Code on Droplet](./docs/UPDATING_CODE.md)** - **Quick reference for code updates** 🚀
- **[Deployment Status & Checklist](./docs/DEPLOYMENT_STATUS.md)** - What's complete and what's optional
- **[Frontend + Backend Deployment](./docs/FRONTEND_BACKEND_DEPLOYMENT.md)** - Deploy both UI and API on same Droplet (assumes separate repos)

## Authentication

The API uses **JWT (JSON Web Tokens)** for authentication. All protected endpoints require an `Authorization: Bearer <token>` header.

**Features:**
- ✅ Secure password hashing (bcrypt)
- ✅ Strong password requirements
- ✅ Password reset functionality
- ✅ Google Sign-In support
- ✅ Rate limiting on auth endpoints
- ✅ All endpoints secured with proper authorization

See [API Routes](./docs/API_ROUTES.md#authentication) for authentication endpoints.

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

