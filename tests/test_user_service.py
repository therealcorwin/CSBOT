"""Tests unitaires du service utilisateur et de la gestion des résidents."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.user_service import UserService


@pytest.mark.asyncio
async def test_onboarding_and_approval(test_db: AsyncSession):
    user_id = 123456789
    data = {
        "first_name": "Jean",
        "last_name": "Dupont",
        "phone": "+33612345678",
        "email": "jean.dupont@test.fr",
        "status": "OWNER_OCCUPANT",
        "apartment_number": "204",
        "floor": 2,
        "building": "B",
    }

    # 1. Soumission d'onboarding
    user, apt = await UserService.submit_onboarding(test_db, user_id=user_id, data=data)
    assert user.id == user_id
    assert user.first_name == "Jean"
    assert user.last_name == "Dupont"
    assert user.is_approved is False
    assert apt.number == "204"
    assert apt.building == "B"

    # Vérification occupant actif
    active_apt = await UserService.get_active_apartment_for_user(test_db, user_id)
    assert active_apt is not None
    assert active_apt.number == "204"

    # 2. Validation par le CS
    approved_user = await UserService.approve_user(test_db, user_id)
    assert approved_user is not None
    assert approved_user.is_approved is True

    # 3. Recherche par appartement
    occupants = await UserService.get_occupants_by_apartment(test_db, "204")
    assert len(occupants) == 1
    assert occupants[0][0].id == user_id

    # 4. Recherche par nom
    search_res = await UserService.search_residents_by_query(test_db, "Dupont")
    assert len(search_res) >= 1
    assert search_res[0][0].id == user_id

    # 5. Déménagement
    move_res = await UserService.move_out_user(test_db, user_id)
    assert move_res is True

    # Après déménagement, plus d'appartement actif
    active_apt_after = await UserService.get_active_apartment_for_user(test_db, user_id)
    assert active_apt_after is None

