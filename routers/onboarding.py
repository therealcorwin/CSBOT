"""Routeur d'onboarding : formulaire FSM d'inscription des résidents et soumission au CS."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from keyboards.cs_kb import get_registration_validation_kb
from keyboards.onboarding_kb import get_confirmation_kb, get_phone_kb, get_status_kb
from services.user_service import UserService

onboarding_router = Router(name="onboarding_router")


class OnboardingFSM(StatesGroup):
    waiting_status = State()
    waiting_apt_number = State()
    waiting_building_floor = State()
    waiting_name = State()
    waiting_phone = State()
    waiting_email = State()
    waiting_confirmation = State()


@onboarding_router.message(F.text == "📝 Demander l'accès à la copropriété")
async def start_onboarding(message: Message, state: FSMContext, is_approved: bool):
    """Démarre le parcours d'inscription pour un nouveau résident."""
    if is_approved:
        await message.answer("✅ Votre profil est déjà validé. Vous avez un accès complet au bot !")
        return

    await state.clear()
    await message.answer(
        "👋 <b>Bienvenue dans le processus d'adhésion à la copropriété.</b>\n\n"
        "Pour valider votre entrée et maintenir un annuaire à jour, merci de renseigner ces quelques informations.\n\n"
        "1️⃣ <b>Quel est votre statut dans l'immeuble ?</b>",
        reply_markup=get_status_kb(),
        parse_mode="HTML"
    )
    await state.set_state(OnboardingFSM.waiting_status)


@onboarding_router.callback_query(OnboardingFSM.waiting_status, F.data.startswith("status:"))
async def process_status(callback: CallbackQuery, state: FSMContext):
    status_val = callback.data.split(":")[1]
    await state.update_data(status=status_val)
    await callback.answer()

    await callback.message.edit_text(
        "2️⃣ <b>Quel est votre numéro d'appartement ou de lot ?</b>\n"
        "<i>(Exemple : 204, B12, Lot 45)</i>",
        parse_mode="HTML"
    )
    await state.set_state(OnboardingFSM.waiting_apt_number)


@onboarding_router.message(OnboardingFSM.waiting_apt_number, F.text)
async def process_apt_number(message: Message, state: FSMContext):
    apt_num = message.text.strip().upper()
    await state.update_data(apartment_number=apt_num)

    await message.answer(
        "3️⃣ <b>À quel bâtiment et étage habitez-vous ?</b>\n"
        "<i>(Exemple : Bâtiment B, 2ème étage - ou simplement 'B2')</i>",
        parse_mode="HTML"
    )
    await state.set_state(OnboardingFSM.waiting_building_floor)


@onboarding_router.message(OnboardingFSM.waiting_building_floor, F.text)
async def process_building_floor(message: Message, state: FSMContext):
    text = message.text.strip()
    # Parsing simple
    building = "A"
    floor = 0
    if "bâtiment" in text.lower() or "bat" in text.lower():
        words = text.split()
        for i, w in enumerate(words):
            if w.lower() in ("bâtiment", "bat", "bât") and i + 1 < len(words):
                building = words[i + 1].upper()
    try:
        # Essayer d'extraire un chiffre pour l'étage
        for char in text:
            if char.isdigit():
                floor = int(char)
                break
    except Exception:
        floor = 0

    await state.update_data(building=building, floor=floor, building_floor_text=text)

    await message.answer(
        "4️⃣ <b>Quels sont vos Nom et Prénom ?</b>\n"
        "<i>(Exemple : Marie DUPONT)</i>",
        parse_mode="HTML"
    )
    await state.set_state(OnboardingFSM.waiting_name)


