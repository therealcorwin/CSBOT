"""Tests unitaires pour la logique et les validations du parcours d'onboarding."""

import pytest

from keyboards.onboarding_kb import get_floor_kb
from routers.onboarding import EMAIL_REGEX


def test_floor_kb_options():
    """Vérifie que le clavier d'étages contient bien RDJ jusqu'au 4ème étage."""
    kb = get_floor_kb()
    all_buttons = [btn for row in kb.inline_keyboard for btn in row]
    callbacks = [btn.callback_data for btn in all_buttons]

    expected_callbacks = [
        "floor:0:Rez-de-jardin (RDJ)",
        "floor:1:1er étage",
        "floor:2:2ème étage",
        "floor:3:3ème étage",
        "floor:4:4ème étage",
    ]
    assert callbacks == expected_callbacks
    assert len(all_buttons) == 5


@pytest.mark.parametrize(
    "raw_input,is_valid,expected_val",
    [
        ("3", True, 3),
        ("64", True, 64),
        ("32", True, 32),
        ("  45  ", True, 45),
        ("1", False, None),
        ("2", False, None),
        ("0", False, None),
        ("65", False, None),
        ("-5", False, None),
        ("100", False, None),
        ("abc", False, None),
        ("B12", False, None),
        ("", False, None),
    ],
)
def test_apartment_number_validation(raw_input, is_valid, expected_val):
    """Vérifie la validation du numéro d'appartement (3 à 64)."""
    text = raw_input.strip()
    valid = text.isdigit() and (3 <= int(text) <= 64)
    assert valid == is_valid
    if is_valid:
        assert int(text) == expected_val


@pytest.mark.parametrize(
    "raw_email,expected_clean,is_valid",
    [
        ("test@domain.com", "test@domain.com", True),
        ("  jean.dupont@test.fr  ", "jean.dupont@test.fr", True),
        ("marie . dupont @ hotmail . fr", "marie.dupont@hotmail.fr", True),
        ("user+tag@domain.co.uk", "user+tag@domain.co.uk", True),
        ("invalid-email", "invalid-email", False),
        ("test@domain", "test@domain", False),
        ("@domain.com", "@domain.com", False),
        ("user@.com", "user@.com", False),
        ("", "", False),
    ],
)
def test_email_cleaning_and_validation(raw_email, expected_clean, is_valid):
    """Vérifie le nettoyage des espaces et la validation de l'adresse email."""
    cleaned = raw_email.replace(" ", "").strip().lower()
    assert cleaned == expected_clean
    valid = bool(EMAIL_REGEX.match(cleaned))
    assert valid == is_valid
