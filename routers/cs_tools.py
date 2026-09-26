import re
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.models import User, VendorVisit
from keyboards.menu_kb import get_main_menu
from services.ticket_service import TicketService
from services.user_service import UserService

cs_tools_router = Router(name="cs_tools_router")


class SearchLotFSM(StatesGroup):
    waiting_lot = State()


class VendorVisitFSM(StatesGroup):
    waiting_vendor_name = State()
    waiting_summary = State()
    waiting_date = State()


# --- VALIDATION D'INSCRIPTION PAR LE CS DANS LE GROUPE PRIVÉ ---
@cs_tools_router.callback_query(F.data.startswith("val_user:"))
async def handle_user_validation(callback: CallbackQuery, db: AsyncSession, is_cs: bool):
    """Traitement de l'approbation ou du refus d'un résident par un membre du CS."""
    if not is_cs and callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("⛔ Vous devez être membre du Conseil Syndical.", show_alert=True)
        return

    parts = callback.data.split(":")
    target_user_id = int(parts[1])
    action = parts[2]

    approver = callback.from_user
    approver_name = approver.full_name or approver.first_name
    approver_username = f"@{approver.username}" if approver.username else None

    # Format pour la base de données : Nom (@pseudo)
    if approver_username:
        approved_by_str = f"{approver_name} ({approver_username})"
    else:
        approved_by_str = approver_name or f"ID {approver.id}"

    # Format complet pour les logs console/fichier
    approver_log = f"{approver_name}"
    if approver_username:
        approver_log += f" ({approver_username})"
    approver_log += f" [ID: {approver.id}]"

    now_str = datetime.now().strftime("%d/%m à %H:%M")

    if action == "approve":
        user = await UserService.approve_user(
            db,
            user_id=target_user_id,
            approved_by=approved_by_str,
            approved_by_id=approver.id,
        )
        if not user:
            await callback.answer("Utilisateur introuvable.", show_alert=True)
            return

        logger.info(
            f"✅ Inscription validée : résident {user.id} ({user.full_name}) "
            f"validé par {approver_log}."
        )

        # Mise à jour de la fiche dans le groupe CS
        new_text = callback.message.text + f"\n\n✅ <b>VALIDÉ par {approver_name}"
        if approver.username:
            new_text += f" (@{approver.username})"
        new_text += f"</b> (ID: <code>{approver.id}</code>) le {now_str}."
        try:
            await callback.message.edit_text(new_text, reply_markup=None, parse_mode="HTML")
        except Exception:
            pass

        # Création du lien d'invitation au groupe copro
        invite_link = None
        if settings.COPRO_CHAT_ID != 0:
            try:
                link_obj = await callback.bot.create_chat_invite_link(
                    chat_id=settings.COPRO_CHAT_ID,
                    member_limit=1,
                    name=f"Invite-{user.full_name}"
                )
                invite_link = link_obj.invite_link
            except Exception as e:
                logger.warning(f"Impossible de créer un lien d'invitation automatique : {e}")

        # Notification en MP au résident
        welcome_dm = (
            f"🎉 <b>Félicitations {user.first_name} !</b>\n\n"
            "Votre inscription a été <b>validée</b> par le Conseil Syndical.\n\n"
            "Vous avez désormais accès à l'ensemble des services de Georges Bot."
        )
        if invite_link:
            welcome_dm += f"\n\n👉 <b>Rejoindre le chat de la copropriété :</b>\n{invite_link}\n\n<i>(Ce lien est strictement personnel et à usage unique).</i>"

        try:
            await callback.bot.send_message(
                chat_id=user.id,
                text=welcome_dm,
                reply_markup=get_main_menu(is_cs=user.is_cs_member),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(f"Impossible d'envoyer le message de bienvenue à {user.id} : {e}")

        await callback.answer("Résident validé et lien d'accès envoyé !")

    elif action == "reject":
        await UserService.reject_user(db, target_user_id)
        logger.info(
            f"❌ Inscription refusée : utilisateur {target_user_id} refusé par {approver_log}."
        )
        new_text = callback.message.text + f"\n\n❌ <b>REFUSÉ par {approver_name}"
        if approver.username:
            new_text += f" (@{approver.username})"
        new_text += f"</b> (ID: <code>{approver.id}</code>) le {now_str}."
        try:
            await callback.message.edit_text(new_text, reply_markup=None, parse_mode="HTML")
        except Exception:
            pass

        try:
            await callback.bot.send_message(
                chat_id=target_user_id,
                text="⚠️ Votre demande d'adhésion au chat de la copropriété n'a pas été retenue par le Conseil Syndical. Contactez directement un membre du CS en cas d'erreur.",
                parse_mode="HTML"
            )
        except Exception:
            pass

        await callback.answer("Demande refusée.")


# --- TABLEAU DE BORD DES INCIDENTS (CS) ---
@cs_tools_router.message(F.text == "📋 Tableau des incidents")
async def show_incidents_dashboard(message: Message, db: AsyncSession, is_cs: bool):
    if not is_cs:
        await message.answer("⛔ Réservé au Conseil Syndical.")
        return

    tickets = await TicketService.get_active_tickets(db)
    if not tickets:
        await message.answer("✅ <b>Aucun incident en cours.</b> Tous les tickets sont résolus !", parse_mode="HTML")
        return

    lines = ["📋 <b>INCIDENTS & PANNES EN COURS :</b>\n"]
    for t in tickets:
        apt_str = f"Lot {t.apartment.number}" if t.apartment else "Parties communes"
        status_icon = {"OPEN": "🟢", "SENT_TO_SYNDIC": "📞", "IN_PROGRESS": "🔧"}.get(t.status, "⚪")
        lines.append(
            f"• {status_icon} <b>{t.ticket_code}</b> | {t.category} ({apt_str})\n"
            f"  <i>{t.description[:80]}...</i>\n"
        )

    await message.answer("\n".join(lines), parse_mode="HTML")


# --- RECHERCHE DE LOT / OCCUPANT ---
@cs_tools_router.message(F.text == "🔍 Rechercher un lot")
async def start_search_lot(message: Message, state: FSMContext, is_cs: bool):
    if not is_cs:
        await message.answer("⛔ Réservé au Conseil Syndical.")
        return

    await state.clear()
    await message.answer(
        "🔍 <b>RECHERCHE D'OCCUPANT PAR NUMÉRO DE LOT :</b>\n\n"
        "Entrez le numéro de l'appartement recherché (ex : <code>204</code>, <code>B12</code>) :",
        parse_mode="HTML"
    )
    await state.set_state(SearchLotFSM.waiting_lot)


@cs_tools_router.message(SearchLotFSM.waiting_lot, F.text)
async def process_search_lot(message: Message, state: FSMContext, db: AsyncSession):
    lot_num = message.text.strip().upper()
    occupants = await UserService.get_occupants_by_apartment(db, lot_num)

    if not occupants:
        await message.answer(f"❌ Aucun occupant enregistré ou actif pour le lot <b>{lot_num}</b>.", parse_mode="HTML")
    else:
        lines = [f"🏠 <b>OCCUPANTS ACTUELS DU LOT {lot_num} :</b>\n"]
        for user, apt in occupants:
            lines.append(
                f"👤 <b>{user.full_name}</b> (@{user.username or 'aucun'})\n"
                f"• Statut : {user.status}\n"
                f"• Téléphone : <code>{user.phone or 'Non renseigné'}</code>\n"
                f"• Courriel : {user.email or 'Non renseigné'}\n"
                f"• Bâtiment {apt.building}, Étage {apt.floor}\n"
            )
        await message.answer("\n".join(lines), parse_mode="HTML")

    await state.clear()


# --- INSCRIPTIONS EN ATTENTE ---
@cs_tools_router.message(F.text == "⚙️ Inscriptions en attente")
async def show_pending_registrations(message: Message, db: AsyncSession, is_cs: bool):
    if not is_cs:
        await message.answer("⛔ Réservé au Conseil Syndical.")
        return

    pending = await UserService.get_pending_users(db)
    if not pending:
        await message.answer("✅ Aucune demande d'inscription en attente de validation.")
        return

    lines = [f"⚙️ <b>{len(pending)} INSCRIPTION(S) EN ATTENTE :</b>\n"]
    for u in pending:
        apt_str = u.occupancies[0].apartment.number if u.occupancies else "N/D"
        lines.append(f"• <b>{u.full_name}</b> (Lot {apt_str}) - Tél : {u.phone}")

    lines.append("\n<i>Rendez-vous dans le groupe privé du CS pour valider ou refuser les fiches.</i>")
    await message.answer("\n".join(lines), parse_mode="HTML")


def parse_visit_datetime(text: str) -> datetime | None:
    """Parse une chaîne utilisateur en datetime (supporte plusieurs formats naturels français)."""
    text_clean = text.strip().lower()
    now = datetime.now()

    if text_clean in ("maintenant", "now", "aujourd'hui", "auj"):
        return now

    if text_clean.startswith("hier"):
        return now - timedelta(days=1)

    # Heure seule aujourd'hui : "14:30", "14h30", "9h", "9h00"
    m_time = re.match(r"^(\d{1,2})[h:](\d{2})?$", text_clean)
    if m_time:
        hour = int(m_time.group(1))
        minute = int(m_time.group(2) or 0)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # Remplacer ' à ' ou ' a ' par un espace, et 'h' par ':'
    normalized = re.sub(r"\s+[àa]\s+", " ", text_clean)
    normalized = re.sub(r"(\d{1,2})h(\d{2})?", lambda m: f"{m.group(1)}:{m.group(2) or '00'}", normalized)

    formats = [
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
        "%d/%m/%y %H:%M",
        "%d/%m/%y",
        "%d/%m %H:%M",
        "%d/%m",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(normalized, fmt)
            if "%Y" not in fmt and "%y" not in fmt:
                dt = dt.replace(year=now.year)
            if "%H" not in fmt:
                dt = dt.replace(hour=12, minute=0)
            return dt
        except ValueError:
            continue

    return None


def get_vendor_date_kb() -> InlineKeyboardMarkup:
    now_str = datetime.now().strftime("%d/%m à %H:%M")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🕒 Maintenant ({now_str})", callback_data="vendor_date:now")],
            [InlineKeyboardButton(text="❌ Annuler", callback_data="vendor_date:cancel")],
        ]
    )


