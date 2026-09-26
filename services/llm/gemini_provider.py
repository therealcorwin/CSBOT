"""Fournisseur d'IA Google Gemini (gemini-2.5-flash via google-genai SDK)."""

from loguru import logger

from config.settings import settings
from services.llm.base import BaseLLMService


class GeminiProvider(BaseLLMService):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self._client = None

        if self._is_valid_key(self.api_key):
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Impossible d'initialiser le client Gemini : {e}")

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
        """Ferme proprement le client Gemini."""
        if self._client:
            try:
                if hasattr(self._client, "aio") and hasattr(self._client.aio, "aclose"):
                    await self._client.aio.aclose()
                elif hasattr(self._client, "close"):
                    self._client.close()
            except Exception:
                pass
            self._client = None

    async def generate_response(self, prompt: str, system_prompt: str | None = None) -> str:
        if not await self.is_available():
            return "Le service d'intelligence artificielle Gemini n'est pas configuré (clé API manquante)."

        try:
            from google.genai import types

            config = types.GenerateContentConfig()
            if system_prompt:
                config.system_instruction = system_prompt

            # Appel asynchrone via l'interface aio du SDK google-genai
            response = await self._client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            return response.text or "Aucune réponse générée."
        except Exception as e:
            logger.error(f"Erreur lors de l'appel à Gemini : {e}")
            return f"Désolé, une erreur est survenue lors de l'analyse : {str(e)}"

