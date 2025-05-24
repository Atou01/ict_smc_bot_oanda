"""
test_pnl_tracker.py
Script pour tester la fonctionnalité du PnLTracker avec des trades simulés.
"""

import os
import json
import time
import yaml
from bot.pnl_tracker import PnLTracker


# Chemin vers le fichier d'état partagé
SHARED_STATE_PATH = "shared_state.json"

def load_config():
    """Charge la configuration depuis config.yaml."""
    with open("config.yaml", 'r') as f:
        return yaml.safe_load(f)

def check_shared_state():
    """Vérifie et affiche l'état actuel de shared_state.json."""
    print("\n--- État actuel de shared_state.json ---")
    try:
        if os.path.exists(SHARED_STATE_PATH):
            with open(SHARED_STATE_PATH, 'r') as f:
                state = json.load(f)
                pnl_data = state.get("pnl_summary", {})
                print(f"PnL réalisé: {pnl_data.get('realized', 0)}€")
                print(f"PnL latent: {pnl_data.get('unrealized', 0)}€")
                print(f"Drawdown max: {pnl_data.get('drawdown_max', 0)}%")
                print(f"Trades ouverts: {pnl_data.get('open_trades', 0)}")
                print(f"Trades gagnants: {pnl_data.get('winning_trades', 0)}")
                print(f"Trades perdants: {pnl_data.get('losing_trades', 0)}")
                if 'last_update_timestamp' in pnl_data:
                    print(f"Dernière mise à jour: {pnl_data.get('last_update_timestamp')}")
                return pnl_data
        else:
            print(f"Fichier {SHARED_STATE_PATH} non trouvé.")
    except Exception as e:
        print(f"Erreur lors de la lecture de {SHARED_STATE_PATH}: {e}")
    except:
        pass
    return {}

def update_shared_state(pnl_data):
    """Met à jour le PnL dans shared_state.json."""
    try:
        if os.path.exists(SHARED_STATE_PATH):
            with open(SHARED_STATE_PATH, 'r') as f:
                state = json.load(f)
            
            # Mise à jour uniquement de la partie pnl_summary
            state["pnl_summary"] = pnl_data
            
            with open(SHARED_STATE_PATH, 'w') as f:
                json.dump(state, f, indent=2)
            
            print(f"shared_state.json mis à jour avec les nouvelles données PnL")
        else:
            print(f"Fichier {SHARED_STATE_PATH} non trouvé. Impossible de mettre à jour.")
    except Exception as e:
        print(f"Erreur lors de la mise à jour de {SHARED_STATE_PATH}: {e}")
    except:
        pass

def simulate_trades():
    """Simule une série de trades pour tester le PnLTracker."""
    
    try:
        cfg = load_config()
        
        
        
    except Exception as e:
        print("Utilisation d'un mock pour les tests...")
        from unittest.mock import MagicMock
        ib = MagicMock()
        ib.positions = lambda: []
    except:
        pass
    
    # Création du PnLTracker
    initial_capital = 10000
    pnl_tracker = PnLTracker(ib, initial_capital)
    
    # Vérification de l'état initial
    print("\n--- ÉTAT INITIAL ---")
    check_shared_state()
    
    # Scénario 1: Ajouter un trade gagnant
    print("\n--- SCÉNARIO 1: TRADE GAGNANT ---")
    pnl_tracker.add_realized_trade(120, is_win=True)
    print("Trade gagnant ajouté: +120€")
    pnl_tracker.update()
    summary = pnl_tracker.export_summary()
    print(f"PnL réalisé: {summary['realized']}€")
    print(f"Trades gagnants: {summary['winning_trades']}")
    
    # Mise à jour de shared_state.json et vérification
    update_shared_state(summary)
    time.sleep(1)  # Pause pour s'assurer que les fichiers sont bien écrits
    check_shared_state()
    
    # Scénario 2: Ajouter un trade perdant
    print("\n--- SCÉNARIO 2: TRADE PERDANT ---")
    pnl_tracker.add_realized_trade(-50, is_win=False)
    print("Trade perdant ajouté: -50€")
    pnl_tracker.update()
    summary = pnl_tracker.export_summary()
    print(f"PnL réalisé: {summary['realized']}€")
    print(f"Trades perdants: {summary['losing_trades']}")
    
    # Mise à jour de shared_state.json et vérification
    update_shared_state(summary)
    time.sleep(1)
    check_shared_state()
    
    # Scénario 3: Plusieurs trades pour tester le drawdown
    print("\n--- SCÉNARIO 3: TEST DRAWDOWN ---")
    # Séquence de trades gagnants et perdants pour tester le drawdown
    trades = [
        (80, True),    # +80€
        (-120, False), # -120€
        (-40, False),  # -40€
        (60, True),    # +60€
        (-30, False)   # -30€
    ]
    
    for amount, is_win in trades:
        win_lose = "gagnant" if is_win else "perdant"
        pnl_tracker.add_realized_trade(amount, is_win)
        print(f"Trade {win_lose} ajouté: {amount}€")
        pnl_tracker.update()
        summary = pnl_tracker.export_summary()
        print(f"PnL réalisé: {summary['realized']}€ | Drawdown: {summary['drawdown_max']}%")
    
    # État final après tous les tests
    update_shared_state(summary)
    time.sleep(1)
    
    print("\n--- ÉTAT FINAL ---")
    final_pnl = check_shared_state()
    
    # Sauvegarde de l'historique
    pnl_tracker.save_history_to_json()
    print("\nHistorique PnL sauvegardé dans pnl_history.json")
    
    
    try:
        pass
    except:
        pass
    
    return final_pnl

if __name__ == "__main__":
    print("=== TEST DU PNL TRACKER ===")
    final_state = simulate_trades()
    print("\nTest terminé.")
    print(f"PnL final réalisé: {final_state.get('realized', 0)}€")
    print(f"Drawdown maximum: {final_state.get('drawdown_max', 0)}%")
    print(f"Ratio G/P: {final_state.get('winning_trades', 0)}/{final_state.get('losing_trades', 0)}")
