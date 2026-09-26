"""Gestion de la connexion asynchrone à la base de données (MariaDB / MySQL)."""

import asyncio
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


async def init_db(max_retries: int = 3, retry_delay: float = 2.0) -> bool:
    """Initialise les tables de la base de données au démarrage (avec retries)."""
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                f"Connexion à la base de données ({attempt}/{max_retries}) : "
                f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
            )
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await conn.run_sync(_sync_migrations)
            logger.success("Tables de la base de données initialisées avec succès.")
            return True
        except Exception as e:
            logger.error(f"Tentative {attempt}/{max_retries} échouée pour la base de données : {e}")
            if attempt < max_retries:
                logger.info(f"Nouvelle tentative dans {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                logger.critical("Échec définitif de connexion à la base de données.")
                logger.warning("Vérifiez vos paramètres MariaDB dans le fichier .env et l'état du serveur.")
                return False
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

