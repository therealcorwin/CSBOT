"""Tests unitaires du service de sondages avec contrôle 1 vote par appartement."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Apartment, Occupant, User
from services.poll_service import PollService


@pytest.mark.asyncio
async def test_poll_one_vote_per_apartment(test_db: AsyncSession):
    # Appartement A12
    apt = Apartment(number="A12", floor=1, building="A")
    test_db.add(apt)
    await test_db.flush()

    # Deux co-occupants (conjoints) pour l'appartement A12
    user1 = User(id=101, first_name="Marc", last_name="Dubois", is_approved=True)
    user2 = User(id=102, first_name="Sophie", last_name="Dubois", is_approved=True)
    test_db.add_all([user1, user2])
    await test_db.flush()

    occ1 = Occupant(apartment_id=apt.id, user_id=user1.id, is_active=True)
    occ2 = Occupant(apartment_id=apt.id, user_id=user2.id, is_active=True)
    test_db.add_all([occ1, occ2])
    await test_db.flush()

    # 1. Création d'un sondage
    poll = await PollService.create_poll(
        session=test_db,
        title="Ravalement de façade : quelle couleur privilégier ?",
        options=["Blanc cassé", "Beige pierre", "Gris perle"],
        created_by_user_id=999
    )
    assert poll.id is not None
    assert len(poll.options["choices"]) == 3

    # 2. Premier vote par Marc (Option 1 : Beige pierre)
    success1, msg1 = await PollService.cast_vote(
        session=test_db,
        poll_id=poll.id,
        user_id=user1.id,
        option_index=1
    )
    assert success1 is True
    assert "succès" in msg1.lower()

    # 3. Deuxième vote par Sophie pour le même appartement (Option 0 : Blanc cassé) -> DOIT ÊTRE REFUSÉ
    success2, msg2 = await PollService.cast_vote(
        session=test_db,
        poll_id=poll.id,
        user_id=user2.id,
        option_index=0
    )
    assert success2 is False
    assert "déjà été enregistré" in msg2.lower()

    # 4. Vérification des résultats
    results = await PollService.get_results(test_db, poll.id)
    assert results["total_votes"] == 1
    assert results["counts"][1] == 1
    assert results["counts"][0] == 0
    assert "A12" in results["voted_lots"]

