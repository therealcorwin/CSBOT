"""Gestionnaire des demandes d'adhésion au chat de copropriété (ChatJoinRequest)."""

from aiogram import Router
from aiogram.types import ChatJoinRequest
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from services.user_service import UserService

join_requests_router = Router(name="join_requests_router")


@join_requests_router.chat_join_request()
async def handle_chat_join_request(event: ChatJoinRequest, db: AsyncSession):
    """Intercepte les demandes d'entrée dans le groupe de la copropriété."""
    user_id = event.from_user.id
    user = await UserService.get_user_by_id(db, user_id)

    if user and user.is_approved:
        # Utilisateur déjà validé par le Conseil Syndical -> Approbation immédiate
        try:
            await event.approve()
            logger.info(f"Demande d'adhésion approuvée automatiquement pour {user.full_name} ({user_id})")
            await event.bot.send_message(
                chat_id=user_id,
                text="🎉 <b>Bienvenue dans le chat de la copropriété !</b>\nVotre accès a été validé automatiquement.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'approbation de la demande pour {user_id} : {e}")
    else:
        # Utilisateur inconnu ou non validé
        logger.warning(f"Demande d'adhésion refusée/en attente pour {user_id} (non validé par le CS)")
        try:
            await event.bot.send_message(
                chat_id=user_id,
                text=(
                    "👋 <b>Demande d'accès au chat de la copropriété :</b>\n\n"
                    "L'accès à ce groupe est strictement réservé aux résidents validés par le Conseil Syndical.\n\n"
                    "👉 Merci de démarrer le bot avec <b>/start</b> et de renseigner vos coordonnées pour obtenir l'approbation."
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass

