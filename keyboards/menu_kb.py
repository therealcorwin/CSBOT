"""Claviers de navigation principaux (ReplyKeyboardMarkup)."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_unregistered_menu() -> ReplyKeyboardMarkup:
    """Menu affiché pour un utilisateur non encore validé."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Demander l'accès à la copropriété")],
            [KeyboardButton(text="ℹ️ À propos du bot"), KeyboardButton(text="🚨 Urgences Résidence")]
        ],
        resize_keyboard=True,
        is_persistent=True
    )


def get_main_menu(is_cs: bool = False) -> ReplyKeyboardMarkup:
    """Menu principal persistant pour un résident validé."""
    keyboard = [
        [
            KeyboardButton(text="🚨 Urgence Résidence 24/7"),
            KeyboardButton(text="🔧 Signaler une panne")
        ],
        [
            KeyboardButton(text="💬 Poser une question (IA)"),
            KeyboardButton(text="ℹ️ Contacts & Infos Copro")
        ],
        [
            KeyboardButton(text="💶 Mes Charges & Compte"),
            KeyboardButton(text="📦 Voisins Solidaires")
        ],
        [
            KeyboardButton(text="💡 Boîte à idées AG"),
            KeyboardButton(text="🚪 Déclarer un déménagement")
        ]
    ]

    if is_cs:
        keyboard.append([KeyboardButton(text="👑 Espace Conseil Syndical")])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, is_persistent=True)


def get_cs_menu() -> ReplyKeyboardMarkup:
    """Menu dédié aux membres du Conseil Syndical."""
    keyboard = [
        [
            KeyboardButton(text="📢 Diffuser une annonce"),
            KeyboardButton(text="📋 Tableau des incidents")
        ],
        [
            KeyboardButton(text="🔍 Rechercher un lot"),
            KeyboardButton(text="📊 Finances Copro (CPTCOPRO)")
        ],
        [
            KeyboardButton(text="🗳️ Créer un sondage"),
            KeyboardButton(text="⚙️ Inscriptions en attente")
        ],
        [
            KeyboardButton(text="🛠️ Carnet prestataires"),
            KeyboardButton(text="🏠 Retour Menu Résident")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, is_persistent=True)