@onboarding_router.message(OnboardingFSM.waiting_name, F.text)
async def process_name(message: Message, state: FSMContext):
    full_name = message.text.strip()
    parts = full_name.split(maxsplit=1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""

    await state.update_data(first_name=first_name, last_name=last_name)

    await message.answer(
        "5️⃣ <b>Quel est votre numéro de téléphone ?</b>\n"
        "<i>Vous pouvez utiliser le bouton ci-dessous pour partager votre contact Telegram ou le saisir manuellement.</i>",
        reply_markup=get_phone_kb(),
        parse_mode="HTML"
    )
    await state.set_state(OnboardingFSM.waiting_phone)


@onboarding_router.message(OnboardingFSM.waiting_phone, F.contact | F.text)
async def process_phone(message: Message, state: FSMContext):
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text.strip()

    await state.update_data(phone=phone)

    await message.answer(
        "6️⃣ <b>Quelle est votre adresse e-mail ?</b>\n"
        "<i>(Pour les communications officielles du Conseil Syndical)</i>",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )
    await state.set_state(OnboardingFSM.waiting_email)


@onboarding_router.message(OnboardingFSM.waiting_email, F.text)
async def process_email(message: Message, state: FSMContext):
    email = message.text.strip()
    await state.update_data(email=email)

    data = await state.get_data()
    status_label = {
        "OWNER_OCCUPANT": "🏠 Copropriétaire occupant",
        "TENANT": "🔑 Locataire",
        "OWNER_NON_RESIDENT": "📑 Copropriétaire bailleur"
    }.get(data.get("status", ""), "Résident")

    summary_text = (
        "📋 <b>RÉCAPITULATIF DE VOTRE DEMANDE :</b>\n\n"
        f"• <b>Identité :</b> {data.get('first_name')} {data.get('last_name')}\n"
        f"• <b>Statut :</b> {status_label}\n"
        f"• <b>Appartement / Lot :</b> {data.get('apartment_number')}\n"
        f"• <b>Bâtiment & Étage :</b> {data.get('building_floor_text')}\n"
        f"• <b>Téléphone :</b> {data.get('phone')}\n"
        f"• <b>E-mail :</b> {data.get('email')}\n\n"
        "Souhaitez-vous transmettre cette fiche aux membres du Conseil Syndical pour validation ?"
    )

    await message.answer(summary_text, reply_markup=get_confirmation_kb(), parse_mode="HTML")
    await state.set_state(OnboardingFSM.waiting_confirmation)


@onboarding_router.callback_query(OnboardingFSM.waiting_confirmation, F.data == "onboarding:confirm")
async def confirm_onboarding(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    user_id = callback.from_user.id

    # Enregistrement en base
    user, apartment = await UserService.submit_onboarding(db, user_id=user_id, data=data)

    status_label = {
        "OWNER_OCCUPANT": "Copropriétaire occupant",
        "TENANT": "Locataire",
        "OWNER_NON_RESIDENT": "Copropriétaire bailleur"
    }.get(user.status, "Résident")

    # Notification au Conseil Syndical
    if settings.CS_GROUP_ID != 0:
        cs_card = (
            "🔔 <b>NOUVELLE DEMANDE D'INSCRIPTION RÉSIDENT</b>\n\n"
            f"👤 <b>Nom :</b> {user.full_name} (@{callback.from_user.username or 'aucun'})\n"
            f"🏠 <b>Appartement :</b> {apartment.number} (Bâtiment {apartment.building}, Étage {apartment.floor})\n"
            f"🏷️ <b>Statut :</b> {status_label}\n"
            f"📞 <b>Téléphone :</b> {user.phone}\n"
            f"✉️ <b>Courriel :</b> {user.email}\n"
            f"🆔 <b>ID Telegram :</b> <code>{user.id}</code>"
        )
        try:
            await callback.bot.send_message(
                chat_id=settings.CS_GROUP_ID,
                text=cs_card,
                reply_markup=get_registration_validation_kb(user.id),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Erreur de notification au CS (CS_GROUP_ID={settings.CS_GROUP_ID}) : {e}")
            await callback.message.answer(f"⚠️ Erreur de notification au CS : {e}")

    await state.clear()
    await callback.message.edit_text(
        "✅ <b>Votre demande a été transmise au Conseil Syndical !</b>\n\n"
        "Un membre du CS va vérifier vos informations. Dès validation, vous recevrez une notification "
        "avec votre lien d'accès au chat de la copropriété.",
        parse_mode="HTML"
    )
    await callback.answer()


@onboarding_router.callback_query(OnboardingFSM.waiting_confirmation, F.data == "onboarding:restart")
async def restart_onboarding(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🔄 <b>Saisie réinitialisée.</b> Cliquez à nouveau sur le bouton ci-dessous pour recommencer.",
        parse_mode="HTML"
    )
    await callback.answer()

