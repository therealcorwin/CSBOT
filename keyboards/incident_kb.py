"""Claviers pour le signalement et la gestion des incidents."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_categories_kb() -> InlineKeyboardMarkup:
    """Catégories d'incidents / pannes."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛗 Ascenseur", callback_data="inc_cat:Ascenseur"),
                InlineKeyboardButton(text="💧 Plomberie / Fuite", callback_data="inc_cat:Plomberie")
            ],
            [
                InlineKeyboardButton(text="⚡ Électricité / Éclairage", callback_data="inc_cat:Electricite"),
                InlineKeyboardButton(text="🚗 Parking / Porte de garage", callback_data="inc_cat:Parking")
            ],
            [
                InlineKeyboardButton(text="🚪 Portes / Digicode / Vigik", callback_data="inc_cat:Acces"),
                InlineKeyboardButton(text="🌿 Espaces verts / Extérieur", callback_data="inc_cat:EspacesVerts")
            ],
            [
                InlineKeyboardButton(text="❓ Autre incident", callback_data="inc_cat:Autre"),
                InlineKeyboardButton(text="❌ Annuler", callback_data="inc_cat:cancel")
            ]
        ]
    )


def get_photo_skip_kb() -> InlineKeyboardMarkup:
    """Passer l'envoi de photo lors du signalement."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭️ Passer sans photo", callback_data="inc_photo:skip")],
            [InlineKeyboardButton(text="❌ Annuler le signalement", callback_data="inc_photo:cancel")]
        ]
    )


def get_ticket_cs_actions_kb(ticket_id: int) -> InlineKeyboardMarkup:
    """Actions d'un membre du CS sur une fiche de ticket."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📞 Transmis Syndic", callback_data=f"ticket_status:{ticket_id}:SENT_TO_SYNDIC"),
                InlineKeyboardButton(text="🔧 En cours", callback_data=f"ticket_status:{ticket_id}:IN_PROGRESS")
            ],
            [
                InlineKeyboardButton(text="✅ Marquer Résolu", callback_data=f"ticket_status:{ticket_id}:RESOLVED"),
                InlineKeyboardButton(text="❌ Annuler ticket", callback_data=f"ticket_status:{ticket_id}:CANCELLED")
            ]
        ]
    )

