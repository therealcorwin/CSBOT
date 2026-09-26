"""Routeur des commandes d'administration technique (réservées aux administrateurs)."""

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.models import User
from keyboards.menu_kb import get_main_menu
from services.user_service import UserService

admin_router = Router(name="admin_router")


async def resolve_target_user(
    message: Message,
    command: CommandObject,
    db: AsyncSession,
) -> tuple[int | None, str | None, str | None]:
    """Résout l'identifiant et les informations de l'utilisateur cible.

    Retourne:
        tuple (user_id, username, error_message)
    """
    # 1. Résolution par réponse (reply) à un message
    if message.reply_to_message and message.reply_to_message.from_user:
        target_from = message.reply_to_message.from_user
        return target_from.id, target_from.username, None

    # 2. Résolution par argument
    if not command.args:
        return None, None, "NO_ARGS"

    raw_arg = command.args.strip()

    # ID numérique Telegram direct
    if raw_arg.isdigit():
        return int(raw_arg), None, None

    # Pseudo Telegram @username
    if raw_arg.startswith("@"):
        username = raw_arg.lstrip("@")
        user = await UserService.get_user_by_username(db, username)
        if user:
            return user.id, user.username, None
        return None, None, f"Aucun utilisateur trouvé avec le pseudo @{username} en base de données."

    # Numéro d'appartement
    residents = await UserService.get_occupants_by_apartment(db, raw_arg)
    if len(residents) == 1:
        u, _ = residents[0]
        return u.id, u.username, None
    if len(residents) > 1:
        details = ", ".join([f"{u.full_name} (ID: <code>{u.id}</code>)" for u, _ in residents])
        return None, None, f"Plusieurs résidents trouvés pour l'appartement N°{raw_arg} :\n{details}\n\n👉 Précisez l'ID Telegram : <code>/{command.command} &lt;ID&gt;</code>"

    return None, None, f"Paramètre « {raw_arg} » non reconnu (doit être un ID Telegram, @pseudo ou n° d'appartement)."


