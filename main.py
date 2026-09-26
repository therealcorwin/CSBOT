"""Point d'entrée principal de CSBOT (Georges Bot v2.0).

Initialisation du Dispatcher aiogram v3, de la base de données MariaDB,
des middlewares, des routeurs, du planificateur de tâches et du serveur de webhooks.
"""

import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from loguru import logger

from api.webhook_server import start_webhook_server
from config.settings import settings
from database.session import async_session_maker, close_db, init_db
from middlewares.db_middleware import DbSessionMiddleware
from middlewares.role_middleware import RoleMiddleware
from routers import setup_routers
from scheduler.tasks import setup_scheduler
from services.llm.manager import llm_manager

# Configuration des logs
logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add("logs/csbot_{time:YYYY-MM-DD}.log", rotation="10 MB", retention="30 days", level="DEBUG")


async def set_default_commands(bot: Bot):
    """Enregistre les commandes visibles dans le menu Telegram."""
    commands = [
        BotCommand(command="start", description="Afficher le menu principal"),
        BotCommand(command="id", description="Afficher l'ID du chat actuel"),
        BotCommand(command="help", description="Guide d'utilisation et aide"),
        BotCommand(command="prestataire", description="Enregistrer une visite de prestataire (CS)"),
        BotCommand(command="resultats_sondage", description="Résultats du sondage en cours (CS)"),
        BotCommand(command="promouvoir", description="Nommer un membre au Conseil Syndical (Admin)"),
        BotCommand(command="retrograder", description="Rétrograder un membre CS en simple copro (Admin)"),
        BotCommand(command="membres_cs", description="Liste des membres du Conseil Syndical (Admin)"),
    ]
    try:
        await bot.set_my_commands(commands)
    except Exception as e:
        logger.warning(f"Impossible de configurer les commandes Telegram : {e}")


async def main():
    logger.info("==========================================")
    logger.info("   Démarrage de CSBOT (Georges Bot v2.0)  ")
    logger.info("==========================================")

    if not settings.BOT_TOKEN or settings.BOT_TOKEN == "votre_token_telegram_bot_ici":
        logger.warning("ATTENTION : Le token Telegram n'est pas encore renseigné dans le fichier .env.")

    # 1. Initialisation de la base de données (Fail-Fast)
    db_ok = await init_db()
    if not db_ok:
        logger.critical("🛑 Arrêt critique : CSBOT ne peut pas fonctionner sans base de données. Démarrage annulé.")
        return

    # 2. Initialisation du Bot et du Dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # 3. Enregistrement des Middlewares
    dp.update.middleware(DbSessionMiddleware(session_pool=async_session_maker))
    dp.update.middleware(RoleMiddleware())

    # 4. Enregistrement des Routeurs
    root_router = setup_routers()
    dp.include_router(root_router)

    # 5. Configuration des commandes du bot
    if settings.BOT_TOKEN and settings.BOT_TOKEN != "votre_token_telegram_bot_ici":
        await set_default_commands(bot)

    # 6. Démarrage du planificateur de tâches
    scheduler = setup_scheduler(bot)

    # 7. Démarrage du serveur Webhook (n8n / CPTCOPRO)
    webhook_runner = None
    try:
        webhook_runner = await start_webhook_server(bot)
    except Exception as e:
        logger.error(f"Erreur au démarrage du serveur webhook : {e}")

    try:
        logger.success("CSBOT est en ligne et écoute les messages (mode Long-Polling)...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        logger.info("Arrêt du bot en cours...")
        if scheduler:
            scheduler.shutdown()
        if webhook_runner:
            await webhook_runner.cleanup()
        await close_db()
        await llm_manager.close()
        await bot.session.close()
        logger.info("CSBOT arrêté proprement.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Interruption détectée, fermeture.")

