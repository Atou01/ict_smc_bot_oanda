"""
test_full_pipeline.py
Test bout-en-bout du pipeline complet du bot de trading sans exécution réelle.
Simule le flux : Contexte → LLM → StrategySelector → Signal → OrderManager → PnL → shared_state
"""

import os
import json
import yaml
import datetime
import time
from unittest.mock import MagicMock

from bot.llm_brain import LLMBrain
from bot.structure_detector import StructureDetector
from bot.strategy_selector import StrategySelector

from bot.order_manager import OrderManager
from bot.pnl_tracker import PnLTracker

# Chemins des fichiers
CONFIG_PATH = "config.yaml"
SHARED_STATE_PATH = "shared_state.json"
TEST_CONTEXT_PATH = "test_contexts/mock_context_1.json"

def load_config():
    """Charge la configuration."""
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)

def load_test_context():
    """Charge un contexte de test prédéfini."""
    with open(TEST_CONTEXT_PATH, 'r') as f:
        return json.load(f)

def update_shared_state(state_data):
    """Met à jour le fichier shared_state.json."""
    with open(SHARED_STATE_PATH, 'w') as f:
        json.dump(state_data, f, indent=2)
    print(f"[TEST] shared_state.json mis à jour: {datetime.datetime.now().strftime('%H:%M:%S')}")

def log_step(step_name, data=None):
    """Affiche un log formaté pour suivre les étapes du pipeline."""
    separator = "=" * 50
    print(f"\n{separator}")
    print(f"ÉTAPE: {step_name}")
    if data:
        print(f"DONNÉES: {data if len(str(data)) < 100 else str(data)[:100] + '...'}")
    print(separator)

def run_full_pipeline_test():
    """Exécute un test complet du pipeline."""
    log_step("INITIALISATION")
    
    # Chargement de la configuration
    cfg = load_config()
    context = load_test_context()
    
    try:
        ib = MagicMock()
        ib.positions = lambda: []
    except Exception:
        pass
    else:
        ib = MagicMock()
        ib.positions = lambda: []
    
    # Initialisation des composants
    llm = LLMBrain(api_key=cfg["OPENAI"]["api_key"])
    detector = StructureDetector()
    initial_capital = float(cfg.get('RISK', {}).get('capital', 10000))
    pnl_tracker = PnLTracker(ib, initial_capital)
    order_manager = OrderManager(ib, cfg, pnl_tracker)
    
    # ÉTAPE 1: Contexte Macro et Structures
    log_step("1. CONTEXTE ET STRUCTURES")
    
    macro_data = context["macro_data"]
    print(f"[TEST] Macro: {macro_data}")
    
    # Simulation de détection de structures
    structures_detected = context["structures_detected"]
    print(f"[TEST] Structures détectées: {structures_detected}")
    
    # Résumé PnL simulé
    pnl_summary = context["pnl_summary"]
    print(f"[TEST] PnL: {pnl_summary}")
    
    # ÉTAPE 2: Analyse LLM
    log_step("2. ANALYSE LLM")
    
    start_time = datetime.datetime.now()
    strategy = llm.analyze_context_and_choose_strategy(
        macro_data,
        structures_detected,
        pnl_summary
    )
    end_time = datetime.datetime.now()
    
    print(f"[TEST] Stratégie LLM ({(end_time - start_time).total_seconds():.2f}s):")
    print(strategy)
    
    # ÉTAPE 3: Sélection de stratégie et génération de signaux
    log_step("3. STRATÉGIE → SIGNAUX")
    
    selector = StrategySelector(llm)
    signals = selector.route_strategy(strategy)
    
    print(f"[TEST] Signaux générés: {len(signals)}")
    for i, sig in enumerate(signals):
        print(f"Signal {i+1}: {sig['type']} {sig['side']} sur {sig['timeframe']} - {sig.get('confidence', 'N/A')}")
    
    # ÉTAPE 4: Gestion d'ordre (simulation)
    log_step("4. SIGNAL → ORDRE (Simulation)")
    
    # Affichage du plan de trade
    order_manager.print_trade_plan(signals)
    
    # Simulation d'un trade réussi
    if signals:
        signal = signals[0]
        trade_result = 75 if signal['side'] == "LONG" else -40  # Simuler un gain ou une perte
        
        print(f"[TEST] Simulation d'un résultat de trade: {trade_result}€")
        pnl_tracker.add_realized_trade(trade_result, is_win=(trade_result > 0))
    
    # ÉTAPE 5: Mise à jour PnL
    log_step("5. MISE À JOUR PNL")
    
    pnl_tracker.update()
    pnl_data = pnl_tracker.export_summary()
    
    print(f"[TEST] PnL mis à jour:")
    print(f"- Réalisé: {pnl_data['realized']}€")
    print(f"- Latent: {pnl_data['unrealized']}€")
    print(f"- Drawdown: {pnl_data['drawdown_max']}%")
    print(f"- G/P: {pnl_data['winning_trades']}/{pnl_data['losing_trades']}")
    
    # ÉTAPE 6: Mise à jour shared_state.json
    log_step("6. MISE À JOUR SHARED_STATE.JSON")
    
    # Construction de l'état complet
    shared_state = {
        "mode": cfg.get('MODE', 'Simulation'),
        "timestamp": datetime.datetime.now().isoformat(),
        "macro_context": macro_data,
        "structures_detected": {
            "fvg": detector.detect_fvg(),
            "ob": detector.detect_ob(),
            "bos": detector.detect_bos(),
            "sweep": detector.detect_sweep()
        },
        "llm_strategy": strategy,
        "last_signal": signals[0] if signals else None,
        "pnl_summary": pnl_data
    }
    
    # Mise à jour du fichier partagé
    update_shared_state(shared_state)
    
    # Vérification finale
    log_step("VÉRIFICATION FINALE")
    
    try:
        with open(SHARED_STATE_PATH, 'r') as f:
            final_state = json.load(f)
            print(f"[TEST] Vérification shared_state.json: OK")
            print(f"[TEST] Mode: {final_state.get('mode')}")
            print(f"[TEST] Timestamp: {final_state.get('timestamp')}")
            print(f"[TEST] PnL réalisé: {final_state.get('pnl_summary', {}).get('realized')}€")
    except Exception:
        pass
    else:
        print(f"[TEST] Erreur lors de la vérification: {e}")
    
    # Sauvegarde de l'historique PnL
    pnl_tracker.save_history_to_json()
    print("[TEST] Historique PnL sauvegardé")
    
    # Déconnexion
    try:
        pass
    except:
        pass
    
    log_step("TEST TERMINÉ")
    print("[TEST] Pipeline complet testé avec succès!")

if __name__ == "__main__":
    print("\n=== TEST DU PIPELINE COMPLET ===\n")
    run_full_pipeline_test()
