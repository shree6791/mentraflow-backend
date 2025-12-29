"""Add performance indexes

Revision ID: 9db8f30accb4
Revises: 
Create Date: 2024-12-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9db8f30accb4"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Schema name where tables are located
    schema_name = "mentraflow"
    
    from sqlalchemy import inspect, text
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if tables exist in mentraflow schema
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
    
    # Helper function to check if index exists
    def index_exists(table_name: str, index_name: str) -> bool:
        try:
            indexes = inspector.get_indexes(table_name, schema=schema_name)
            return any(idx["name"] == index_name for idx in indexes)
        except Exception:
            return False
    
    # Add index on flashcard_srs_state.due_at for date range queries
    # Only if table exists and index doesn't already exist
    if "flashcard_srs_state" in existing_tables:
        if not index_exists("flashcard_srs_state", "ix_flashcard_srs_state_due_at"):
            op.create_index(
                "ix_flashcard_srs_state_due_at",
                "flashcard_srs_state",
                ["due_at"],
                unique=False,
                schema=schema_name,
            )
    
    # Add index on kg_edges.src_id for graph traversal queries
    if "kg_edges" in existing_tables:
        if not index_exists("kg_edges", "ix_kg_edges_src_id"):
            op.create_index(
                "ix_kg_edges_src_id",
                "kg_edges",
                ["src_id"],
                unique=False,
                schema=schema_name,
            )
    
    # Add index on kg_edges.dst_id for graph traversal queries
    if "kg_edges" in existing_tables:
        if not index_exists("kg_edges", "ix_kg_edges_dst_id"):
            op.create_index(
                "ix_kg_edges_dst_id",
                "kg_edges",
                ["dst_id"],
                unique=False,
                schema=schema_name,
            )


def downgrade() -> None:
    # Drop indexes in reverse order
    schema_name = "mentraflow"
    try:
        op.drop_index("ix_kg_edges_dst_id", table_name="kg_edges", schema=schema_name)
    except Exception:
        pass
    try:
        op.drop_index("ix_kg_edges_src_id", table_name="kg_edges", schema=schema_name)
    except Exception:
        pass
    try:
        op.drop_index("ix_flashcard_srs_state_due_at", table_name="flashcard_srs_state", schema=schema_name)
    except Exception:
        pass

