"""Routeur pour l'espace d'entraide entre résidents (dons et prêts d'outils)."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import SolidarityItem, User
from keyboards.solidarity_kb import get_solidarity_menu_kb

solidarity_router = Router(name="solidarity_router")


class SolidarityFSM(StatesGroup):
    waiting_title = State()
    waiting_description = State()


@solidarity_router.message(F.text == "📦 Voisins Solidaires")
async def show_solidarity_menu(message: Message, is_approved: bool):
    if not is_approved:
        await message.answer("⚠️ Fonctionnalité réservée aux résidents validés.")
        return

    await message.answer(
        "📦 <b>ESPACE VOISINS SOLIDAIRES</b>\n\n"
        "Prêtez du matériel (perceuse, escabeau, diable) ou donnez des objets utiles (cartons, meubles, plantes) entre voisins :",
        reply_markup=get_solidarity_menu_kb(),
        parse_mode="HTML"
    )


@solidarity_router.callback_query(F.data.in_(["sol:new_donation", "sol:new_loan"]))
async def start_new_item(callback: CallbackQuery, state: FSMContext):
    item_type = "DONATION" if callback.data == "sol:new_donation" else "LOAN"
    await state.clear()
    await state.update_data(item_type=item_type)

    type_label = "un don" if item_type == "DONATION" else "un prêt de matériel"
    await callback.message.answer(
        f"📦 <b>Proposer {type_label} :</b>\n\nQuel est l'objet proposé ? (ex : <i>'Perceuse à percussion Bosch'</i>, <i>'10 cartons de déménagement'</i>) :",
        parse_mode="HTML"
    )
    await state.set_state(SolidarityFSM.waiting_title)
    await callback.answer()


@solidarity_router.message(SolidarityFSM.waiting_title, F.text)
async def process_item_title(message: Message, state: FSMContext):
    title = message.text.strip()
    await state.update_data(title=title)

    await message.answer(
        "Ajoutez une brève description (état, modalités d'emprunt ou de récupération) :",
        parse_mode="HTML"
    )
    await state.set_state(SolidarityFSM.waiting_description)


@solidarity_router.message(SolidarityFSM.waiting_description, F.text)
async def process_item_desc(message: Message, state: FSMContext, db: AsyncSession, current_user: User):
    desc = message.text.strip()
    data = await state.get_data()
    item_type = data.get("item_type", "LOAN")
    title = data.get("title", "")

    item = SolidarityItem(
        user_id=current_user.id,
        item_type=item_type,
        title=title,
        description=desc,
        is_available=True
    )
    db.add(item)
    await db.flush()

    label = "Don" if item_type == "DONATION" else "Prêt"
    await message.answer(
        f"✅ <b>Votre annonce de {label} a été publiée !</b>\n\n"
        f"• <b>Objet :</b> {title}\n"
        f"• <b>Description :</b> {desc}\n\n"
        "Les voisins intéressés pourront vous contacter directement.",
        parse_mode="HTML"
    )
    await state.clear()


@solidarity_router.callback_query(F.data == "sol:list")
async def list_solidarity_items(callback: CallbackQuery, db: AsyncSession):
    stmt = (
        select(SolidarityItem)
        .where(SolidarityItem.is_available.is_(True))
        .order_by(SolidarityItem.created_at.desc())
        .limit(10)
    )
    res = await db.execute(stmt)
    items = list(res.scalars().all())

    if not items:
        await callback.message.answer("Aucune annonce active actuellement. N'hésitez pas à en créer une !", parse_mode="HTML")
    else:
        lines = ["📦 <b>ANNONCES DISPONIBLES :</b>\n"]
        for item in items:
            badge = "🎁 [DON]" if item.item_type == "DONATION" else "🔧 [PRÊT]"
            lines.append(f"• {badge} <b>{item.title}</b>\n  <i>{item.description}</i>")
        await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()

