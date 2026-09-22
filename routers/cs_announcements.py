"""Routeur pour la rédaction et la diffusion d'annonces officielles du CS."""

from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from loguru import logger

from config.settings import settings
from keyboards.cs_kb import get_announcement_actions_kb, get_announcement_levels_kb

announcements_router = Router(name="announcements_router")


class AnnouncementFSM(StatesGroup):
    waiting_level = State()
    waiting_content = State()
    waiting_confirmation = State()


@announcements_router.message(F.text == "📢 Diffuser une annonce")
async def start_announcement(message: Message, state: FSMContext, is_cs: bool):
    """Démarre le parcours de rédaction d'une annonce officielle par le CS."""
    if not is_cs:
        await message.answer("⛔ Action réservée aux membres du Conseil Syndical.")
        return

    await state.clear()
    await message.answer(
        "📢 <b>DIFFUSION D'UNE ANNONCE OFFICIELLE DANS LE CHAT COPRO</b>\n\n"
        "Quel est le niveau d'importance de ce message ?",
        reply_markup=get_announcement_levels_kb(),
        parse_mode="HTML"
    )
    await state.set_state(AnnouncementFSM.waiting_level)


@announcements_router.callback_query(AnnouncementFSM.waiting_level, F.data.startswith("ann_level:"))
async def process_level(callback: CallbackQuery, state: FSMContext):
    level = callback.data.split(":")[1]
    if level == "cancel":
        await state.clear()
        await callback.message.edit_text("❌ Diffusion annulée.")
        await callback.answer()
        return

    await state.update_data(level=level)
    await callback.answer()

    await callback.message.edit_text(
        "✍️ <b>Rédigez le texte de votre annonce :</b>\n\n"
        "Vous pouvez formater votre texte ou envoyer une photo avec une légende.\n"
        "Un aperçu vous sera présenté avant publication.",
        parse_mode="HTML"
    )
    await state.set_state(AnnouncementFSM.waiting_content)


@announcements_router.message(AnnouncementFSM.waiting_content, F.text | F.photo)
async def process_content(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id if message.photo else None
    text_content = message.caption if message.photo else message.text

    await state.update_data(text_content=text_content, photo_id=photo_id)
    data = await state.get_data()
    level = data.get("level", "INFO")

    header_map = {
        "INFO": "📢 <b>INFORMATION DU CONSEIL SYNDICAL</b>",
        "IMPORTANT": "⚠️ <b>MESSAGE IMPORTANT DU CONSEIL SYNDICAL</b>",
        "URGENT": "🚨 <b>ALERTE URGENTE DU CONSEIL SYNDICAL</b>",
    }
    header = header_map.get(level, "📢 <b>COMMUNICATION CONSEIL SYNDICAL</b>")
    preview = f"{header}\n\n{text_content}\n\n<i>📅 {datetime.now().strftime('%d/%m/%Y')}</i>"

    await message.answer("👁️ <b>APERÇU DE VOTRE MESSAGE :</b>\n\n" + preview, parse_mode="HTML")
    await message.answer("Validez la diffusion ci-dessous :", reply_markup=get_announcement_actions_kb())
    await state.set_state(AnnouncementFSM.waiting_confirmation)


@announcements_router.callback_query(AnnouncementFSM.waiting_confirmation, F.data.startswith("ann_action:"))
async def handle_announcement_action(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[1]
    if action == "cancel":
        await state.clear()
        await callback.message.edit_text("❌ Diffusion abandonnée.")
        await callback.answer()
        return

    data = await state.get_data()
    level = data.get("level", "INFO")
    text_content = data.get("text_content", "")
    photo_id = data.get("photo_id")

    header_map = {
        "INFO": "📢 <b>INFORMATION DU CONSEIL SYNDICAL</b>",
        "IMPORTANT": "⚠️ <b>MESSAGE IMPORTANT DU CONSEIL SYNDICAL</b>",
        "URGENT": "🚨 <b>ALERTE URGENTE DU CONSEIL SYNDICAL</b>",
    }
    header = header_map.get(level, "📢 <b>COMMUNICATION DU CONSEIL SYNDICAL</b>")
    final_message = f"{header}\n\n{text_content}\n\n<i>📅 Publié par le Conseil Syndical le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</i>"

    if settings.COPRO_CHAT_ID != 0:
        try:
            if photo_id:
                sent_msg = await callback.bot.send_photo(
                    chat_id=settings.COPRO_CHAT_ID,
                    photo=photo_id,
                    caption=final_message,
                    parse_mode="HTML"
                )
            else:
                sent_msg = await callback.bot.send_message(
                    chat_id=settings.COPRO_CHAT_ID,
                    text=final_message,
                    parse_mode="HTML"
                )

            # Épinglage si demandé
            if action == "publish_pin":
                try:
                    await callback.bot.pin_chat_message(
                        chat_id=settings.COPRO_CHAT_ID,
                        message_id=sent_msg.message_id
                    )
                except Exception as pin_err:
                    logger.warning(f"Impossible d'épingler le message : {pin_err}")

            await callback.message.edit_text("✅ <b>Votre annonce a été publiée avec succès dans le chat copro !</b>", parse_mode="HTML")
        except Exception as e:
            await callback.message.edit_text(f"⚠️ Erreur lors de la publication dans le groupe copro : {e}")
    else:
        await callback.message.edit_text("⚠️ L'ID du groupe copro (COPRO_CHAT_ID) n'est pas configuré dans le fichier .env.")

    await state.clear()
    await callback.answer()