# --- CARNET DE PASSAGE DES PRESTATAIRES ---
@cs_tools_router.message(F.text == "🛠️ Carnet prestataires")
async def show_vendor_log(message: Message, db: AsyncSession, is_cs: bool):
    if not is_cs:
        await message.answer("⛔ Réservé au Conseil Syndical.")
        return

    stmt = select(VendorVisit).order_by(VendorVisit.visit_date.desc()).limit(10)
    res = await db.execute(stmt)
    visits = list(res.scalars().all())

    add_btn = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Enregistrer une intervention", callback_data="cs:add_vendor")]
        ]
    )

    if not visits:
        await message.answer(
            "🛠️ <b>CARNET DE PASSAGE DES PRESTATAIRES</b>\n\n"
            "Aucune intervention récente enregistrée dans le carnet.\n\n"
            "Cliquez sur le bouton ci-dessous ou tapez : <code>/prestataire &lt;Nom&gt; - &lt;Raison&gt; [- &lt;Date&gt;]</code>",
            reply_markup=add_btn,
            parse_mode="HTML",
        )
        return

    lines = ["🛠️ <b>DERNIÈRES VISITES PRESTATAIRES :</b>\n"]
    for v in visits:
        date_str = v.visit_date.strftime("%d/%m/%Y à %H:%M")
        lines.append(f"• <b>{date_str} - {v.vendor_name}</b> ({v.service_type})\n  <i>{v.intervention_summary}</i>")

    lines.append("\n<i>Ajout rapide : /prestataire &lt;Nom&gt; - &lt;Raison&gt; [- &lt;Date&gt;]</i>")
    await message.answer("\n".join(lines), reply_markup=add_btn, parse_mode="HTML")


