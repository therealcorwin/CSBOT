"""Tests unitaires pour EmergencyService et LLMManager."""

from services.emergency_service import EmergencyService
from services.llm.manager import LLMManager


def test_emergency_overview():
    overview = EmergencyService.get_emergency_overview()
    assert "NUMÉROS D'URGENCE" in overview
    assert "Ascensoriste" in overview
    assert "COUPURES GÉNÉRALES" in overview


def test_llm_manager_document_loading(tmp_path):
    # Création d'un dossier temporaire avec un document texte
    doc_file = tmp_path / "reglement_test.txt"
    doc_file.write_text("Les travaux sont interdits le dimanche après 12h.", encoding="utf-8")

    manager = LLMManager(docs_dir=tmp_path)
    loaded_text = manager.load_condo_documents()
    assert "reglement_test.txt" in loaded_text
    assert "interdits le dimanche" in loaded_text

