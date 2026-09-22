"""Claviers spécifiques aux fonctionnalités du Conseil Syndical."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_registration_validation_kb(user_id: int) -> InlineKeyboardMarkup:
    """Boutons de validation d'un nouveau résident par le CS."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Valider l'accès", callback_data=f"val_user:{user_id}:approve"),
                InlineKeyboardButton(text="❌ Refuser", callback_data=f"val_user:{user_id}:reject")
            ]
        ]
    )


def get_announcement_levels_kb() -> InlineKeyboardMarkup:
    """Niveau d'importance d'une annonce."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="ℹ️ Information courante", callback_data="ann_level:INFO"),
            ],
            [
                InlineKeyboardButton(text="⚠️ Important (coupure d'eau, travaux)", callback_data="ann_level:IMPORTANT"),
            ],
            [
                InlineKeyboardButton(text="🚨 Urgent (sécurité, panne bloquante)", callback_data="ann_level:URGENT"),
            ],
            [
                InlineKeyboardButton(text="❌ Annuler", callback_data="ann_level:cancel"),
            ]
        ]
    )


def get_announcement_actions_kb() -> InlineKeyboardMarkup:
    """Options de publication de l'annonce."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Publier dans le chat copro", callback_data="ann_action:publish"),
                InlineKeyboardButton(text="📌 Publier & Épingler", callback_data="ann_action:publish_pin"),
            ],
            [
                InlineKeyboardButton(text="❌ Abandonner", callback_data="ann_action:cancel"),
            ]
        ]
    )

