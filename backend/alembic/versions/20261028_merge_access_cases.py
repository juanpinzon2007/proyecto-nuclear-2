"""Unir revisiones publicadas de Identity y Cases, sin DDL adicional.

Las cuatro tablas de acceso y las nueve tablas de Cases no se solapan.
Ninguna rama requiere el DDL de la otra. Se conserva el historial original.
"""

revision = "20261028_merge_access_cases"
down_revision = ("20261028_identity_access", "c27a750108db")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
