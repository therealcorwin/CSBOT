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

    # 2. Validation par le CS avec enregistrement du validateur
    approved_user = await UserService.approve_user(
        test_db,
        user_id,
        approved_by="Alice Martin (@alice)",
        approved_by_id=987654,
    )
    assert approved_user is not None
    assert approved_user.is_approved is True
    assert approved_user.approved_by == "Alice Martin (@alice)"
    assert approved_user.approved_by_id == 987654
    assert approved_user.approved_at is not None

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


@pytest.mark.asyncio
async def test_cs_promotion_and_demotion(test_db: AsyncSession):
    user_id = 999888
    user = await UserService.get_or_create_user(
        test_db,
        user_id=user_id,
        username="claire_cs",
        first_name="Claire",
        last_name="Bernard",
    )
    assert user.is_cs_member is False

    # 1. Recherche par username (@ et sans @)
    found_user = await UserService.get_user_by_username(test_db, "@claire_cs")
    assert found_user is not None
    assert found_user.id == user_id

    found_nocap = await UserService.get_user_by_username(test_db, "CLAIRE_CS")
    assert found_nocap is not None
    assert found_nocap.id == user_id

    # 2. Promotion en tant que membre CS
    promoted = await UserService.promote_to_cs(test_db, user_id)
    assert promoted is not None
    assert promoted.is_cs_member is True
    assert promoted.is_approved is True

    # 3. Liste des membres CS
    cs_members = await UserService.get_cs_members(test_db)
    assert any(m.id == user_id for m in cs_members)

    # 4. Rétrogradation en simple copropriétaire
    demoted = await UserService.demote_from_cs(test_db, user_id)
    assert demoted is not None
    assert demoted.is_cs_member is False

    # Vérification après rétrogradation
    cs_members_after = await UserService.get_cs_members(test_db)
    assert not any(m.id == user_id for m in cs_members_after)


