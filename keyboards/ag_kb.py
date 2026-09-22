"""Claviers pour l'AG, la bourse aux pouvoirs et la boîte à idées."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_ag_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💡 Proposer une idée de résolution", callback_data="ag:new_idea"),
                InlineKeyboardButton(text="📋 Voir les idées soumises", callback_data="ag:list_ideas")
            ],
            [
                InlineKeyboardButton(text="🤝 Bourse aux pouvoirs d'AG", callback_data="ag:power_proxy")
            ]
        ]
    )

