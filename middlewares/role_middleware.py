"""Middleware de détection et injection des rôles utilisateur (Résident, CS, Admin)."""

from typing import Any, Awaitable, Callable, Dict, Optional
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from config.settings import settings
from database.models import User


class RoleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user: Optional[TgUser] = data.get("event_from_user")
        db: Optional[AsyncSession] = data.get("db")

        current_user: Optional[User] = None
        is_approved = False
        is_cs = False
        is_admin = False

        if tg_user:
            # Vérification Super Admin par ID de configuration
            if tg_user.id in settings.ADMIN_IDS:
                is_admin = True
                is_cs = True

            if db:
                stmt = select(User).where(User.id == tg_user.id)
                res = await db.execute(stmt)
                current_user = res.scalar_one_or_none()

                if current_user:
                    is_approved = current_user.is_approved
                    is_cs = is_cs or current_user.is_cs_member
                    is_admin = is_admin or current_user.is_admin

            if is_cs or is_admin:
                is_approved = True

        data["current_user"] = current_user
        data["is_approved"] = is_approved
        data["is_registered"] = bool(current_user and current_user.phone)
        data["is_cs"] = is_cs
        data["is_admin"] = is_admin

        return await handler(event, data)

