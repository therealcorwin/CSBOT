"""Claviers pour les finances et la comptabilité CPTCOPRO."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_finance_resident_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💶 Mon solde de charges", callback_data="fin:my_balance"),
                InlineKeyboardButton(text="📅 Dates des appels de fonds", callback_data="fin:dates")
            ]
        ]
    )


def get_finance_cs_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Balance des impayés", callback_data="fin_cs:unpaid"),
                InlineKeyboardButton(text="💰 Synthèse de trésorerie", callback_data="fin_cs:treasury")
            ],
            [
                InlineKeyboardButton(text="📈 Détection anomalies CPTCOPRO", callback_data="fin_cs:anomalies")
            ]
        ]
    )

