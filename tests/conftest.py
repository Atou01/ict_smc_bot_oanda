import pytest, json, types, sys, os
from pathlib import Path

# Ajout du chemin pour l'importation depuis le projet
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))    

@pytest.fixture
def sample_payload():
    # 3 paires min pour satisfaire le prompt
    return {
        "market_data": {"EURUSD": {}, "GBPUSD": {}, "USDJPY": {}},
        "ict_signals": {},
        "macro_events": [],
        "history": {},
    }

@pytest.fixture
def tmp_csv(tmp_path, monkeypatch):
    """Force le CSV à aller dans un dossier temporaire pour les tests."""
    from src.bot.llm_engine import _log_decision_to_csv, os
    monkeypatch.setattr(os, "path", types.SimpleNamespace(
        dirname=lambda p: tmp_path,
        join=lambda *a: tmp_path / "llm_decisions.csv",
        isfile=lambda p: Path(p).exists()
    ))
    return tmp_path / "llm_decisions.csv"
