"""Fournisseur d'IA Mistral AI (en synergie avec CPTCOPRO)."""

from typing import Optional
from loguru import logger
from config.settings import settings
from services.llm.base import BaseLLMService


class MistralProvider(BaseLLMService):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.MISTRAL_API_KEY
        self.model = model or settings.MISTRAL_MODEL
        self._client = None
        if self.api_key:
            try:
                from mistralai import Mistral
                self._client = Mistral(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Impossible d'initialiser le client Mistral : {e}")

    async def is_available(self) -> bool:
        return bool(self._client and self.api_key)

    async def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
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

