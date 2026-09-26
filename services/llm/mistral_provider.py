"""Fournisseur d'IA Mistral AI (en synergie avec CPTCOPRO)."""

from loguru import logger

from config.settings import settings
from services.llm.base import BaseLLMService


def _patch_mistral_finalize() -> None:
    """Corrige le bug atexit du SDK mistralai sous Python 3.12+ / 3.14.

    Lorsque le bot est arrêté par Ctrl+C, asyncio.run() dans weakref.finalize
    lève un KeyboardInterrupt que close_clients n'intercepte pas par défaut.
    """
    try:
        import mistralai.httpclient as h
        import mistralai.sdk as s

        orig_close = h.close_clients
        if not getattr(orig_close, "_is_safe_patched", False):
            def safe_close_clients(*args, **kwargs):
                try:
                    return orig_close(*args, **kwargs)
                except BaseException:
                    pass

            safe_close_clients._is_safe_patched = True
            h.close_clients = safe_close_clients
            s.close_clients = safe_close_clients
    except Exception:
        pass


class MistralProvider(BaseLLMService):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.MISTRAL_API_KEY
        self.model = model or settings.MISTRAL_MODEL
        self._client = None

        if self._is_valid_key(self.api_key):
            try:
                _patch_mistral_finalize()
                from mistralai import Mistral
                self._client = Mistral(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Impossible d'initialiser le client Mistral : {e}")

    @staticmethod
    def _is_valid_key(key: str | None) -> bool:
        if not key:
            return False
        cleaned = key.strip()
        if not cleaned or cleaned.startswith("votre_cle"):
            return False
        return True

    async def is_available(self) -> bool:
        return bool(self._client and self._is_valid_key(self.api_key))

    async def aclose(self) -> None:
        """Ferme proprement les sessions HTTP du client Mistral."""
        if self._client:
            try:
                sdk_cfg = getattr(self._client, "sdk_configuration", None)
                if sdk_cfg and sdk_cfg.async_client:
                    await sdk_cfg.async_client.aclose()
                    sdk_cfg.async_client = None
            except Exception:
                pass
            try:
                sdk_cfg = getattr(self._client, "sdk_configuration", None)
                if sdk_cfg and sdk_cfg.client:
                    sdk_cfg.client.close()
                    sdk_cfg.client = None
            except Exception:
                pass
            self._client = None

    async def generate_response(self, prompt: str, system_prompt: str | None = None) -> str:
        if not await self.is_available():
            return "Le service d'intelligence artificielle Mistral AI n'est pas configuré (clé API manquante)."

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await self._client.chat.complete_async(
                model=self.model,
                messages=messages,
            )
            return response.choices[0].message.content or "Aucune réponse générée."
        except Exception as e:
            logger.error(f"Erreur lors de l'appel à Mistral AI : {e}")
            return f"Désolé, une erreur est survenue lors de l'analyse avec Mistral : {str(e)}"

