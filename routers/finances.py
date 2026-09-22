"""Routeur de consultation financière en synergie avec CPTCOPRO."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from keyboards.finance_kb import get_finance_cs_kb, get_finance_resident_kb
from services.cptcopro_service import cptcopro_service
from services.user_service import UserService

finances_router = Router(name="finances_router")


@finances_router.message(F.text == "💶 Mes Charges & Compte")
async def resident_finance_menu(message: Message, is_approved: bool):
    if not is_approved:
        await message.answer("⚠️ Fonctionnalité réservée aux résidents validés.")
        return

    await message.answer(
        "💶 <b>CONSULTATION COMPTABLE DU LOT (CPTCOPRO)</b>\n\n"
        "Accédez à votre situation de charges personnelles en toute confidentialité :",
        reply_markup=get_finance_resident_kb(),
        parse_mode="HTML"
    )


@finances_router.callback_query(F.data == "fin:my_balance")
async def show_my_balance(callback: CallbackQuery, db: AsyncSession, current_user: User):
    apt = await UserService.get_active_apartment_for_user(db, current_user.id)
    if not apt:
        await callback.message.answer("⚠️ Aucun lot actif associé à votre compte.")
        await callback.answer()
        return

    res = await cptcopro_service.get_user_charges(apt.number)
    if res.get("connected"):
        balance_text = (
            f"🏠 <b>SITUATION COMPTABLE - LOT {apt.number} :</b>\n\n"
            f"• <b>Solde actuel :</b> <b>{res.get('balance')}</b>\n"
            f"• <b>Date d'arrêté comptable :</b> {res.get('date', 'N/D')}\n"
            f"• <b>Statut :</b> {res.get('status', 'À jour')}\n\n"
            f"<i>{res.get('message', '')}</i>"
        )
    else:
        balance_text = (
            f"🏠 <b>LOT {apt.number}</b>\n\n"
            f"ℹ️ {res.get('message')}"
        )

    await callback.message.answer(balance_text, parse_mode="HTML")
    await callback.answer()


@finances_router.callback_query(F.data == "fin:dates")
async def show_call_dates(callback: CallbackQuery):
    dates_text = (
        "📅 <b>CALENDRIER DES APPELS DE FONDS :</b>\n\n"
        "• <b>1er Trimestre :</b> 1er Janvier\n"
        "• <b>2ème Trimestre :</b> 1er Avril\n"
        "• <b>3ème Trimestre :</b> 1er Juillet\n"
        "• <b>4ème Trimestre :</b> 1er Octobre\n\n"
        "<i>Règlement par prélèvement automatique ou virement bancaire sur le compte du syndic.</i>"
    )
    await callback.message.answer(dates_text, parse_mode="HTML")
    await callback.answer()


@finances_router.message(F.text == "📊 Finances Copro (CPTCOPRO)")
async def cs_finance_menu(message: Message, is_cs: bool):
    if not is_cs:
        await message.answer("⛔ Réservé aux membres du Conseil Syndical.")
        return

    summary = await cptcopro_service.get_cs_financial_summary()
    cs_finance_text = (
        "📊 <b>SYNTHÈSE FINANCIÈRE DE LA COPROPRIÉTÉ (CPTCOPRO)</b>\n\n"
        f"• <b>Total des impayés débiteurs :</b> <b>{summary.get('total_unpaid')}</b>\n"
        f"• <b>Nombre de lots en retard de paiement :</b> {summary.get('lots_in_debt')}\n"
        f"• <b>Trésorerie globale estimée :</b> {summary.get('treasury', 'N/D')}\n\n"
        f"<i>{summary.get('message', '')}</i>"
    )
    await message.answer(cs_finance_text, reply_markup=get_finance_cs_kb(), parse_mode="HTML")


@finances_router.callback_query(F.data == "fin_cs:unpaid")
async def show_cs_unpaid(callback: CallbackQuery, is_cs: bool):
    if not is_cs:
        await callback.answer("Action réservée au CS.", show_alert=True)
        return

    summary = await cptcopro_service.get_cs_financial_summary()
    await callback.message.answer(
        f"📉 <b>DÉTAIL DES IMPAYÉS :</b>\n\n"
        f"Montant total à recouvrer : <b>{summary.get('total_unpaid')}</b> répartis sur {summary.get('lots_in_debt')} lots.\n\n"
        "<i>Les courriers de relance générés par Mistral AI sont disponibles dans l'interface Streamlit de CPTCOPRO.</i>",
        parse_mode="HTML"
    )
    await callback.answer()

