"""
Test unitaire pour le module llm_engine.py
Vérifie que le module fonctionne correctement avec un payload minimal.
"""

import json
import os
import sys
from datetime import datetime

# Ajouter le répertoire parent au path pour permettre l'importation
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importer le module llm_engine
from src.bot.llm_engine import decide_trade

def create_test_payload():
    """Crée un payload de test minimal avec 3 paires"""
    return {
        "market_data": {
            "EURUSD": {
                "current_price": 1.0850,
                "daily_change": 0.0012,
                "atr": 0.0065,
                "structure": "bullish"
            },
            "GBPUSD": {
                "current_price": 1.2720,
                "daily_change": -0.0025,
                "atr": 0.0078,
                "structure": "bearish"
            },
            "USDJPY": {
                "current_price": 144.35,
                "daily_change": 0.0089,
                "atr": 0.65,
                "structure": "neutral"
            }
        },
        "ict_signals": {
            "EURUSD": [
                {"type": "OB", "timeframe": "H4", "level": 1.0825, "freshness": "high"},
                {"type": "BOS", "timeframe": "H1", "level": 1.0860, "direction": "up"}
            ],
            "GBPUSD": [
                {"type": "FVG", "timeframe": "H4", "level": 1.2695, "direction": "down"},
                {"type": "OB", "timeframe": "H1", "level": 1.2740, "freshness": "medium"}
            ],
            "USDJPY": [
                {"type": "OB", "timeframe": "H1", "level": 144.50, "freshness": "high"},
                {"type": "BOS", "timeframe": "H4", "level": 143.80, "direction": "down"}
            ]
        },
        "macro_events": [
            {"currency": "USD", "event": "CPI", "impact": "high", "expected": "0.2%", "previous": "0.4%", "time": datetime.utcnow().isoformat()},
            {"currency": "EUR", "event": "ECB Rate Decision", "impact": "high", "expected": "unchanged", "previous": "4.25%", "time": datetime.utcnow().isoformat()},
            {"currency": "GBP", "event": "Retail Sales", "impact": "medium", "expected": "-0.5%", "previous": "0.2%", "time": datetime.utcnow().isoformat()}
        ],
        "history": {
            "last_trades": [
                {"symbol": "EURUSD", "direction": "LONG", "result": "win", "pips": 35},
                {"symbol": "GBPUSD", "direction": "SHORT", "result": "loss", "pips": -20},
                {"symbol": "USDJPY", "direction": "LONG", "result": "win", "pips": 45}
            ]
        }
    }

def main():
    """Test principal"""
    print("===== TEST LLM ENGINE =====")
    print("Création du payload de test...")
    
    # Créer le payload de test
    payload = create_test_payload()
    
    print(f"Payload créé avec {len(payload['market_data'])} paires")
    
    # Appeler decide_trade
    print("\nAppel de decide_trade()...")
    try:
        result = decide_trade(payload)
        
        # Vérifier la réponse
        if result is None:
            print("\n❌ ERREUR: decide_trade() a retourné None")
        elif "status" in result and result["status"] == "stub":
            print("\n⚠️ WARNING: decide_trade() a retourné un stub - en attente de l'implémentation complète")
        else:
            print("\n✅ SUCCÈS: decide_trade() a retourné une décision valide")
            print("\nDétails de la décision:")
            print(json.dumps(result, indent=2))
            
            # Vérifier que le fichier CSV a été créé
            csv_path = os.path.join("logs", "llm_decisions.csv")
            if os.path.exists(csv_path):
                print(f"\n✅ Le fichier CSV a été créé à: {csv_path}")
            else:
                print(f"\n❌ ERREUR: Le fichier CSV n'a pas été créé à: {csv_path}")
    
    except Exception as e:
        print(f"\n❌ ERREUR: Une exception s'est produite: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
