
from alembic import context
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.db.models import registrar_modelos_integrados
from app.db.session import get_engine


def run_migrations_offline() -> None:
    url = get_settings().database_url
    context.configure(
        url=url,
        target_metadata=registrar_modelos_integrados(make_url(url).get_backend_name()),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = context.config.attributes.get("connection")

    if connection is not None:
        context.configure(
            connection=connection,
            target_metadata=registrar_modelos_integrados(connection.dialect.name),
        )

        with context.begin_transaction():
            context.run_migrations()

        return

    with get_engine().connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=registrar_modelos_integrados(connection.dialect.name),
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
