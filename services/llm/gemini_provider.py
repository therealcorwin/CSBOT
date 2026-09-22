"""Fournisseur d'IA Google Gemini (gemini-2.5-flash via google-genai SDK)."""

from typing import Optional
from loguru import logger
from config.settings import settings
from services.llm.base import BaseLLMService


class GeminiProvider(BaseLLMService):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self._client = None
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Impossible d'initialiser le client Gemini : {e}")

    async def is_available(self) -> bool:
        return bool(self._client and self.api_key)

    async def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
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

