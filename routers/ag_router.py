"""Routeur pour la préparation d'AG (boîte à idées et bourse aux pouvoirs)."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AGIdea, User
from keyboards.ag_kb import get_ag_menu_kb

ag_router = Router(name="ag_router")


class IdeaFSM(StatesGroup):
    waiting_title = State()
    waiting_description = State()


@ag_router.message(F.text == "💡 Boîte à idées AG")
async def show_ag_hub(message: Message, is_approved: bool):
    if not is_approved:
        await message.answer("⚠️ Fonctionnalité réservée aux résidents validés.")
        return

    await message.answer(
        "💡 <b>ESPACE PRÉPARATION ASSEMBLÉE GÉNÉRALE</b>\n\n"
        "Proposez des projets pour la résidence ou organisez la délégation de votre pouvoir de vote :",
        reply_markup=get_ag_menu_kb(),
        parse_mode="HTML"
    )


@ag_router.callback_query(F.data == "ag:new_idea")
async def start_new_idea(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(
        "💡 <b>PROPOSER UNE RÉSOLUTION POUR LA PROCHAINE AG :</b>\n\n"
        "Donnez un titre court à votre idée (ex : <i>'Installation de prises pour vélos électriques'</i>) :",
        parse_mode="HTML"
    )
    await state.set_state(IdeaFSM.waiting_title)
    await callback.answer()


@ag_router.message(IdeaFSM.waiting_title, F.text)
async def process_idea_title(message: Message, state: FSMContext):
    title = message.text.strip()
    await state.update_data(title=title)

    await message.answer(
        "Détaillez votre proposition (bénéfice pour l'immeuble, coût estimé si connu, contraintes) :",
        parse_mode="HTML"
    )
    await state.set_state(IdeaFSM.waiting_description)


@ag_router.message(IdeaFSM.waiting_description, F.text)
async def process_idea_description(message: Message, state: FSMContext, db: AsyncSession, current_user: User):
    desc = message.text.strip()
    data = await state.get_data()
    title = data.get("title", "")

    idea = AGIdea(
        user_id=current_user.id,
        title=title,
        description=desc,
        status="PROPOSED"
    )
    db.add(idea)
    await db.flush()

    await message.answer(
        "✅ <b>Votre proposition a été enregistrée dans la boîte à idées !</b>\n\n"
        "Le Conseil Syndical l'étudiera lors de la préparation de l'ordre du jour avec le syndic.",
        parse_mode="HTML"
    )
    await state.clear()


@ag_router.callback_query(F.data == "ag:list_ideas")
async def list_ideas(callback: CallbackQuery, db: AsyncSession):
    stmt = select(AGIdea).order_by(AGIdea.created_at.desc()).limit(10)
    res = await db.execute(stmt)
    ideas = list(res.scalars().all())

    if not ideas:
        await callback.message.answer("Aucune idée soumise pour l'instant. Soyez le premier !", parse_mode="HTML")
    else:
        lines = ["📋 <b>PROPOSITIONS CITOYENNES POUR L'AG :</b>\n"]
        for i in ideas:
            lines.append(f"• 💡 <b>{i.title}</b>\n  <i>{i.description[:100]}...</i>")
        await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()


@ag_router.callback_query(F.data == "ag:power_proxy")
async def ag_proxy(callback: CallbackQuery):
    proxy_info = (
        "🤝 <b>BOURSE AUX POUVOIRS D'AG</b>\n\n"
        "Vous ne pouvez pas assister à l'Assemblée Générale ?\n\n"
        "Ne laissez pas votre voix vacante ! Donnez votre pouvoir à un voisin présent pour garantir le quorum.\n\n"
        "• Un copropriétaire ne peut détenir plus de 3 pouvoirs ou 10% des voix.\n"
        "• Pour déléguer votre pouvoir, vous pouvez poster une demande sur le groupe de la copropriété ou contacter le Conseil Syndical."
    )
    await callback.message.answer(proxy_info, parse_mode="HTML")
    await callback.answer()

