"""Gestionnaire multi-fournisseurs de modèles de langage (LLMManager) et RAG documentaire."""

import json
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger
from pypdf import PdfReader
from config.settings import settings
from services.llm.base import BaseLLMService
from services.llm.gemini_provider import GeminiProvider
from services.llm.mistral_provider import MistralProvider


class LLMManager:
    def __init__(self, docs_dir: Optional[Path] = None):
        self.docs_dir = docs_dir or Path(__file__).resolve().parent.parent.parent / "data" / "documents"
        self.docs_dir.mkdir(parents=True, exist_ok=True)

        self.gemini = GeminiProvider()
        self.mistral = MistralProvider()
        self._cached_docs_text: Optional[str] = None

    def get_provider(self, task_type: str = "general") -> BaseLLMService:
        """Sélectionne le fournisseur le plus adapté selon la tâche et la configuration."""
        if task_type in ("long_doc", "rag_pdf"):
            return self.gemini
        elif task_type in ("finance", "french_legal"):
            return self.mistral if self.mistral.api_key else self.gemini

        # Repli sur le choix par défaut configuré
        if settings.DEFAULT_LLM_PROVIDER.lower() == "mistral" and self.mistral.api_key:
            return self.mistral
        return self.gemini

    def load_condo_documents(self, force_reload: bool = False) -> str:
        """Charge et extrait le texte de tous les documents présents dans data/documents/."""
        if self._cached_docs_text and not force_reload:
            return self._cached_docs_text

        text_parts: List[str] = []
        if not self.docs_dir.exists():
            return ""

        for file_path in self.docs_dir.glob("*"):
            if file_path.suffix.lower() == ".pdf":
                try:
                    reader = PdfReader(file_path)
                    content = "".join([page.extract_text() or "" for page in reader.pages])
                    text_parts.append(f"--- DOCUMENT: {file_path.name} ---\n{content}\n")
                except Exception as e:
                    logger.warning(f"Erreur lecture PDF {file_path.name} : {e}")
            elif file_path.suffix.lower() in (".txt", ".md"):
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    text_parts.append(f"--- DOCUMENT: {file_path.name} ---\n{content}\n")
                except Exception as e:
                    logger.warning(f"Erreur lecture fichier texte {file_path.name} : {e}")

        self._cached_docs_text = "\n".join(text_parts)
        return self._cached_docs_text

    async def answer_condo_question(self, question: str) -> str:
        """Répond à une question d'un résident sur la vie de l'immeuble ou le règlement de copropriété."""
        docs_context = self.load_condo_documents()
        provider = self.get_provider("rag_pdf" if len(docs_context) > 2000 else "general")

        system_prompt = (
            "Tu es Georges Bot, l'assistant virtuel bienveillant et rigoureux de la copropriété. "
            "Ton rôle est d'aider les copropriétaires et résidents en répondant précisément à leurs questions "
            "sur le règlement de copropriété, les horaires autorisés, le tri des déchets, les parties communes, etc.\n"
            "Règles strictes :\n"
            "1. Base-toi en priorité sur les documents de la copropriété fournis en contexte ci-dessous.\n"
            "2. Si l'information ne s'y trouve pas ou s'il s'agit d'une décision dépendant de l'AG ou du syndic, "
            "dis-le clairement et invite poliment à contacter le Conseil Syndical.\n"
            "3. Reste toujours courtois, concis et constructif.\n\n"
            f"DOCUMENTS DE LA COPROPRIÉTÉ :\n{docs_context}"
        )

        return await provider.generate_response(prompt=question, system_prompt=system_prompt)

    async def prefilter_resident_request(self, message: str, known_open_tickets: str = "") -> Dict:
        """Analyse le message d'un résident pour déterminer s'il s'agit d'une simple question ou d'une panne nécessitant ticket."""
        provider = self.get_provider("general")

        docs_context = self.load_condo_documents()

        system_prompt = (
            "Tu es le système de triage intelligent de la copropriété. "
            "Un résident t'envoie un message. Tu dois déterminer s'il s'agit :\n"
            "- D'une simple question d'information (ex: code porte, horaires de bruit, encombrants, badge) : dans ce cas, fournis la réponse si elle est connue.\n"
            "- D'une panne ou d'un incident matériel déjà connu (ex: ascenseur déjà signalé en panne) : informe le résident sans ouvrir de doublon.\n"
            "- D'un incident matériel ou d'une panne NOUVELLE nécessitant l'intervention du Conseil Syndical / Syndic (ex: fuite d'eau, porte de garage coincée, ampoule grillée).\n\n"
            "Tu dois impérativement répondre avec un JSON valide au format suivant :\n"
            "{\n"
            '  "is_breakdown": true/false,\n'
            '  "category": "Ascenseur" | "Plomberie" | "Electricite" | "Parking" | "Acces" | "EspacesVerts" | "Autre",\n'
            '  "immediate_answer": "Texte explicatif à envoyer au résident",\n'
            '  "should_open_ticket": true/false\n'
            "}\n"
            f"INCIDENTS DÉJÀ EN COURS DANS L'IMMEUBLE :\n{known_open_tickets}\n\n"
            f"EXTRAIT DES RÈGLES DE LA COPRO :\n{docs_context[:3000]}"
        )

        response_text = await provider.generate_response(prompt=message, system_prompt=system_prompt)

        # Nettoyage et parsing JSON
        try:
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned.strip())
        except Exception:
            return {
                "is_breakdown": True,
                "category": "Autre",
                "immediate_answer": "",
                "should_open_ticket": True,
            }


# Instance partagée
llm_manager = LLMManager()

