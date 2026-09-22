"""Interface abstraite pour les fournisseurs de modèles de langage (LLM)."""

from abc import ABC, abstractmethod
from typing import Optional


class BaseLLMService(ABC):
    @abstractmethod
    async def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Génère une réponse textuelle à partir d'un prompt."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Vérifie si le fournisseur est correctement configuré et accessible."""
        pass

