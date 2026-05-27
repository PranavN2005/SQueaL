"""v4 tab status, payments, splits

Revision ID: f3a9c1d4b2e7
Revises: 6dc4284fb6ee
Create Date: 2026-05-26 18:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3a9c1d4b2e7"
down_revision: Union[str, None] = "6dc4284fb6ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- tabs: lifecycle status + close timestamp ---
    op.add_column(
        "tabs",
        sa.Column("status", sa.String(), nullable=False, server_default="open"),
    )
    op.add_column(
        "tabs",
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_tabs_status", "tabs", "status IN ('open', 'paid', 'void')"
    )

    # --- payments: one row recorded per checkout ---
    op.create_table(
        "payments",
        sa.Column("payment_id", sa.Integer(), nullable=False),
        sa.Column("tab_id", sa.Integer(), nullable=False),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False),
        sa.Column("tax", sa.Numeric(10, 2), nullable=False),
        sa.Column("tip", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(10, 2), nullable=False),
        sa.Column("payment_method", sa.String(), nullable=False),
        sa.Column(
            "paid_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tab_id"], ["tabs.tab_id"]),
        sa.PrimaryKeyConstraint("payment_id"),
    )
    op.create_index("ix_payments_tab_id", "payments", ["tab_id"])

    # --- tab_splits + tab_split_payers: a recorded division of a tab ---
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
    op.create_index("ix_tab_split_payers_split_id", "tab_split_payers", ["split_id"])


def downgrade() -> None:
    op.drop_table("tab_split_payers")
    op.drop_table("tab_splits")
    op.drop_table("payments")
    op.drop_constraint("ck_tabs_status", "tabs", type_="check")
    op.drop_column("tabs", "closed_at")
    op.drop_column("tabs", "status")
