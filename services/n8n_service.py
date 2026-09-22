"""Service de communication avec la plateforme d'automatisation n8n."""

from typing import Any, Dict, Optional
import httpx
from loguru import logger
from config.settings import settings


class N8nService:
    @staticmethod
    async def send_event(event_name: str, payload: Dict[str, Any]) -> bool:
        """Envoie un événement déclencheur vers un webhook n8n."""
        if not settings.N8N_WEBHOOK_URL:
            return False

        data = {
            "event": event_name,
            "secret": settings.N8N_WEBHOOK_SECRET,
            "payload": payload,
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.post(settings.N8N_WEBHOOK_URL, json=data)
                return response.is_success
        except Exception as e:
            logger.warning(f"Impossible de notifier n8n pour l'événement '{event_name}' : {e}")
            return False

    @staticmethod
    async def query_extended_knowledge(query: str, user_id: int) -> Optional[str]:
        """Interroge n8n pour chercher dans les e-mails du syndic, courriers ou drive cloud."""
        if not settings.N8N_WEBHOOK_URL:
            return None

        data = {
            "action": "search_knowledge",
            "query": query,
            "user_id": user_id,
            "secret": settings.N8N_WEBHOOK_SECRET,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(settings.N8N_WEBHOOK_URL, json=data)
                if response.is_success:
                    res_json = response.json()
                    return res_json.get("answer") or res_json.get("result")
        except Exception as e:
            logger.warning(f"Recherche documentaire n8n en échec : {e}")

        return None

