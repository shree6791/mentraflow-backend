# Alembic Migrations

This directory contains database migration scripts.

## Usage

- Create a new migration: `alembic revision --autogenerate -m "description"`
- Apply migrations: `alembic upgrade head`
- Rollback: `alembic downgrade -1`

