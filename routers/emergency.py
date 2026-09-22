"""Routeur pour les urgences 24/7 et astreintes techniques."""

from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.models import User
from keyboards.emergency_kb import get_emergency_kb
from services.emergency_service import EmergencyService
from services.user_service import UserService

emergency_router = Router(name="emergency_router")


class EmergencyAlertFSM(StatesGroup):
    waiting_message = State()


@emergency_router.message(F.text == "🚨 Urgence Résidence 24/7")
async def show_emergency_menu(message: Message):
    """Affiche la page d'urgence avec les numéros d'astreinte et vannes d'arrêt."""
    text = EmergencyService.get_emergency_overview()
    await message.answer(text, reply_markup=get_emergency_kb(), parse_mode="HTML")


@emergency_router.callback_query(F.data.startswith("urg_info:"))
async def handle_urg_info(callback: CallbackQuery):
    topic = callback.data.split(":")[1]
    if topic == "valves":
        msg = (
            "🚰 <b>EMPLACEMENT DES COUPURES D'URGENCE :</b>\n\n"
            f"💧 <b>Vanne générale d'eau :</b>\n{settings.WATER_VALVE_LOCATION}\n\n"
            f"⚡ <b>Coupure générale électricité (TGBT) :</b>\n{settings.ELECTRIC_ROOM_LOCATION}\n\n"
            f"🔥 <b>Coupure générale Gaz :</b>\n{settings.GAS_VALVE_LOCATION}"
        )
        await callback.message.answer(msg, parse_mode="HTML")
    elif topic == "ascenseur":
        await callback.answer(f"Appelez immédiatement le {settings.EMERGENCY_ASCENSEUR_PHONE}", show_alert=True)
    elif topic == "chauffage":
        await callback.answer(f"Astreinte chauffagiste : {settings.EMERGENCY_CHAUFFAGE_PHONE}", show_alert=True)
    elif topic == "plomberie":
        await callback.answer(f"Astreinte plomberie : {settings.EMERGENCY_PLOMBERIE_PHONE}", show_alert=True)
    await callback.answer()


@emergency_router.callback_query(F.data == "urg_action:alert_cs")
async def start_alert_cs(callback: CallbackQuery, state: FSMContext):
    """Déclenche la saisie du message d'urgence avant transmission au Conseil Syndical."""
    await state.clear()
    cancel_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Annuler", callback_data="urg:cancel")]
        ]
    )
    await callback.message.answer(
        "🚨 <b>TRANSMETTRE UNE ALERTE AU CONSEIL SYNDICAL</b>\n\n"
        "Veuillez décrire la situation d'urgence à transmettre immédiatement aux membres du CS "
        "(ex : <i>fuite d'eau importante au 2e étage, portail du parking bloqué grand ouvert, odeur anormale de gaz</i>) :\n\n"
        "<i>(Vous pouvez également envoyer une photo avec votre description, ou cliquer sur Annuler ci-dessous)</i>",
        reply_markup=cancel_kb,
        parse_mode="HTML",
    )
    await state.set_state(EmergencyAlertFSM.waiting_message)
    await callback.answer()


@emergency_router.callback_query(F.data == "urg:cancel")
async def cancel_alert_cs(callback: CallbackQuery, state: FSMContext):
    """Annule l'envoi d'alerte au CS."""
    await state.clear()
    await callback.message.edit_text("❌ Alerte au Conseil Syndical annulée.")
    await callback.answer()


@emergency_router.message(EmergencyAlertFSM.waiting_message, F.text)
async def process_alert_text(
    message: Message, state: FSMContext, db: AsyncSession, current_user: User | None
):
    """Traite le message texte d'urgence envoyé par le résident."""
    if message.text.strip().lower() in ("/annuler", "annuler"):
        await state.clear()
        await message.answer("❌ Envoi de l'alerte annulé.")
        return

    await _send_alert_to_cs(
        bot=message.bot,
        reply_to_message=message,
        state=state,
        db=db,
        current_user=current_user,
        tg_user=message.from_user,
        user_message=message.text.strip(),
        photo_file_id=None,
    )


@emergency_router.message(EmergencyAlertFSM.waiting_message, F.photo)
async def process_alert_photo(
    message: Message, state: FSMContext, db: AsyncSession, current_user: User | None
):
    """Traite une photo avec description transmise par le résident pour l'alerte."""
    photo_file_id = message.photo[-1].file_id
    caption = message.caption.strip() if message.caption else "Photo jointe (sans texte explicatif)."

    await _send_alert_to_cs(
        bot=message.bot,
        reply_to_message=message,
        state=state,
        db=db,
        current_user=current_user,
        tg_user=message.from_user,
        user_message=caption,
        photo_file_id=photo_file_id,
    )


async def _send_alert_to_cs(
    bot,
    reply_to_message: Message,
    state: FSMContext,
    db: AsyncSession,
    current_user: User | None,
    tg_user,
    user_message: str,
    photo_file_id: str | None = None,
):
    """Formate et diffuse l'alerte avec les coordonnées du résident dans le groupe CS."""
    now_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
    user_name = current_user.full_name if current_user else tg_user.full_name
    username_str = f"@{tg_user.username}" if tg_user.username else "aucun pseudo"

    apt = await UserService.get_active_apartment_for_user(db, current_user.id) if current_user else None
    apt_str = f"Lot {apt.number} (Bât {apt.building}, Étage {apt.floor})" if apt else "Lot non renseigné"
    phone_str = current_user.phone if (current_user and current_user.phone) else "Non renseigné"

    alert_card = (
        "🚨🚨🚨 <b>ALERTE URGENCE RÉSIDENCE</b> 🚨🚨🚨\n\n"
        f"👤 <b>Résident :</b> {user_name} ({username_str})\n"
        f"🏠 <b>Logement :</b> {apt_str}\n"
        f"📞 <b>Téléphone :</b> {phone_str}\n"
        f"📅 <b>Date & Heure :</b> {now_str}\n\n"
        f"⚠️ <b>MESSAGE D'URGENCE TRANSMIS :</b>\n"
        f"<i>{user_message}</i>"
    )

    if settings.CS_GROUP_ID != 0:
        try:
            if photo_file_id:
                await bot.send_photo(
                    chat_id=settings.CS_GROUP_ID,
                    photo=photo_file_id,
                    caption=alert_card,
                    parse_mode="HTML",
                )
            else:
                await bot.send_message(
                    chat_id=settings.CS_GROUP_ID,
                    text=alert_card,
                    parse_mode="HTML",
                )

            await reply_to_message.answer(
                "✅ <b>Votre message d'urgence a été transmis au Conseil Syndical !</b>\n\n"
                "Les membres du CS ont reçu votre notification avec vos coordonnées pour intervenir rapidement.\n\n"
                "<i>ℹ️ Rappel : En cas de danger immédiat pour les personnes ou incendie, contactez en priorité les secours au 18 ou 112.</i>",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Erreur envoi alerte CS : {e}")
            await reply_to_message.answer(f"⚠️ Erreur lors de l'envoi de l'alerte au CS : {e}")
    else:
        await reply_to_message.answer("⚠️ Le groupe du Conseil Syndical n'est pas configuré dans le bot.")

    await state.clear()
