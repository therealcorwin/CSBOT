"""Gestion de la connexion asynchrone à la base de données (MariaDB / MySQL)."""

from collections.abc import AsyncGenerator

from loguru import logger
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config.settings import settings
from database.models import Base

# Moteur principal
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False,
)

# Fabrique de sessions
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


def _sync_migrations(sync_conn):
    """Effectue les migrations légères de colonnes pour les tables existantes."""
    from sqlalchemy import inspect, text

    inspector = inspect(sync_conn)
    if "users" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("users")}
        if "approved_by" not in cols:
            sync_conn.execute(text("ALTER TABLE users ADD COLUMN approved_by VARCHAR(128) NULL"))
        if "approved_by_id" not in cols:
            sync_conn.execute(text("ALTER TABLE users ADD COLUMN approved_by_id BIGINT NULL"))
        if "approved_at" not in cols:
            sync_conn.execute(text("ALTER TABLE users ADD COLUMN approved_at DATETIME NULL"))


async def init_db() -> bool:
    """Initialise les tables de la base de données au démarrage."""
    try:
        logger.info(f"Connexion à la base de données : {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(_sync_migrations)
        logger.success("Tables de la base de données initialisées avec succès.")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de la base de données : {e}")
        logger.warning("Vérifiez vos paramètres MariaDB dans le fichier .env.")
        return False


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Fournit une session de base de données asynchrone."""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db() -> None:
    """Ferme proprement le pool de connexions du moteur."""
    await engine.dispose()
    logger.info("Connexions base de données fermées.")

