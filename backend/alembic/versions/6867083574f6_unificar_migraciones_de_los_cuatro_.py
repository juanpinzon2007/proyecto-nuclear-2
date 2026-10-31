"""unificar migraciones de los cuatro modulos

Revision ID: 6867083574f6
Revises: 20261028_merge_access_cases, 36b9e0790539
Create Date: 2026-10-31 12:07:42.028369
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '6867083574f6'
down_revision: Union[str, Sequence[str], None] = ('20261028_merge_access_cases', '36b9e0790539')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
