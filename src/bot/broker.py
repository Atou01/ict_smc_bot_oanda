"""
broker.py
---------
Sélectionne et instancie le broker approprié selon la config (Vantage, autres à venir).
"""
import os
from typing import Optional

class BrokerBase:
    def connect(self):
        raise NotImplementedError
    def get_market_data(self, *a, **k):
        raise NotImplementedError
    def submit_order(self, *a, **k):
        raise NotImplementedError
    def get_account_summary(self):
        raise NotImplementedError
    def disconnect(self):
        raise NotImplementedError

def get_broker_from_config(cfg: dict) -> Optional[BrokerBase]:
    broker_type = cfg.get("type", "vantage").lower()
    if broker_type == "vantage":
        from VantageConnector import VantageConnector
        login = int(os.getenv("VANTAGE_LOGIN", cfg.get("login", "0")))
        password = os.getenv("VANTAGE_PWD", cfg.get("password", ""))
        server = os.getenv("VANTAGE_SERVER", cfg.get("server", "VantageInternational-Demo"))
        base_currency = cfg.get("base_currency", "EUR")
        return VantageConnector(login, password, server, base_currency)
    raise NotImplementedError(f"Broker inconnu: {broker_type}")
