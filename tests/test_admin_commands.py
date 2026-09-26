"""Tests unitaires pour les commandes d'administration (/promouvoir, /retrograder, /membres_cs)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.filters import CommandObject
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.models import User
from routers.admin import cmd_demote_cs, cmd_list_cs_members, cmd_promote_cs
from services.user_service import UserService


@pytest.mark.asyncio
async def test_promote_command_non_admin(test_db: AsyncSession):
    """Un non-admin ne peut pas exécuter /promouvoir."""
    message = AsyncMock()
    command = CommandObject(prefix="/", command="promouvoir", args="12345")

    await cmd_promote_cs(message, command, test_db, is_admin=False)

    message.reply.assert_called_once()
    assert "strictement réservée aux administrateurs" in message.reply.call_args[0][0]


@pytest.mark.asyncio
async def test_promote_command_no_args(test_db: AsyncSession):
    """Sans argument ni réponse, la commande affiche l'aide d'utilisation."""
    message = AsyncMock()
    message.reply_to_message = None
    command = CommandObject(prefix="/", command="promouvoir", args=None)

    await cmd_promote_cs(message, command, test_db, is_admin=True)

    message.reply.assert_called_once()
    assert "Utilisation de la commande /promouvoir" in message.reply.call_args[0][0]


@pytest.mark.asyncio
async def test_promote_command_by_id(test_db: AsyncSession):
    """Un admin peut promouvoir un utilisateur via son ID Telegram."""
    target_id = 112233
    await UserService.get_or_create_user(test_db, user_id=target_id, first_name="Paul", last_name="Durand")

    message = AsyncMock()
    message.reply_to_message = None
    message.bot = AsyncMock()
    command = CommandObject(prefix="/", command="promouvoir", args=str(target_id))

    await cmd_promote_cs(message, command, test_db, is_admin=True)

    message.reply.assert_called_once()
    assert "PROMOTION CONSEIL SYNDICAL EFFECTUÉE" in message.reply.call_args[0][0]

    # Vérification BDD
    user = await UserService.get_user_by_id(test_db, target_id)
    assert user.is_cs_member is True
    assert user.is_approved is True

    # Vérification notification DM envoyée à l'utilisateur
    message.bot.send_message.assert_called_once()
    assert message.bot.send_message.call_args.kwargs["chat_id"] == target_id


@pytest.mark.asyncio
async def test_promote_command_by_reply(test_db: AsyncSession):
    """Un admin peut promouvoir en répondant au message d'un utilisateur."""
    target_id = 445566
    await UserService.get_or_create_user(test_db, user_id=target_id, first_name="Nathalie")

    reply_user = MagicMock()
    reply_user.id = target_id
    reply_user.username = "nathalie_copro"

    message = AsyncMock()
    message.reply_to_message = MagicMock()
    message.reply_to_message.from_user = reply_user
    message.bot = AsyncMock()
    command = CommandObject(prefix="/", command="promouvoir", args=None)

    await cmd_promote_cs(message, command, test_db, is_admin=True)

    message.reply.assert_called_once()
    assert "PROMOTION CONSEIL SYNDICAL EFFECTUÉE" in message.reply.call_args[0][0]

    user = await UserService.get_user_by_id(test_db, target_id)
    assert user.is_cs_member is True


@pytest.mark.asyncio
async def test_promote_command_by_username(test_db: AsyncSession):
    """Un admin peut promouvoir via @username."""
    target_id = 778899
    await UserService.get_or_create_user(test_db, user_id=target_id, username="lucas_immo", first_name="Lucas")

    message = AsyncMock()
    message.reply_to_message = None
    message.bot = AsyncMock()
    command = CommandObject(prefix="/", command="promouvoir", args="@lucas_immo")

    await cmd_promote_cs(message, command, test_db, is_admin=True)

    message.reply.assert_called_once()
    assert "PROMOTION CONSEIL SYNDICAL EFFECTUÉE" in message.reply.call_args[0][0]

    user = await UserService.get_user_by_id(test_db, target_id)
    assert user.is_cs_member is True


@pytest.mark.asyncio
async def test_demote_command_non_admin(test_db: AsyncSession):
    """Un non-admin ne peut pas exécuter /retrograder."""
    message = AsyncMock()
    command = CommandObject(prefix="/", command="retrograder", args="12345")

    await cmd_demote_cs(message, command, test_db, is_admin=False)

    message.reply.assert_called_once()
    assert "strictement réservée aux administrateurs" in message.reply.call_args[0][0]


@pytest.mark.asyncio
async def test_demote_super_admin_protection(test_db: AsyncSession):
    """Interdiction stricte de rétrograder un super-admin listé dans ADMIN_IDS."""
    super_admin_id = 1726678699
    settings.ADMIN_IDS = [super_admin_id]

    message = AsyncMock()
    message.reply_to_message = None
    command = CommandObject(prefix="/", command="retrograder", args=str(super_admin_id))

    await cmd_demote_cs(message, command, test_db, is_admin=True)

    message.reply.assert_called_once()
    assert "Super-Administrateur" in message.reply.call_args[0][0]


@pytest.mark.asyncio
async def test_demote_command_success(test_db: AsyncSession):
    """Un admin peut rétrograder un membre CS en simple copropriétaire."""
    target_id = 556677
    user = await UserService.get_or_create_user(test_db, user_id=target_id, first_name="Eric")
    user.is_cs_member = True
    await test_db.flush()

    message = AsyncMock()
    message.reply_to_message = None
    message.bot = AsyncMock()
    command = CommandObject(prefix="/", command="retrograder", args=str(target_id))

    await cmd_demote_cs(message, command, test_db, is_admin=True)

    message.reply.assert_called_once()
    assert "RÉTROGRADATION EFFECTUÉE" in message.reply.call_args[0][0]

    # Vérification BDD
    user_after = await UserService.get_user_by_id(test_db, target_id)
    assert user_after.is_cs_member is False

    # Notification DM
    message.bot.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_demote_user_not_cs(test_db: AsyncSession):
    """Rétrograder un utilisateur qui n'est pas CS renvoie un message d'information."""
    target_id = 998877
    await UserService.get_or_create_user(test_db, user_id=target_id, first_name="Julien")

    message = AsyncMock()
    message.reply_to_message = None
    command = CommandObject(prefix="/", command="retrograder", args=str(target_id))

    await cmd_demote_cs(message, command, test_db, is_admin=True)

    message.reply.assert_called_once()
    assert "n'est pas enregistré comme membre" in message.reply.call_args[0][0]


@pytest.mark.asyncio
async def test_list_cs_members_command(test_db: AsyncSession):
    """Un admin peut lister tous les membres du CS."""
    user = await UserService.get_or_create_user(test_db, user_id=123123, first_name="Benoit")
    user.is_cs_member = True
    await test_db.flush()

    message = AsyncMock()
    await cmd_list_cs_members(message, test_db, is_admin=True)

    message.reply.assert_called_once()
    assert "MEMBRES DU CONSEIL SYNDICAL" in message.reply.call_args[0][0]
    assert "Benoit" in message.reply.call_args[0][0]
