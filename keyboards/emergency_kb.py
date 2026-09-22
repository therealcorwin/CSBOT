"""Claviers d'urgence 24/7 et numéros d'astreinte."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config.settings import settings


def get_emergency_kb() -> InlineKeyboardMarkup:
    """Boutons d'urgence et accès rapide aux astreintes."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"🛗 Ascenseur : {settings.EMERGENCY_ASCENSEUR_PHONE}", callback_data="urg_info:ascenseur")
            ],
            [
                InlineKeyboardButton(text=f"🔥 Chauffage : {settings.EMERGENCY_CHAUFFAGE_PHONE}", callback_data="urg_info:chauffage")
            ],
            [
                InlineKeyboardButton(text=f"💧 Plomberie Urgence : {settings.EMERGENCY_PLOMBERIE_PHONE}", callback_data="urg_info:plomberie")
            ],
            [
                InlineKeyboardButton(text="🚰 Vannes d'arrêt & Coupures générales", callback_data="urg_info:valves")
            ],
            [
                InlineKeyboardButton(text="🚨 Alerter le Conseil Syndical", callback_data="urg_action:alert_cs")
            ]
        ]
    )