@cs_tools_router.callback_query(F.data == "cs:add_vendor")
async def cb_add_vendor(callback: CallbackQuery, state: FSMContext, is_cs: bool):
    if not is_cs:
        await callback.answer("⛔ Réservé au Conseil Syndical.", show_alert=True)
        return
    await state.clear()
    await callback.message.answer(
        "🛠️ <b>ENREGISTREMENT D'UN PASSAGE PRESTATAIRE (1/3)</b>\n\n"
        "Quel est le nom de l'entreprise ou du prestataire ? (ex : <i>Otis, Veolia, Propreté Plus</i>) :\n\n"
        "<i>(Tapez /annuler pour abandonner)</i>",
        parse_mode="HTML",
    )
    await state.set_state(VendorVisitFSM.waiting_vendor_name)
    await callback.answer()


@cs_tools_router.message(Command("prestataire"))
async def add_vendor_command(
    message: Message, command: CommandObject, state: FSMContext, db: AsyncSession, is_cs: bool
):
    if not is_cs:
        await message.answer("⛔ Cette commande est réservée aux membres du Conseil Syndical.")
        return

    args = command.args
    if args and "-" in args:
        parts = [p.strip() for p in args.split("-")]
        vendor_name = parts[0]
        summary = parts[1] if len(parts) > 1 else ""
        visit_date = datetime.now()

        if len(parts) >= 3 and parts[2]:
            parsed = parse_visit_datetime(parts[2])
            if parsed:
                visit_date = parsed

        if vendor_name and summary:
            visit = VendorVisit(
                vendor_name=vendor_name,
                service_type="Maintenance",
                intervention_summary=summary,
                reported_by_user_id=message.from_user.id,
                visit_date=visit_date,
            )
            db.add(visit)
            await db.flush()
            await message.answer(
                f"✅ <b>Passage enregistré dans le carnet d'entretien !</b>\n\n"
                f"• <b>Prestataire :</b> {vendor_name}\n"
                f"• <b>Intervention :</b> {summary}\n"
                f"• <b>Date :</b> {visit_date.strftime('%d/%m/%Y à %H:%M')}",
                parse_mode="HTML",
            )
            return

    # Si pas d'argument ou format incomplet, on lance le guidage interactif FSM
    await state.clear()
    await message.answer(
        "🛠️ <b>ENREGISTREMENT D'UN PASSAGE PRESTATAIRE (1/3)</b>\n\n"
        "Quel est le nom de l'entreprise ou de l'artisan ? (ex : <i>Otis, Propreté Plus, Veolia</i>) :\n\n"
        "<i>(Tapez /annuler pour abandonner)</i>",
        parse_mode="HTML",
    )
    await state.set_state(VendorVisitFSM.waiting_vendor_name)


