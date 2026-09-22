"""Claviers pour l'espace d'entraide entre résidents (dons et prêts de matériel)."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_solidarity_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎁 Proposer un don", callback_data="sol:new_donation"),
                InlineKeyboardButton(text="🔧 Proposer un prêt d'outil", callback_data="sol:new_loan"),
            ],
            [
                InlineKeyboardButton(text="📋 Voir les annonces disponibles", callback_data="sol:list"),
            ],
        ]
    )

