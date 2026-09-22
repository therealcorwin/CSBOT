"""Service de gestion des tickets de signalement d'incidents et synchronisation externe."""

from datetime import datetime, timedelta
import random
from typing import List, Optional
import httpx
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from config.settings import settings
from database.models import Apartment, Ticket, User


class TicketService:
    @staticmethod
    async def generate_ticket_code(session: AsyncSession) -> str:
        """Génère un code de ticket incrémental et lisible (ex: INC-1042)."""
        stmt = select(func.count(Ticket.id))
        res = await session.execute(stmt)
        count = res.scalar() or 0
        rand_suffix = random.randint(10, 99)
        return f"INC-{count + 1000}{rand_suffix}"

    @staticmethod
    async def create_ticket(
        session: AsyncSession,
        user_id: int,
        apartment_id: Optional[int],
        category: str,
        description: str,
        photo_file_id: Optional[str] = None,
    ) -> Ticket:
        """Crée un nouveau ticket et enclenche la synchronisation externe optionnelle."""
        ticket_code = await TicketService.generate_ticket_code(session)

        ticket = Ticket(
            ticket_code=ticket_code,
            user_id=user_id,
            apartment_id=apartment_id,
            category=category,
            description=description,
            photo_file_id=photo_file_id,
            status="OPEN",
        )
        session.add(ticket)
        await session.flush()

        logger.info(f"Ticket créé : {ticket.ticket_code} (Catégorie: {category})")

        # Notification externe asynchrone (n8n / Trello / Jira)
        if settings.N8N_WEBHOOK_URL:
            await TicketService._sync_external_webhook(ticket)

        return ticket

    @staticmethod
    async def update_status(
        session: AsyncSession,
        ticket_id: int,
        new_status: str,
        handled_by_cs_id: Optional[int] = None,
    ) -> Optional[Ticket]:
        """Met à jour le statut du ticket et horodate les étapes."""
        stmt = (
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .options(selectinload(Ticket.user), selectinload(Ticket.apartment))
        )
        res = await session.execute(stmt)
        ticket = res.scalar_one_or_none()

        if ticket:
            ticket.status = new_status
            ticket.handled_by_cs_id = handled_by_cs_id
            if new_status == "SENT_TO_SYNDIC" and not ticket.sent_to_syndic_at:
                ticket.sent_to_syndic_at = datetime.now()

            await session.flush()
            logger.info(f"Ticket {ticket.ticket_code} passé au statut {new_status}")

            if settings.N8N_WEBHOOK_URL:
                await TicketService._sync_external_webhook(ticket)

        return ticket

    @staticmethod
    async def get_active_tickets(session: AsyncSession) -> List[Ticket]:
        """Récupère les tickets non encore résolus ou annulés."""
        stmt = (
            select(Ticket)
            .where(Ticket.status.in_(["OPEN", "SENT_TO_SYNDIC", "IN_PROGRESS"]))
            .options(selectinload(Ticket.user), selectinload(Ticket.apartment))
            .order_by(Ticket.created_at.desc())
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_tickets_requiring_reminder(session: AsyncSession, days_threshold: int = 7) -> List[Ticket]:
        """Récupère les tickets transmis au syndic depuis plus de X jours sans mise à jour."""
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        stmt = (
            select(Ticket)
            .where(
                Ticket.status == "SENT_TO_SYNDIC",
                Ticket.sent_to_syndic_at <= cutoff_date,
            )
            .options(selectinload(Ticket.user), selectinload(Ticket.apartment))
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_summary_for_llm(session: AsyncSession) -> str:
        """Génère un résumé textuel des pannes actuelles pour orienter l'IA lors du pré-filtrage."""
        active = await TicketService.get_active_tickets(session)
        if not active:
            return "Aucune panne majeure actuellement signalée dans l'immeuble."

        lines = []
        for t in active:
            lines.append(f"- [{t.ticket_code}] {t.category} : {t.description[:100]} (Statut : {t.status})")
        return "\n".join(lines)

    @staticmethod
    async def _sync_external_webhook(ticket: Ticket) -> None:
        """Envoie l'état du ticket vers n8n qui peut propager vers Jira / Trello."""
        try:
            payload = {
                "event": "ticket_updated",
                "ticket_code": ticket.ticket_code,
                "category": ticket.category,
                "description": ticket.description,
                "status": ticket.status,
                "user_id": ticket.user_id,
                "apartment_id": ticket.apartment_id,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(settings.N8N_WEBHOOK_URL, json=payload)
        except Exception as e:
            logger.warning(f"Échec envoi webhook ticket vers n8n : {e}")

