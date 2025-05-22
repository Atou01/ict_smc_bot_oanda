"""
vantage_smoke_test.py
---------------------
Script de test rapide pour valider la connexion Vantage/MT5, récupération de données, passage d'ordre, et déconnexion.
"""
import os
from VantageConnector import VantageConnector

def main():
    login = int(os.getenv("VANTAGE_LOGIN", "10827125"))
    password = os.getenv("VANTAGE_PWD", "changeme")
    server = os.getenv("VANTAGE_SERVER", "VantageInternational-Demo")
    base_currency = os.getenv("VANTAGE_BASE_CURRENCY", "EUR")
    connector = VantageConnector(login, password, server, base_currency)

    print("== [1] Connexion à Vantage...")
    assert connector.connect(), "Connexion échouée"

    print("== [2] Infos compte:")
    summary = connector.get_account_summary()
    print(summary)
    assert summary and summary.get("balance"), "Pas d'infos compte"

    print("== [3] Bougies EURUSD (M1, 3 dernières):")
    candles = connector.get_market_data("EURUSD", n_bars=3)
    print(candles)
    assert candles is not None and len(candles) == 3, "Récupération bougies échouée"

    print("== [4] Passage d'un ordre BUY 0.01 lot EURUSD...")
    result = connector.submit_order("EURUSD", lot=0.01, order_type="BUY")
    print(result)
    assert result["success"], f"Order failed: {result}"

    print("== [5] Déconnexion...")
    connector.disconnect()
    print("[SMOKE TEST] OK!")

if __name__ == "__main__":
    main()
