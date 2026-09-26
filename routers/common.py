"""Routeur pour les commandes communes, l'accueil et l'aiguillage des menus."""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ReplyKeyboardRemove

from config.settings import settings
from database.models import User
from keyboards.menu_kb import get_cs_menu, get_main_menu, get_unregistered_menu

common_router = Router(name="common_router")


@common_router.message(CommandStart())
async def cmd_start(message: Message, current_user: User | None, is_approved: bool, is_cs: bool):
    """Message d'accueil avec affichage du menu adapté au rôle."""
    if message.chat.type != "private":
        bot_info = await message.bot.get_me()
        await message.reply(
            f"👋 Bonjour ! Pour interagir avec Georges Bot et accéder à vos démarches de copropriété, "
            f"veuillez m'écrire en message privé :\n👉 @{bot_info.username}",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML",
        )
        return

    if not is_approved and not is_cs:
        # Résident ayant déjà soumis son formulaire, en attente d'approbation CS
        if current_user and current_user.phone:
            welcome_text = (
                f"👋 Bonjour <b>{current_user.first_name}</b> !\n\n"
                "⏳ <b>Votre demande d'inscription est en cours de validation par le Conseil Syndical.</b>\n\n"
                "Dès qu'un membre du CS aura validé votre fiche, vous recevrez une notification "
                "avec votre lien personnel d'accès au chat de la copropriété."
            )
            await message.answer(welcome_text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
            return

        welcome_text = (
            "👋 <b>Bienvenue sur Georges Bot !</b>\n\n"
            "Je suis l'assistant virtuel de votre résidence.\n\n"
            "Pour accéder aux fonctionnalités complètes et au groupe de discussion de la copropriété, "
            "votre compte doit être validé par un membre du <b>Conseil Syndical</b>.\n\n"
            "👉 Cliquez sur <b>« 📝 Demander l'accès à la copropriété »</b> ci-dessous pour démarrer."
        )
        await message.answer(welcome_text, reply_markup=get_unregistered_menu(), parse_mode="HTML")
        return

    name = current_user.first_name if current_user else message.from_user.first_name
    cs_badge = " [Conseil Syndical]" if is_cs else ""

    welcome_text = (
        f"👋 Bonjour <b>{name}</b>{cs_badge} !\n\n"
        "Que souhaitez-vous faire aujourd'hui ? Utilisez le menu ci-dessous pour naviguer."
    )
    await message.answer(welcome_text, reply_markup=get_main_menu(is_cs=is_cs), parse_mode="HTML")


@common_router.message(F.text == "👑 Espace Conseil Syndical")
async def open_cs_menu(message: Message, is_cs: bool):
    """Bascule vers le menu dédié au Conseil Syndical."""
    if not is_cs:
        await message.answer("⛔ Cet espace est réservé aux membres du Conseil Syndical.")
        return
    await message.answer("👑 <b>Espace Conseil Syndical</b> activé.", reply_markup=get_cs_menu(), parse_mode="HTML")


@common_router.message(F.text == "🏠 Retour Menu Résident")
async def back_to_resident_menu(message: Message, is_cs: bool):
    """Retour au menu principal résident."""
    await message.answer("🏠 Retour au menu principal.", reply_markup=get_main_menu(is_cs=is_cs), parse_mode="HTML")


@common_router.message(F.text == "ℹ️ Contacts & Infos Copro")
async def show_condo_info(message: Message):
    """Informations de base et contacts de la copropriété."""
    info_text = (
        "🏢 <b>INFORMATIONS COPROPRIÉTÉ</b>\n\n"
        "• <b>Syndic de copropriété :</b> Cabinet Gestion Immo\n"
        "  📞 01 40 00 00 00 | ✉️ syndic@exemple-immo.fr\n"
        "• <b>Horaires d'ouverture :</b> Lun - Ven : 9h00 - 12h30 / 14h00 - 18h00\n\n"
        "• <b>Gardiennage & Entretien :</b> Société Propreté Plus\n"
        "  Passage le matin du Lundi au Samedi\n\n"
        "• <b>Local Vélos & Poussettes :</b> Rez-de-chaussée (clé Vigik générale)\n"
        "• <b>Local Poubelles :</b> Sortie des bacs jaunes (Mardi & Vendredi), bacs verts (Lundi, Mercredi, Vendredi)\n"
        f"• <b>Encombrants :</b> {settings.ENCOMBRANTS_SCHEDULE}\n"
    )
    await message.answer(info_text, parse_mode="HTML")


@common_router.message(F.text == "ℹ️ À propos du bot")
async def show_about(message: Message):
    about_text = (
        "🤖 <b>Georges Bot - Assistant de Copropriété</b>\n\n"
        "Développé pour simplifier les échanges entre les résidents et le Conseil Syndical, "
        "faciliter le signalement des pannes et fluidifier la vie de l'immeuble.\n\n"
        "<i>Version 2.0 (aiogram v3 + Gemini / Mistral + CPTCOPRO)</i>"
    )
    await message.answer(about_text, parse_mode="HTML")


@common_router.message(Command("help"))
async def cmd_help(message: Message, is_cs: bool, is_admin: bool):
    help_text = (
        "📖 <b>AIDE & GUIDE DES FONCTIONNALITÉS</b>\n\n"
        "• <b>🚨 Urgences 24/7 :</b> Contacts d'astreinte immédiats (ascenseur, plomberie, coupures).\n"
        "• <b>🔧 Signaler une panne :</b> Déclarer un incident avec photo et suivi du ticket.\n"
        "• <b>💬 Poser une question (IA) :</b> Renseignements sur le règlement, le tri, les règles de vie.\n"
        "• <b>💶 Mes Charges :</b> Consultation de votre situation comptable.\n"
        "• <b>📦 Voisins Solidaires :</b> Prêts d'outils et dons entre voisins.\n"
        "• <b>💡 Boîte à idées AG :</b> Soumettre une proposition pour l'Assemblée Générale.\n"
        "• <b>🚪 Déclarer un déménagement :</b> Quitter la résidence et libérer le lot.\n"
    )
    if is_cs:
        help_text += (
            "\n👑 <b>COMMANDES CONSEIL SYNDICAL :</b>\n"
            "• <b>📢 Diffuser une annonce :</b> Message officiel dans le groupe copro.\n"
            "• <b>📋 Tableau des incidents :</b> Liste des tickets et statut d'intervention.\n"
            "• <b>🔍 Rechercher un lot :</b> /lot &lt;numéro&gt; pour voir les occupants.\n"
            "• <b>📊 Finances Copro :</b> Balance des impayés et trésorerie CPTCOPRO.\n"
            "• <b>🗳️ Créer un sondage :</b> Sondage officiel avec contrôle 1 vote par lot.\n"
        )
    if is_admin:
        help_text += (
            "\n🛠️ <b>COMMANDES ADMINISTRATEUR :</b>\n"
            "• <b>/promouvoir &lt;ID/@pseudo&gt; :</b> Nommer un membre au Conseil Syndical.\n"
            "• <b>/retrograder &lt;ID/@pseudo&gt; :</b> Rétablir un membre CS en simple copropriétaire.\n"
            "• <b>/membres_cs :</b> Afficher la liste de tous les membres du CS.\n"
        )
    await message.answer(help_text, parse_mode="HTML")


@common_router.message(Command("id", "chatid"))
async def cmd_chat_id(message: Message):
    """Affiche l'identifiant du chat (groupe ou privé) pour la configuration .env."""
    chat_id = message.chat.id
    chat_type = message.chat.type
    chat_title = message.chat.title or message.chat.full_name or "Privé"
    await message.reply(
        f"📋 <b>Informations du chat :</b>\n\n"
        f"• <b>Nom :</b> {chat_title}\n"
        f"• <b>Type :</b> <code>{chat_type}</code>\n"
        f"• <b>Chat ID :</b> <code>{chat_id}</code>\n\n"
        f"<i>Copiez cet ID dans votre .env (COPRO_CHAT_ID ou CS_GROUP_ID).</i>",
        parse_mode="HTML",
    )

