import threading, json, sys, os

# Ajout du chemin pour l'importation depuis src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.bot import llm_engine as le

def _write(decision, path):
    le._log_decision_to_csv(decision, outcome="pending")

def test_concurrent_lock(tmp_path, monkeypatch):
    monkeypatch.setattr(le, "os", __import__("os"))  # path normal
    
    # Patch le chemin du CSV pour utiliser le répertoire temporaire
    original_join = os.path.join
    def patched_join(*args):
        if args and args[0] == "logs" and args[1] == "llm_decisions.csv":
            return tmp_path / "llm.csv"
        return original_join(*args)
    
    monkeypatch.setattr(os.path, "join", patched_join)
    monkeypatch.setattr(os.path, "isfile", lambda p: os.path.exists(p))
    
    # S'assurer que le répertoire existe
    os.makedirs(tmp_path, exist_ok=True)

    decision = {"symbol":"EURUSD","direction":"LONG","strategy":"ICT_OB",
                "entry":1,"sl":0.9,"tp":1.1,"confidence":0.8,"reasoning":"x"}
    th1 = threading.Thread(target=_write, args=(decision, tmp_path))
    th2 = threading.Thread(target=_write, args=(decision, tmp_path))
    th1.start(); th2.start(); th1.join(); th2.join()

    # Vérifier que les deux entrées sont écrites
    with open(tmp_path / "llm.csv", "r") as f:
        content = f.read()
        assert content.count("EURUSD") == 2