@admin_router.message(Command("promouvoir", "promote_cs", "promote"))
async def cmd_promote_cs(
    message: Message,
    command: CommandObject,
    db: AsyncSession,
    is_admin: bool,
):
    """Promeut un utilisateur au rôle de membre du Conseil Syndical."""
    if not is_admin:
        await message.reply("⛔ Cette commande est strictement réservée aux administrateurs.")
        return

    target_id, target_username, error = await resolve_target_user(message, command, db)

    if error == "NO_ARGS":
        await message.reply(
            "📖 <b>Utilisation de la commande /promouvoir :</b>\n\n"
            "• Répondez au message d'un résident avec <code>/promouvoir</code>\n"
            "• Ou saisissez son ID Telegram : <code>/promouvoir 123456789</code>\n"
            "• Ou son @pseudo : <code>/promouvoir @pseudo</code>\n"
            "• Ou son numéro d'appartement : <code>/promouvoir 12</code>",
            parse_mode="HTML",
        )
        return

    if error:
        await message.reply(f"⚠️ {error}", parse_mode="HTML")
        return

    # Promotion en base de données
    user = await UserService.promote_to_cs(db, target_id)
    if not user:
        # Création du profil minimum si pas encore en base
        first_name = target_username or f"Résident_{target_id}"
        user = await UserService.get_or_create_user(
            db,
            user_id=target_id,
            username=target_username,
            first_name=first_name,
        )
        user.is_cs_member = True
        user.is_approved = True
        await db.flush()

    user_label = user.full_name or f"ID {user.id}"
    username_str = f" (@{user.username})" if user.username else ""

    await message.reply(
        f"👑 <b>PROMOTION CONSEIL SYNDICAL EFFECTUÉE</b>\n\n"
        f"👤 <b>Résident :</b> {user_label}{username_str}\n"
        f"🆔 <b>ID Telegram :</b> <code>{user.id}</code>\n"
        f"🏷️ <b>Nouveau statut :</b> Membre du Conseil Syndical (CS)\n\n"
        f"L'utilisateur a désormais accès à l'<b>Espace Conseil Syndical</b>.",
        parse_mode="HTML",
    )

    # Notification en message privé au résident promu
    try:
        await message.bot.send_message(
            chat_id=user.id,
            text=(
                f"🎉 <b>Félicitations {user.first_name} !</b>\n\n"
                "Un administrateur vous a nommé <b>membre du Conseil Syndical</b>.\n\n"
                "Votre menu Telegram a été mis à jour avec le bouton "
                "<b>« 👑 Espace Conseil Syndical »</b> pour vous permettre d'accéder "
                "aux outils de gestion de la copropriété."
            ),
            reply_markup=get_main_menu(is_cs=True),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.debug(f"Notification privée non transmise à {user.id} (l'utilisateur n'a peut-être pas démarré le bot en DM) : {e}")


@admin_router.message(Command("retrograder", "demote_cs", "demote"))
async def cmd_demote_cs(
    message: Message,
    command: CommandObject,
    db: AsyncSession,
    is_admin: bool,
):
    """Rétrograde un membre du Conseil Syndical au statut de simple copropriétaire."""
    if not is_admin:
        await message.reply("⛔ Cette commande est strictement réservée aux administrateurs.")
        return

    target_id, _, error = await resolve_target_user(message, command, db)

    if error == "NO_ARGS":
        await message.reply(
            "📖 <b>Utilisation de la commande /retrograder :</b>\n\n"
            "• Répondez au message d'un membre CS avec <code>/retrograder</code>\n"
            "• Ou saisissez son ID Telegram : <code>/retrograder 123456789</code>\n"
            "• Ou son @pseudo : <code>/retrograder @pseudo</code>\n"
            "• Ou son numéro d'appartement : <code>/retrograder 12</code>",
            parse_mode="HTML",
        )
        return

    if error:
        await message.reply(f"⚠️ {error}", parse_mode="HTML")
        return

    # Sécurité : protection des Super Admins configurés dans .env
    if target_id in settings.ADMIN_IDS:
        await message.reply(
            "🛑 <b>Action refusée :</b> Cet utilisateur est configuré comme Super-Administrateur dans le fichier .env.",
            parse_mode="HTML",
        )
        return

    user = await UserService.get_user_by_id(db, target_id)
    if not user or not user.is_cs_member:
        name = user.full_name if user else f"ID {target_id}"
        await message.reply(f"ℹ️ {name} n'est pas enregistré comme membre du Conseil Syndical.")
        return

    await UserService.demote_from_cs(db, target_id)

    user_label = user.full_name or f"ID {user.id}"
    username_str = f" (@{user.username})" if user.username else ""

    await message.reply(
        f"👤 <b>RÉTROGRADATION EFFECTUÉE</b>\n\n"
        f"👤 <b>Résident :</b> {user_label}{username_str}\n"
        f"🆔 <b>ID Telegram :</b> <code>{user.id}</code>\n"
        f"🏷️ <b>Nouveau statut :</b> Simple copropriétaire / résident\n\n"
        f"Les accès à l'Espace Conseil Syndical ont été révoqués.",
        parse_mode="HTML",
    )

    # Notification en message privé au résident rétrogradé
    try:
        await message.bot.send_message(
            chat_id=user.id,
            text=(
                f"ℹ️ Bonjour {user.first_name},\n\n"
                "Votre rôle de membre du Conseil Syndical a été révoqué par un administrateur.\n\n"
                "Votre menu a été réinitialisé au statut de résident standard."
            ),
            reply_markup=get_main_menu(is_cs=False),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.debug(f"Notification privée non transmise à {user.id} : {e}")


@admin_router.message(Command("membres_cs", "cs_list"))
async def cmd_list_cs_members(
    message: Message,
    db: AsyncSession,
    is_admin: bool,
):
    """Affiche la liste complète des membres actuels du Conseil Syndical."""
    if not is_admin:
        await message.reply("⛔ Cette commande est strictement réservée aux administrateurs.")
        return

    members = await UserService.get_cs_members(db)
    if not members:
        await message.reply("📋 Aucun membre du Conseil Syndical enregistré en base de données.")
        return

    lines = [f"👑 <b>MEMBRES DU CONSEIL SYNDICAL ({len(members)}) :</b>\n"]
    for idx, u in enumerate(members, start=1):
        username_str = f" (@{u.username})" if u.username else ""
        admin_tag = " <i>[Super-Admin .env]</i>" if u.id in settings.ADMIN_IDS else ""
        apt_str = f" | Apt: {u.occupancies[0].apartment.number}" if u.occupancies and u.occupancies[0].apartment else ""
        lines.append(f"{idx}. <b>{u.full_name}</b>{username_str}{admin_tag}\n   🆔 <code>{u.id}</code>{apt_str} | 📞 {u.phone or 'N/A'}")

    await message.reply("\n".join(lines), parse_mode="HTML")
