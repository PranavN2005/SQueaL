"""add indexes for party tabs query

Revision ID: 63e7bf35c61b
Revises: f3a9c1d4b2e7
Create Date: 2026-06-01 20:12:55.158043

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63e7bf35c61b'
down_revision: Union[str, None] = 'f3a9c1d4b2e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("idx_tabs_party_id", "tabs", ["party_id"])
    op.create_index("idx_tab_items_tab_id", "tab_items", ["tab_id"])


def downgrade() -> None:
    op.drop_index("idx_tab_items_tab_id", table_name="tab_items")
    op.drop_index("idx_tabs_party_id", table_name="tabs")