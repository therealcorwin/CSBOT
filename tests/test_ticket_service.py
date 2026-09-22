"""Tests unitaires du service de tickets et signalements d'incidents."""

from datetime import datetime, timedelta
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Apartment, User
from services.ticket_service import TicketService


@pytest.mark.asyncio
async def test_ticket_lifecycle(test_db: AsyncSession):
    # Création d'un appartement et utilisateur de test
    apt = Apartment(number="101", floor=1, building="A")
    user = User(id=987654321, first_name="Claire", last_name="Martin", is_approved=True)
    test_db.add_all([apt, user])
    await test_db.flush()

    # 1. Création d'un ticket
    ticket = await TicketService.create_ticket(
        session=test_db,
        user_id=user.id,
        apartment_id=apt.id,
        category="Plomberie",
        description="Fuite d'eau importante au plafond du hall.",
        photo_file_id="photo_test_123"
    )
    assert ticket.ticket_code.startswith("INC-")
    assert ticket.status == "OPEN"
    assert ticket.photo_file_id == "photo_test_123"

    # 2. Récupération des tickets actifs
    active = await TicketService.get_active_tickets(test_db)
    assert len(active) == 1
    assert active[0].ticket_code == ticket.ticket_code

    # 3. Transmission au syndic
    updated = await TicketService.update_status(
        session=test_db,
        ticket_id=ticket.id,
        new_status="SENT_TO_SYNDIC",
        handled_by_cs_id=111222333
    )
    assert updated is not None
    assert updated.status == "SENT_TO_SYNDIC"
    assert updated.sent_to_syndic_at is not None

    # 4. Clôture / Résolution
    resolved = await TicketService.update_status(
        session=test_db,
        ticket_id=ticket.id,
        new_status="RESOLVED"
    )
    assert resolved.status == "RESOLVED"

    # Le ticket résolu n'apparaît plus dans les tickets actifs
    active_after = await TicketService.get_active_tickets(test_db)
    assert len(active_after) == 0

