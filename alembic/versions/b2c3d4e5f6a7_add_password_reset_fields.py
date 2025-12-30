"""add password reset fields

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2024-12-29 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
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
    
    # Add password_reset_token and password_reset_expires columns to users table
    if "users" in existing_tables:
        # Check if columns already exist
        try:
            columns = [col["name"] for col in inspector.get_columns("users", schema=schema_name)]
            
            if "password_reset_token" not in columns:
                op.add_column(
                    "users",
                    sa.Column("password_reset_token", sa.Text(), nullable=True),
                    schema=schema_name,
                )
            
            if "password_reset_expires" not in columns:
                op.add_column(
                    "users",
                    sa.Column("password_reset_expires", sa.DateTime(timezone=True), nullable=True),
                    schema=schema_name,
                )
        except Exception as e:
            # If columns already exist or other error, log and continue
            print(f"Note: Could not add password reset columns (may already exist): {e}")


def downgrade() -> None:
    # Remove password reset columns
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
            
            if "password_reset_expires" in columns:
                op.drop_column("users", "password_reset_expires", schema=schema_name)
            
            if "password_reset_token" in columns:
                op.drop_column("users", "password_reset_token", schema=schema_name)
        except Exception as e:
            print(f"Note: Could not drop password reset columns: {e}")

