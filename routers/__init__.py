"""Package des routeurs aiogram pour CSBOT."""
from aiogram import Router

from .admin import admin_router
from .ag_router import ag_router
from .assistant import assistant_router
from .common import common_router
from .cs_announcements import announcements_router
from .cs_tools import cs_tools_router
from .emergency import emergency_router
from .finances import finances_router
from .incidents import incidents_router
from .join_requests import join_requests_router
from .onboarding import onboarding_router
from .polls import polls_router
from .solidarity import solidarity_router


def setup_routers() -> Router:
    """Enregistre tous les routeurs de l'application dans un routeur racine."""
    root_router = Router()
    root_router.include_router(admin_router)
    root_router.include_router(common_router)
    root_router.include_router(onboarding_router)
    root_router.include_router(incidents_router)
    root_router.include_router(assistant_router)
    root_router.include_router(emergency_router)
    root_router.include_router(announcements_router)
    root_router.include_router(cs_tools_router)
    root_router.include_router(finances_router)
    root_router.include_router(polls_router)
    root_router.include_router(ag_router)
    root_router.include_router(solidarity_router)
    root_router.include_router(join_requests_router)
    return root_router


__all__ = ["setup_routers"]

