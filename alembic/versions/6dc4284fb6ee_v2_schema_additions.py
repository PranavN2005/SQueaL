"""v2 schema additions

Revision ID: 6dc4284fb6ee
Revises: e7bc3d63bde5
Create Date: 2026-05-11 11:40:13.321080

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6dc4284fb6ee"
down_revision: Union[str, None] = "e7bc3d63bde5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New column on tables
    op.add_column("tables", sa.Column("reserved_for", sa.String(), nullable=True))

    # New column + type change on reservations
    op.add_column(
        "reservations",
        sa.Column("status", sa.String(), nullable=False, server_default="reserved"),
    )
    op.alter_column(
        "reservations",
        "reservation_time",
        type_=sa.String(),
        existing_type=sa.DateTime(),
        postgresql_using="reservation_time::text",
    )

    # tabs now link to tables
    op.add_column("tabs", sa.Column("table_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_tabs_table_id", "tabs", "tables", ["table_id"], ["table_id"]
    )
    op.alter_column("tabs", "party_id", existing_type=sa.Integer(), nullable=True)

    # tab line items
    op.create_table(
        "tab_items",
        sa.Column("tab_item_id", sa.Integer(), nullable=False),
        sa.Column("tab_id", sa.Integer(), nullable=False),
        sa.Column("item_name", sa.String(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["tab_id"], ["tabs.tab_id"]),
        sa.PrimaryKeyConstraint("tab_item_id"),
    )


def downgrade() -> None:
    op.drop_table("tab_items")
    op.alter_column("tabs", "party_id", existing_type=sa.Integer(), nullable=False)
    op.drop_constraint("fk_tabs_table_id", "tabs", type_="foreignkey")
    op.drop_column("tabs", "table_id")
    op.alter_column(
        "reservations",
        "reservation_time",
        type_=sa.DateTime(),
        existing_type=sa.String(),
        postgresql_using="reservation_time::timestamp",
    )
    op.drop_column("reservations", "status")
    op.drop_column("tables", "reserved_for")