@cs_tools_router.message(VendorVisitFSM.waiting_vendor_name, F.text)
async def process_vendor_name(message: Message, state: FSMContext):
    if message.text.strip().lower() in ("/annuler", "annuler"):
        await state.clear()
        await message.answer("❌ Enregistrement annulé.")
        return

    vendor_name = message.text.strip()
    await state.update_data(vendor_name=vendor_name)
    await message.answer(
        f"🏢 Prestataire : <b>{vendor_name}</b>\n\n"
        "<b>Étape 2/3 :</b> Quel est le motif de l'intervention ou le résumé des travaux réalisés ?\n"
        "(ex : <i>Remplacement câble ascenseur, fuite colonne générale</i>) :",
        parse_mode="HTML",
    )
    await state.set_state(VendorVisitFSM.waiting_summary)


@cs_tools_router.message(VendorVisitFSM.waiting_summary, F.text)
async def process_vendor_summary(message: Message, state: FSMContext):
    if message.text.strip().lower() in ("/annuler", "annuler"):
        await state.clear()
        await message.answer("❌ Enregistrement annulé.")
        return

    summary = message.text.strip()
    await state.update_data(summary=summary)

    await message.answer(
        "📅 <b>Étape 3/3 : Date et heure de l'intervention</b>\n\n"
        "• Cliquez sur <b>🕒 Maintenant</b> ci-dessous pour utiliser la date et l'heure actuelles,\n"
        "• Ou écrivez la date et l'heure du passage.\n\n"
        "<i>Formats acceptés :</i>\n"
        "• <code>22/09/2026 à 14h30</code> (ou <code>22/09/2026 14:30</code>)\n"
        "• <code>22/09/2026</code>\n"
        "• <code>Aujourd'hui à 15h</code> (ou <code>15h30</code>)\n"
        "• <code>Hier</code>\n\n"
        "<i>(Tapez /annuler pour abandonner)</i>",
        reply_markup=get_vendor_date_kb(),
        parse_mode="HTML",
    )
    await state.set_state(VendorVisitFSM.waiting_date)


