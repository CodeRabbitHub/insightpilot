"""create dashboards dashboard_cards

Revision ID: ee5ee826b050
Revises: f2f458dd2525
Create Date: 2026-08-06 11:50:46.692110

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'ee5ee826b050'
down_revision: Union[str, Sequence[str], None] = 'f2f458dd2525'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create dashboards and dashboard_cards (PRD.md Sec.7) plus the one
    seeded Overview dashboard row, from
    plans/briefs/2026-08-06-dashboard-persistence.md."""
    op.create_table(
        "dashboards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema="app",
    )

    op.create_table(
        "dashboard_cards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "dashboard_id",
            sa.Integer(),
            sa.ForeignKey("app.dashboards.id"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("sql_text", sa.Text(), nullable=False),
        sa.Column("chart_spec_json", JSONB(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema="app",
    )

    op.execute("INSERT INTO app.dashboards (name) VALUES ('Overview')")


def downgrade() -> None:
    """Drop only the two tables this migration created, in FK-safe order
    -- never the `app` schema itself, since other tables already live in
    it and predate this migration."""
    op.drop_table("dashboard_cards", schema="app")
    op.drop_table("dashboards", schema="app")
