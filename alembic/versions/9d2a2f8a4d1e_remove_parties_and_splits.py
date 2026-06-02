"""remove parties and tab splits

Revision ID: 9d2a2f8a4d1e
Revises: 63e7bf35c61b
Create Date: 2026-06-01 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9d2a2f8a4d1e"
down_revision: Union[str, None] = "63e7bf35c61b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("tab_split_payers")
    op.drop_table("tab_splits")
    op.drop_index("idx_tabs_party_id", table_name="tabs")
    op.drop_constraint("tabs_party_id_fkey", "tabs", type_="foreignkey")
    op.drop_column("tabs", "party_id")
    op.drop_table("parties")


def downgrade() -> None:
    op.create_table(
        "parties",
        sa.Column("party_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("party_size", sa.Integer(), nullable=False),
        sa.Column("table_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["table_id"], ["tables.table_id"]),
        sa.PrimaryKeyConstraint("party_id"),
    )
    op.add_column("tabs", sa.Column("party_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "tabs_party_id_fkey",
        "tabs",
        "parties",
        ["party_id"],
        ["party_id"],
    )
    op.create_index("idx_tabs_party_id", "tabs", ["party_id"])

    op.create_table(
        "tab_splits",
        sa.Column("split_id", sa.Integer(), nullable=False),
        sa.Column("tab_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(), nullable=False),
        sa.Column("tip_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tab_id"], ["tabs.tab_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("split_id"),
        sa.CheckConstraint(
            "mode IN ('even', 'by_item', 'percent')", name="ck_tab_splits_mode"
        ),
    )
    op.create_index("ix_tab_splits_tab_id", "tab_splits", ["tab_id"])

    op.create_table(
        "tab_split_payers",
        sa.Column("split_payer_id", sa.Integer(), nullable=False),
        sa.Column("split_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False),
        sa.Column("tax", sa.Numeric(10, 2), nullable=False),
        sa.Column("tip", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(
            ["split_id"], ["tab_splits.split_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("split_payer_id"),
    )
    op.create_index(
        "ix_tab_split_payers_split_id",
        "tab_split_payers",
        ["split_id"],
    )
