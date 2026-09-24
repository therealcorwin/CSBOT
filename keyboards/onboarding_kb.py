"""Claviers pour le parcours d'inscription des résidents."""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def get_status_kb() -> InlineKeyboardMarkup:
    """Choix du statut de l'occupant."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏠 Copropriétaire occupant", callback_data="status:OWNER_OCCUPANT")
            ],
            [
                InlineKeyboardButton(text="🔑 Locataire", callback_data="status:TENANT")
            ],
            [
                InlineKeyboardButton(text="📑 Copropriétaire bailleur (non occupant)", callback_data="status:OWNER_NON_RESIDENT")
            ]
        ]
    )


def get_floor_kb() -> InlineKeyboardMarkup:
    """Choix de l'étage pour le résident (RDJ => 4ème)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🌿 Rez-de-jardin (RDJ)", callback_data="floor:0:Rez-de-jardin (RDJ)")
            ],
            [
                InlineKeyboardButton(text="1️⃣ 1er étage", callback_data="floor:1:1er étage"),
                InlineKeyboardButton(text="2️⃣ 2ème étage", callback_data="floor:2:2ème étage"),
            ],
            [
                InlineKeyboardButton(text="3️⃣ 3ème étage", callback_data="floor:3:3ème étage"),
                InlineKeyboardButton(text="4️⃣ 4ème étage", callback_data="floor:4:4ème étage"),
            ],
        ]
    )


def get_phone_kb() -> ReplyKeyboardMarkup:
    """Demande du numéro de téléphone avec bouton officiel Telegram."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Partager mon numéro de téléphone", request_contact=True)],
            [KeyboardButton(text="✍️ Saisie manuelle")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_confirmation_kb() -> InlineKeyboardMarkup:
    """Confirmation finale de la fiche avant envoi au Conseil Syndical."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Confirmer et transmettre au CS", callback_data="onboarding:confirm")
            ],
            [
                InlineKeyboardButton(text="🔄 Recommencer la saisie", callback_data="onboarding:restart")
            ]
        ]
    )

