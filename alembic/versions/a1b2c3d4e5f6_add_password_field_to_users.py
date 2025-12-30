"""add password field to users

Revision ID: a1b2c3d4e5f6
Revises: 9db8f30accb4
Create Date: 2024-12-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "9db8f30accb4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Schema name where tables are located
    schema_name = "mentraflow"
    
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if table exists in mentraflow schema
    try:
        existing_tables = inspector.get_table_names(schema=schema_name)
    except Exception:
        # Fallback to public schema if mentraflow doesn't exist
        try:
            existing_tables = inspector.get_table_names(schema="public")
            schema_name = "public"
        except Exception:
            existing_tables = inspector.get_table_names()
            schema_name = "public"
    
    # Add hashed_password column to users table if it doesn't exist
    if "users" in existing_tables:
        # Check if column already exists
        try:
            columns = [col["name"] for col in inspector.get_columns("users", schema=schema_name)]
            if "hashed_password" not in columns:
                op.add_column(
                    "users",
                    sa.Column("hashed_password", sa.Text(), nullable=True),
                    schema=schema_name,
                )
        except Exception as e:
            # If column already exists or other error, log and continue
            print(f"Note: Could not add hashed_password column (may already exist): {e}")


def downgrade() -> None:
    # Remove hashed_password column
    schema_name = "mentraflow"
    
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    try:
        existing_tables = inspector.get_table_names(schema=schema_name)
    except Exception:
        try:
            existing_tables = inspector.get_table_names(schema="public")
            schema_name = "public"
        except Exception:
            existing_tables = inspector.get_table_names()
            schema_name = "public"
    
    if "users" in existing_tables:
        try:
            columns = [col["name"] for col in inspector.get_columns("users", schema=schema_name)]
            if "hashed_password" in columns:
                op.drop_column("users", "hashed_password", schema=schema_name)
        except Exception as e:
            print(f"Note: Could not drop hashed_password column: {e}")