@cs_tools_router.callback_query(VendorVisitFSM.waiting_date, F.data == "vendor_date:now")
async def cb_vendor_date_now(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    vendor_name = data.get("vendor_name", "Inconnu")
    summary = data.get("summary", "")
    visit_date = datetime.now()

    visit = VendorVisit(
        vendor_name=vendor_name,
        service_type="Maintenance",
        intervention_summary=summary,
        reported_by_user_id=callback.from_user.id,
        visit_date=visit_date,
    )
    db.add(visit)
    await db.flush()
    await state.clear()

    await callback.message.edit_text(
        f"✅ <b>Passage enregistré dans le carnet d'entretien !</b>\n\n"
        f"• <b>Prestataire :</b> {vendor_name}\n"
        f"• <b>Intervention :</b> {summary}\n"
        f"• <b>Date :</b> {visit_date.strftime('%d/%m/%Y à %H:%M')}",
        parse_mode="HTML",
    )
    await callback.answer()


@cs_tools_router.callback_query(VendorVisitFSM.waiting_date, F.data == "vendor_date:cancel")
async def cb_vendor_date_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Enregistrement de l'intervention annulé.")
    await callback.answer()


@cs_tools_router.message(VendorVisitFSM.waiting_date, F.text)
async def process_vendor_date(message: Message, state: FSMContext, db: AsyncSession):
    if message.text.strip().lower() in ("/annuler", "annuler"):
        await state.clear()
        await message.answer("❌ Enregistrement annulé.")
        return

    parsed_dt = parse_visit_datetime(message.text)
    if not parsed_dt:
        await message.answer(
            "⚠️ <b>Date ou heure non reconnue.</b>\n\n"
            "Veuillez saisir un format valide (ex : <code>22/09/2026 14:30</code>, <code>22/09 à 15h</code>, <code>14h30</code>) "
            "ou cliquer sur <b>🕒 Maintenant</b> ci-dessous.\n\n"
            "<i>(Tapez /annuler pour abandonner)</i>",
            reply_markup=get_vendor_date_kb(),
            parse_mode="HTML",
        )
        return

    data = await state.get_data()
    vendor_name = data.get("vendor_name", "Inconnu")
    summary = data.get("summary", "")

    visit = VendorVisit(
        vendor_name=vendor_name,
        service_type="Maintenance",
        intervention_summary=summary,
        reported_by_user_id=message.from_user.id,
        visit_date=parsed_dt,
    )
    db.add(visit)
    await db.flush()
    await state.clear()

    await message.answer(
        f"✅ <b>Passage enregistré dans le carnet d'entretien !</b>\n\n"
        f"• <b>Prestataire :</b> {vendor_name}\n"
        f"• <b>Intervention :</b> {summary}\n"
        f"• <b>Date de l'intervention :</b> {parsed_dt.strftime('%d/%m/%Y à %H:%M')}",
        parse_mode="HTML",
    )


# --- DÉMÉNAGEMENT & RADIATION ---
@cs_tools_router.message(F.text == "🚪 Déclarer un déménagement")
async def resident_move_out(message: Message, db: AsyncSession, current_user: User):
    """Permet à un résident de déclarer son départ et de libérer le lot."""
    await UserService.move_out_user(db, current_user.id)

    # Tentative d'exclusion du groupe Telegram de la copro
    if settings.COPRO_CHAT_ID != 0:
        try:
            await message.bot.ban_chat_member(chat_id=settings.COPRO_CHAT_ID, user_id=current_user.id)
            await message.bot.unban_chat_member(chat_id=settings.COPRO_CHAT_ID, user_id=current_user.id)
        except Exception as e:
            logger.warning(f"Impossible d'exclure automatiquement le membre {current_user.id} : {e}")

    checklist = (
        "👋 <b>DÉMÉNAGEMENT ENREGISTRÉ AVEC SUCCÈS</b>\n\n"
        "Votre appartement a été libéré dans la base de données et vos accès au chat de la copro ont été révoqués.\n\n"
        "📋 <b>CHECKLIST DE DÉPART :</b>\n"
        "• Restituer l'ensemble des badges Vigik et bips de parking au propriétaire ou au CS.\n"
        "• Relever votre compteur d'eau divisionnaire.\n"
        "• Contacter le syndic pour le certificat de l'article 20-II (pré-état daté si vente).\n\n"
        "Nous vous souhaitons une excellente continuation !"
    )
    await message.answer(checklist, parse_mode="HTML")

