"""Routeur pour le signalement d'incidents, pré-filtrage IA et suivi CS."""

from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.models import User
from keyboards.incident_kb import get_categories_kb, get_photo_skip_kb, get_ticket_cs_actions_kb
from services.llm.manager import llm_manager
from services.ticket_service import TicketService
from services.user_service import UserService

incidents_router = Router(name="incidents_router")


class IncidentFSM(StatesGroup):
    waiting_category = State()
    waiting_description = State()
    waiting_ai_confirmation = State()
    waiting_photo = State()


@incidents_router.message(F.text == "🔧 Signaler une panne")
async def start_incident_report(message: Message, state: FSMContext, is_approved: bool):
    """Débute le signalement d'une panne ou d'un problème matériel."""
    if not is_approved:
        await message.answer("⚠️ Votre compte doit être validé par le Conseil Syndical avant de pouvoir ouvrir un ticket.")
        return

    await state.clear()
    await message.answer(
        "🔧 <b>SIGNALEMENT D'UN INCIDENT / PANNE</b>\n\n"
        "Quelle est la catégorie du problème rencontré ?",
        reply_markup=get_categories_kb(),
        parse_mode="HTML"
    )
    await state.set_state(IncidentFSM.waiting_category)


@incidents_router.callback_query(IncidentFSM.waiting_category, F.data.startswith("inc_cat:"))
async def process_category(callback: CallbackQuery, state: FSMContext):
    cat_code = callback.data.split(":")[1]
    if cat_code == "cancel":
        await state.clear()
        await callback.message.edit_text("❌ Signalement annulé.")
        await callback.answer()
        return

    category_names = {
        "Ascenseur": "🛗 Ascenseur",
        "Plomberie": "💧 Plomberie / Fuite",
        "Electricite": "⚡ Électricité / Éclairage",
        "Parking": "🚗 Parking / Porte de garage",
        "Acces": "🚪 Portes / Digicode / Vigik",
        "EspacesVerts": "🌿 Espaces verts / Extérieur",
        "Autre": "❓ Autre incident",
    }
    category = category_names.get(cat_code, "Autre")
    await state.update_data(category=category)
    await callback.answer()

    await callback.message.edit_text(
        f"Catégorie sélectionnée : <b>{category}</b>\n\n"
        "Décrivez précisément le problème constaté ainsi que sa localisation exacte dans la résidence :",
        parse_mode="HTML"
    )
    await state.set_state(IncidentFSM.waiting_description)


