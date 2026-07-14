"""rename metadata column to meta_data in document_chunks

Revision ID: 003
Revises: 002
Create Date: 2026-07-13
"""
from typing import Sequence, Union
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("document_chunks", "metadata", new_column_name="meta_data")


def downgrade() -> None:
    op.alter_column("document_chunks", "meta_data", new_column_name="metadata")
