"""Routeur pour les sondages officiels certifiés par appartement (1 vote par lot)."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from services.poll_service import PollService

polls_router = Router(name="polls_router")


class CreatePollFSM(StatesGroup):
    waiting_title = State()
    waiting_options = State()


@polls_router.message(F.text == "🗳️ Créer un sondage")
async def start_create_poll(message: Message, state: FSMContext, is_cs: bool):
    """Initialise la création d'un sondage par le Conseil Syndical."""
    if not is_cs:
        await message.answer("⛔ Action réservée aux membres du Conseil Syndical.")
        return

    await state.clear()
    await message.answer(
        "🗳️ <b>CRÉATION D'UN SONDAGE CERTIFIÉ (1 VOTE PAR LOT)</b>\n\n"
        "Quelle est la question ou l'objet de la consultation ?",
        parse_mode="HTML"
    )
    await state.set_state(CreatePollFSM.waiting_title)


@polls_router.message(CreatePollFSM.waiting_title, F.text)
async def process_poll_title(message: Message, state: FSMContext):
    title = message.text.strip()
    await state.update_data(title=title)

    await message.answer(
        "Indiquez les options de réponse possibles, <b>séparées par une virgule</b> :\n"
        "<i>(Exemple : Pour, Contre, Abstention - ou : Lundi soir, Mardi soir, Mercredi soir)</i>",
        parse_mode="HTML"
    )
    await state.set_state(CreatePollFSM.waiting_options)


@polls_router.message(CreatePollFSM.waiting_options, F.text)
async def process_poll_options(message: Message, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    title = data.get("title", "")
    raw_opts = message.text.split(",")
    options = [o.strip() for o in raw_opts if o.strip()]

    if len(options) < 2:
        await message.answer("⚠️ Merci de fournir au moins 2 options valides séparées par des virgules.")
        return

    poll = await PollService.create_poll(
        session=db,
        title=title,
        options=options,
        created_by_user_id=message.from_user.id
    )

    # Clavier de vote
    buttons = [
        [InlineKeyboardButton(text=opt, callback_data=f"poll_vote:{poll.id}:{idx}")]
        for idx, opt in enumerate(options)
    ]
    vote_kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    poll_announcement = (
        "🗳️ <b>CONSULTATION OFFICIELLE DE LA COPROPRIÉTÉ</b>\n\n"
        f"❓ <b>{title}</b>\n\n"
        "<i>Règle : 1 seul vote est comptabilisé par appartement. "
        "Le premier vote exprimé pour votre lot sera validé.</i>"
    )

    # Diffusion dans le groupe copro ou au CS
    if settings.COPRO_CHAT_ID != 0:
        try:
            await message.bot.send_message(
                chat_id=settings.COPRO_CHAT_ID,
                text=poll_announcement,
                reply_markup=vote_kb,
                parse_mode="HTML"
            )
        except Exception:
            pass

    await message.answer(
        "✅ <b>Sondage créé et publié avec succès !</b>\n\n"
        "Consultez les résultats en direct à tout moment avec la commande : <code>/resultats_sondage</code>",
        reply_markup=vote_kb,
        parse_mode="HTML"
    )
    await state.clear()


@polls_router.callback_query(F.data.startswith("poll_vote:"))
async def handle_poll_vote(callback: CallbackQuery, db: AsyncSession):
    """Enregistre le vote d'un résident avec vérification d'unicité par lot."""
    parts = callback.data.split(":")
    poll_id = int(parts[1])
    option_idx = int(parts[2])

    success, msg = await PollService.cast_vote(
        session=db,
        poll_id=poll_id,
        user_id=callback.from_user.id,
        option_index=option_idx
    )

    await callback.answer(msg, show_alert=True)


@polls_router.message(Command("resultats_sondage"))
async def show_poll_results(message: Message, db: AsyncSession, is_cs: bool):
    """Affiche les résultats du dernier sondage actif pour le CS."""
    if not is_cs:
        await message.answer("⛔ Réservé au Conseil Syndical.")
        return

    active_poll = await PollService.get_active_poll(db)
    if not active_poll:
        await message.answer("Aucun sondage actif pour le moment.")
        return

    res = await PollService.get_results(db, active_poll.id)
    title = res.get("title")
    total = res.get("total_votes", 0)
    choices = res.get("choices", [])
    counts = res.get("counts", {})
    voted_lots = res.get("voted_lots", [])

    lines = [
        f"📊 <b>RÉSULTATS DU SONDAGE :</b>\n❓ <i>{title}</i>\n",
        f"👥 <b>Participation :</b> {total} appartement(s) ont voté\n"
    ]
    for idx, choice in enumerate(choices):
        cnt = counts.get(idx, 0)
        pct = (cnt / total * 100) if total > 0 else 0
        lines.append(f"• <b>{choice} :</b> {cnt} vote(s) ({pct:.1f}%)")

    if voted_lots:
        lines.append(f"\n🏠 <b>Lots ayant participé :</b> {', '.join(voted_lots)}")

    await message.answer("\n".join(lines), parse_mode="HTML")