@incidents_router.message(IncidentFSM.waiting_description, F.text)
async def process_description(message: Message, state: FSMContext, db: AsyncSession):
    description = message.text.strip()
    await state.update_data(description=description)

    # 1. Pré-filtrage IA
    summary = await TicketService.get_summary_for_llm(db)
    analysis = await llm_manager.prefilter_resident_request(description, known_open_tickets=summary)

    immediate_answer = analysis.get("immediate_answer")
    should_open = analysis.get("should_open_ticket", True)

    if immediate_answer and not should_open:
        # L'IA a trouvé une réponse directe (panne déjà connue ou consigne)
        await message.answer(
            f"🤖 <b>Renseignement automatique :</b>\n\n{immediate_answer}\n\n"
            "Si cela répond à votre demande, aucune action supplémentaire n'est requise.\n"
            "Si vous souhaitez quand même ouvrir un ticket formel, envoyez une photo ou cliquez sur Passer.",
            reply_markup=get_photo_skip_kb(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "📷 <b>Photo de l'incident (optionnelle) :</b>\n\n"
            "Envoyez une photo pour aider le Conseil Syndical et le prestataire à identifier le problème, "
            "ou cliquez sur <b>« ⏭️ Passer sans photo »</b>.",
            reply_markup=get_photo_skip_kb(),
            parse_mode="HTML"
        )

    await state.set_state(IncidentFSM.waiting_photo)


@incidents_router.message(IncidentFSM.waiting_photo, F.photo)
async def process_photo(message: Message, state: FSMContext, db: AsyncSession, current_user: User):
    photo_id = message.photo[-1].file_id
    await _finalize_ticket(message, state, db, current_user, photo_file_id=photo_id)


@incidents_router.callback_query(IncidentFSM.waiting_photo, F.data == "inc_photo:skip")
async def skip_photo(callback: CallbackQuery, state: FSMContext, db: AsyncSession, current_user: User):
    await callback.answer()
    await _finalize_ticket(callback.message, state, db, current_user, photo_file_id=None)


@incidents_router.callback_query(IncidentFSM.waiting_photo, F.data == "inc_photo:cancel")
async def cancel_incident(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Signalement annulé.")
    await callback.answer()


async def _finalize_ticket(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    current_user: User,
    photo_file_id: str | None = None
):
    data = await state.get_data()
    category = data.get("category", "Autre")
    description = data.get("description", "")

    # Trouver l'appartement du déclarant
    apt = await UserService.get_active_apartment_for_user(db, current_user.id)
    apt_id = apt.id if apt else None
    apt_str = f"Lot {apt.number} (Bât {apt.building}, Étage {apt.floor})" if apt else "Non renseigné"

    ticket = await TicketService.create_ticket(
        session=db,
        user_id=current_user.id,
        apartment_id=apt_id,
        category=category,
        description=description,
        photo_file_id=photo_file_id,
    )

    # Notification au résident
    await message.answer(
        f"✅ <b>Votre ticket a été créé avec succès !</b>\n\n"
        f"• <b>Numéro de référence :</b> <code>{ticket.ticket_code}</code>\n"
        f"• <b>Catégorie :</b> {category}\n"
        f"• <b>Statut :</b> 🟢 Ouvert (en attente de prise en charge par le CS)\n\n"
        "Vous serez notifié automatiquement de l'avancement du dossier.",
        parse_mode="HTML"
    )

    # Notification au groupe privé du Conseil Syndical
    if settings.CS_GROUP_ID != 0:
        cs_msg = (
            f"🚨 <b>NOUVEAU SIGNALEMENT DE PANNE ({ticket.ticket_code})</b>\n\n"
            f"🏷️ <b>Catégorie :</b> {category}\n"
            f"🏠 <b>Signalé par :</b> {current_user.full_name} ({apt_str})\n"
            f"📝 <b>Description :</b>\n{description}\n\n"
            f"📅 <i>{datetime.now().strftime('%d/%m/%Y à %H:%M')}</i>"
        )
        try:
            if photo_file_id:
                await message.bot.send_photo(
                    chat_id=settings.CS_GROUP_ID,
                    photo=photo_file_id,
                    caption=cs_msg,
                    reply_markup=get_ticket_cs_actions_kb(ticket.id),
                    parse_mode="HTML"
                )
            else:
                await message.bot.send_message(
                    chat_id=settings.CS_GROUP_ID,
                    text=cs_msg,
                    reply_markup=get_ticket_cs_actions_kb(ticket.id),
                    parse_mode="HTML"
                )
        except Exception as e:
            await message.answer(f"⚠️ Erreur notification CS : {e}")

    await state.clear()


@incidents_router.callback_query(F.data.startswith("ticket_status:"))
async def handle_ticket_status_change(callback: CallbackQuery, db: AsyncSession, is_cs: bool):
    """Prise en charge et mise à jour d'un ticket par un membre du CS."""
    if not is_cs:
        await callback.answer("⛔ Action réservée aux membres du Conseil Syndical.", show_alert=True)
        return

    parts = callback.data.split(":")
    ticket_id = int(parts[1])
    new_status = parts[2]

    ticket = await TicketService.update_status(
        session=db,
        ticket_id=ticket_id,
        new_status=new_status,
        handled_by_cs_id=callback.from_user.id
    )

    if not ticket:
        await callback.answer("Ticket introuvable.", show_alert=True)
        return

    status_labels = {
        "OPEN": "🟢 Ouvert",
        "SENT_TO_SYNDIC": "📞 Transmis au Syndic",
        "IN_PROGRESS": "🔧 Intervention planifiée / En cours",
        "RESOLVED": "✅ Résolu et clôturé",
        "CANCELLED": "❌ Annulé"
    }
    label = status_labels.get(new_status, new_status)
    cs_name = callback.from_user.first_name

    # Mise à jour du message dans le groupe CS
    now_str = datetime.now().strftime("%d/%m à %H:%M")
    update_text = f"\n\n📌 <b>Statut mis à jour :</b> {label}\n👤 <i>Par {cs_name} le {now_str}</i>"

    try:
        if callback.message.caption:
            await callback.message.edit_caption(
                caption=callback.message.caption + update_text,
                reply_markup=get_ticket_cs_actions_kb(ticket.id) if new_status not in ("RESOLVED", "CANCELLED") else None,
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                text=callback.message.text + update_text,
                reply_markup=get_ticket_cs_actions_kb(ticket.id) if new_status not in ("RESOLVED", "CANCELLED") else None,
                parse_mode="HTML"
            )
    except Exception:
        pass

    # Notification au résident qui a ouvert le ticket
    if ticket.user_id:
        try:
            await callback.bot.send_message(
                chat_id=ticket.user_id,
                text=(
                    f"📢 <b>Mise à jour de votre ticket {ticket.ticket_code} :</b>\n\n"
                    f"Le statut est maintenant : <b>{label}</b>\n"
                    "Le Conseil Syndical suit le dossier."
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass

    await callback.answer(f"Statut changé en : {label}")

