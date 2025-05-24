"""
test_risk_management.py
Script pour tester la gestion du risque dynamique et le blocage du trading en cas de drawdown critique.
"""

import json
import yaml
import os
from unittest.mock import MagicMock

from bot.pnl_tracker import PnLTracker  
from bot.order_manager import OrderManager

# Chemins des fichiers
CONFIG_PATH = "config.yaml"
SHARED_STATE_PATH = "shared_state.json"


def load_config():
    """Charge la configuration depuis config.yaml."""
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def update_shared_state_risk(risk_status):
    """Met à jour uniquement la partie risk_status dans shared_state.json."""
    try:
        if os.path.exists(SHARED_STATE_PATH):
            with open(SHARED_STATE_PATH, "r") as f:
                state = json.load(f)

            # Mise à jour du statut de risque
            state["risk_status"] = risk_status

            with open(SHARED_STATE_PATH, "w") as f:
                json.dump(state, f, indent=2)

            print(
                f"shared_state.json mis à jour avec risque: {risk_status['status_message']}"
            )
        else:
            print(
                f"Fichier {SHARED_STATE_PATH} non trouvé. Impossible de mettre à jour."
            )
    except Exception as e:
        print(f"Erreur lors de la mise à jour de {SHARED_STATE_PATH}: {e}")


def print_trade_details(trade_info):
    """Affiche les détails d'un trade."""
    # Si on reçoit un tuple (trade_info, risk_status), on ne garde que le dict
    if isinstance(trade_info, tuple):
        trade_info = trade_info[0]
    if not trade_info:
        print("❌ Trade non placé")
        return

    print("✅ Trade placé:")
    print(f"  - Side: {trade_info.get('side', 'N/A')}")
    print(f"  - Entry: {trade_info.get('entry', 'N/A')}")
    print(f"  - SL: {trade_info.get('sl', 'N/A')}")
    print(f"  - TP: {trade_info.get('tp', 'N/A')}")
    print(f"  - Risk %: {trade_info.get('risk_pct', 0)*100:.2f}%")
    print(f"  - Size: {trade_info.get('size', 'N/A')}")


def simulate_trade(pnl_tracker, order_manager, risk_pct=0.01):
    """Simule un trade avec le risk actuel."""
    # Signal exemple
    signal = {
        "type": "FVG",
        "side": "LONG",
        "timeframe": "M15",
        "entry": 1.0830,
        "sl": 1.0810,
        "tp": 1.0880,
        "sizing": "1% capital",
        "symbol": "EURUSD",
    }

    # Afficher le statut de risque actuel
    risk_status = pnl_tracker.get_risk_status()
    print(f"\nStatut de risque actuel: {risk_status['status_message']}")

    # Mise à jour du shared_state.json
    update_shared_state_risk(risk_status)

    # Tenter de placer un trade
    print(f"\nTentative de trade avec risk_pct demandé: {risk_pct*100:.2f}%")
    trade_info = order_manager.place_trade(signal, risk_pct)

    # Afficher le résultat
    print_trade_details(trade_info)

    return trade_info, risk_status


