"""Package des claviers et interfaces graphiques Telegram de CSBOT."""
from .ag_kb import get_ag_menu_kb
from .cs_kb import (
    get_announcement_actions_kb,
    get_announcement_levels_kb,
    get_registration_validation_kb,
)
from .emergency_kb import get_emergency_kb
from .finance_kb import get_finance_cs_kb, get_finance_resident_kb
from .incident_kb import get_categories_kb, get_ticket_cs_actions_kb
from .menu_kb import get_cs_menu, get_main_menu, get_unregistered_menu
from .onboarding_kb import get_confirmation_kb, get_floor_kb, get_phone_kb, get_status_kb
from .solidarity_kb import get_solidarity_menu_kb

__all__ = [
    "get_main_menu",
    "get_cs_menu",
    "get_unregistered_menu",
    "get_status_kb",
    "get_floor_kb",
    "get_phone_kb",
    "get_confirmation_kb",
    "get_categories_kb",
    "get_ticket_cs_actions_kb",
    "get_emergency_kb",
    "get_registration_validation_kb",
    "get_announcement_levels_kb",
    "get_announcement_actions_kb",
    "get_finance_resident_kb",
    "get_finance_cs_kb",
    "get_ag_menu_kb",
    "get_solidarity_menu_kb",
]

