from alembic import context

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_engine

# Importar explícitamente aquí los futuros modelos ORM aprobados antes
# de usar autogenerate. Todos deberán heredar de app.db.base.Base.
import app.modules.cases.infrastructure.models  # noqa: F401  (registra modelos en Base.metadata)
import app.modules.scheduling.infrastructure.models  # noqa: F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with get_engine().connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