def test_risk_management():
    """Teste les différents scénarios du risk management dynamique."""

    mock_ib = MagicMock()
    mock_ib.positions = lambda: []

    # Charger la config
    cfg = load_config()

    # Créer le PnL tracker avec capital initial
    contract = {"symbol": "EURUSD"}
    initial_capital = float(cfg.get("RISK", {}).get("capital", 10000))
    pnl_tracker = PnLTracker(mock_ib, initial_capital)

    # Créer l'OrderManager
    order_manager = OrderManager(mock_ib, cfg, pnl_tracker)

    print("=" * 60)
    print("TEST DU RISK MANAGEMENT DYNAMIQUE")
    print("=" * 60)

    # CAS 1: Situation normale (drawdown < 1.5%)
    print("\n\n" + "=" * 20 + " CAS 1: SITUATION NORMALE " + "=" * 20)
    print("Drawdown < 1.5% => risk_pct attendu = 1.0%")

    # Simuler un PnL légèrement négatif (drawdown < 1.5%)
    pnl_tracker.realized_pnl = -100  # -100€ sur 10,000€ = -1% (drawdown de 1%)
    pnl_tracker.update()

    # Tenter un trade
    trade_info, risk_status = simulate_trade(pnl_tracker, order_manager, 0.01)

    # Vérifier si le risk est bien à 1%
    assert (
        risk_status["risk_pct"] == 1.0
    ), f"Risk devrait être 1.0%, obtenu {risk_status['risk_pct']}%"

    # Réinitialiser les trades actifs avant le prochain cas
    order_manager.reset()

    # CAS 2: Drawdown modéré (entre 1.5% et 3%)
    print("\n\n" + "=" * 20 + " CAS 2: DRAWDOWN MODÉRÉ " + "=" * 20)
    print("1.5% ≤ drawdown < 3% => risk_pct attendu = 0.5%")

    # Simuler un PnL négatif modéré (drawdown entre 1.5% et 3%)
    pnl_tracker.realized_pnl = -200  # -200€ sur 10,000€ = -2% (drawdown de 2%)
    pnl_tracker.update()

    # Tenter un trade
    trade_info, risk_status = simulate_trade(pnl_tracker, order_manager, 0.01)

    # Vérifier si le risk est réduit à 0.5%
    assert (
        risk_status["risk_pct"] == 0.5
    ), f"Risk devrait être 0.5%, obtenu {risk_status['risk_pct']}%"

    # Réinitialiser les trades actifs avant le prochain cas
    order_manager.reset()

    # CAS 3: Drawdown critique (> 3%)
    print("\n\n" + "=" * 20 + " CAS 3: DRAWDOWN CRITIQUE " + "=" * 20)
    print("drawdown ≥ 3% => Trading bloqué")

    # Simuler un PnL très négatif (drawdown > 3%)
    pnl_tracker.realized_pnl = -350  # -350€ sur 10,000€ = -3.5% (drawdown de 3.5%)
    pnl_tracker.update()

    # Tenter un trade (devrait être bloqué)
    trade_info, risk_status = simulate_trade(pnl_tracker, order_manager, 0.01)

    # Vérifier si le trading est bloqué
    assert not risk_status[
        "trading_allowed"
    ], "Le trading devrait être bloqué avec un drawdown > 3%"
    assert (
        trade_info is None
    ), "Le trade ne devrait pas être placé avec un drawdown critique"

    # Réinitialiser les trades actifs avant le prochain cas
    order_manager.reset()

    # CAS 4: Retour à la normale
    print("\n\n" + "=" * 20 + " CAS 4: RETOUR À LA NORMALE " + "=" * 20)
    print("Retour à un drawdown < 1.5% => trading à nouveau autorisé")

    # Simuler un PnL positif (fin du drawdown)
    pnl_tracker.realized_pnl = 50  # +50€ = pas de drawdown
    pnl_tracker.drawdown_pct = 0.5  # Drawdown de 0.5%
    pnl_tracker.update()

    # Tenter un trade (devrait être autorisé)
    trade_info, risk_status = simulate_trade(pnl_tracker, order_manager, 0.01)

    # Vérifier si le trading est à nouveau autorisé
    assert risk_status[
        "trading_allowed"
    ], "Le trading devrait être autorisé après un retour à la normale"
    assert (
        trade_info is not None
    ), "Le trade devrait être placé après un retour à la normale"

    print("\n\n" + "=" * 20 + " RÉSUMÉ DES TESTS " + "=" * 20)
    print("✅ Tous les tests de risk management ont réussi!")
    print("1. risk_pct = 1.0% quand drawdown < 1.5%")
    print("2. risk_pct = 0.5% quand 1.5% ≤ drawdown < 3%")
    print("3. Trading bloqué quand drawdown ≥ 3%")
    print("4. Trading ré-autorisé après retour à la normale")


if __name__ == "__main__":
    test_risk_management()
