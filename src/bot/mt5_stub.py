# Stub Mac/Linux pour Mt5Client
class Mt5Client:
    def __init__(self):
        self.connected = False

    def initialize(self, login, password, server):
        print("[MT5-Stub] Appel à initialize ignoré (plateforme non-Windows)")
        self.connected = False
        return False

    def get_prices(self, symbols):
        print(f"[MT5-Stub] get_prices({symbols}) → mock")
        return {s: {'bid': 0, 'ask': 0, 'time': 0} for s in symbols}

    def place_order(self, symbol, order_type, volume, price=None, sl=None, tp=None):
        print(f"[MT5-Stub] place_order({symbol}, {order_type}, {volume}, {price}, {sl}, {tp}) → mock")
        return None

    def close_order(self, ticket):
        print(f"[MT5-Stub] close_order({ticket}) → mock")
        return None

    def is_connected(self):
        return False

    def shutdown(self):
        print("[MT5-Stub] shutdown() → mock")
        pass
