"""create app schema conversations messages

Revision ID: f2f458dd2525
Revises:
Create Date: 2026-08-04 15:33:21.518908

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'f2f458dd2525'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the `app` schema (idempotent -- app/catalog/sync.py and
    app/glossary/embed.py already create it for catalog_tables,
    catalog_columns, and kb_chunks) plus the conversations and messages
    tables from plans/briefs/2026-08-04-app-schema-persistence.md."""
    op.execute("CREATE SCHEMA IF NOT EXISTS app")

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema="app",
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("app.conversations.id"),
            nullable=False,
        ),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content_json", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema="app",
    )


def downgrade() -> None:
    """Drop only the two tables this migration created -- never the `app`
    schema itself, since catalog_tables/catalog_columns/kb_chunks live in
    it too and predate this migration."""
    op.drop_table("messages", schema="app")
    op.drop_table("conversations", schema="app")
