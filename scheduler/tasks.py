"""Tâches planifiées (rappels encombrants, détection des tickets en souffrance, relances)."""

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from config.settings import settings
from database.session import async_session_maker
from services.ticket_service import TicketService


async def check_overdue_tickets(bot: Bot):
    """Vérifie si des tickets transmis au syndic n'ont pas eu de réponse depuis plus de 7 jours."""
    if settings.CS_GROUP_ID == 0:
        return

    async with async_session_maker() as session:
        overdue = await TicketService.get_tickets_requiring_reminder(session, days_threshold=7)
        if overdue:
            logger.info(f"{len(overdue)} ticket(s) en souffrance détecté(s).")
            for t in overdue:
                msg = (
                    f"⏳ <b>RELANCE SYNDIC RECOMMANDÉE :</b>\n\n"
                    f"Le ticket <b>{t.ticket_code}</b> ({t.category}) a été transmis au syndic le "
                    f"{t.sent_to_syndic_at.strftime('%d/%m/%Y') if t.sent_to_syndic_at else 'il y a plus de 7 jours'} "
                    "sans retour enregistré.\n\n"
                    "<i>Pensez à effectuer une relance auprès de votre gestionnaire de copropriété.</i>"
                )
                try:
                    await bot.send_message(chat_id=settings.CS_GROUP_ID, text=msg, parse_mode="HTML")
                except Exception as e:
                    logger.warning(f"Erreur envoi rappel ticket en souffrance : {e}")


async def send_encombrants_reminder(bot: Bot):
    """Envoie un rappel dans le chat de la copro la veille du ramassage des encombrants."""
    if settings.COPRO_CHAT_ID == 0:
        return

    msg = (
        "🚛 <b>RAPPEL : PASSAGE DES ENCOMBRANTS DEMAIN MATIN !</b>\n\n"
        "• Merci de ne déposer vos encombrants sur le trottoir <b>qu'à partir de 19h ce soir</b>.\n"
        "• Ne bloquez pas les accès piétons ni la porte d'entrée de l'immeuble.\n"
        "• <i>Rappel : les gravats, produits chimiques et peintures doivent impérativement être déposés en déchetterie.</i>"
    )
    try:
        await bot.send_message(chat_id=settings.COPRO_CHAT_ID, text=msg, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"Erreur envoi rappel encombrants : {e}")


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Configure et démarre le planificateur de tâches asynchrone."""
    scheduler = AsyncIOScheduler()

    # Vérification quotidienne des tickets en souffrance à 10h00
    scheduler.add_job(
        check_overdue_tickets,
        trigger="cron",
        hour=10,
        minute=0,
        kwargs={"bot": bot},
        id="check_overdue_tickets",
        replace_existing=True
    )

    scheduler.start()
    logger.info("Planificateur de tâches d'arrière-plan initialisé.")
    return scheduler

