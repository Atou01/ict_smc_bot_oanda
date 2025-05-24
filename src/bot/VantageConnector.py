"""
VantageConnector.py
-------------------
Wrapper pour MetaTrader5 (Vantage Markets) : connexion, récupération de données, passage d'ordres, résumé du compte, déconnexion.
"""
import os
import time
from typing import Optional, Dict, Any

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None
    print("[VantageConnector] MetaTrader5 package non trouvé. Installez-le avec 'pip install MetaTrader5'.")

class VantageConnector:
    def __init__(self, login: Optional[int] = None, password: Optional[str] = None, server: Optional[str] = None, base_currency: str = "EUR"):
        self.login = login or int(os.getenv("VANTAGE_LOGIN", "0"))
        self.password = password or os.getenv("VANTAGE_PWD", "")
        self.server = server or os.getenv("VANTAGE_SERVER", "VantageInternational-Demo")
        self.base_currency = base_currency
        self.connected = False
        self._account_info = None

    def connect(self) -> bool:
        if mt5 is None:
            print("[VantageConnector] MT5 non importé, connexion impossible.")
            return False
        if not mt5.initialize():
            print(f"[VantageConnector] Erreur d'initialisation MT5: {mt5.last_error()}")
            return False
        authorized = mt5.login(self.login, password=self.password, server=self.server)
        if not authorized:
            print(f"[VantageConnector] Connexion échouée: {mt5.last_error()}")
            return False
        self.connected = True
        print(f"[VantageConnector] Connecté à Vantage (login={self.login}, server={self.server})")
        return True

    def get_market_data(self, symbol: str, timeframe=mt5.TIMEFRAME_M1, n_bars: int = 3) -> Optional[Any]:
        if not self.connected:
            print("[VantageConnector] Non connecté. Impossible de récupérer les données de marché.")
            return None
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n_bars)
        return rates

    def submit_order(self, symbol: str, lot: float, order_type: str = "BUY", price: Optional[float] = None, sl: Optional[float] = None, tp: Optional[float] = None, comment: str = "") -> Dict[str, Any]:
        if not self.connected:
            return {"success": False, "error": "Not connected"}
        order_type_map = {"BUY": mt5.ORDER_TYPE_BUY, "SELL": mt5.ORDER_TYPE_SELL}
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": order_type_map.get(order_type, mt5.ORDER_TYPE_BUY),
            "price": price or mt5.symbol_info_tick(symbol).ask,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 42,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC
        }
        result = mt5.order_send(request)
        return {"success": result.retcode == mt5.TRADE_RETCODE_DONE, "result": result._asdict()}

    def get_account_summary(self) -> Optional[Dict[str, Any]]:
        if not self.connected:
            return None
        info = mt5.account_info()
        if info:
            return info._asdict()
        return None

    def disconnect(self):
        if mt5:
            mt5.shutdown()
        self.connected = False
        print("[VantageConnector] Déconnecté de Vantage.")
