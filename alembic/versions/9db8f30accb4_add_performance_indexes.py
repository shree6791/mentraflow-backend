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
    # Add index on flashcard_srs_state.due_at for date range queries
    op.create_index(
        "ix_flashcard_srs_state_due_at",
        "flashcard_srs_state",
        ["due_at"],
        unique=False,
    )
    
    # Add index on kg_edges.src_id for graph traversal queries
    op.create_index(
        "ix_kg_edges_src_id",
        "kg_edges",
        ["src_id"],
        unique=False,
    )
    
    # Add index on kg_edges.dst_id for graph traversal queries
    op.create_index(
        "ix_kg_edges_dst_id",
        "kg_edges",
        ["dst_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop indexes in reverse order
    op.drop_index("ix_kg_edges_dst_id", table_name="kg_edges")
    op.drop_index("ix_kg_edges_src_id", table_name="kg_edges")
    op.drop_index("ix_flashcard_srs_state_due_at", table_name="flashcard_srs_state")

