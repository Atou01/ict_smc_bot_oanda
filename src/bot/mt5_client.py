import platform

if platform.system() == "Windows":
    from MetaTrader5 import initialize, shutdown, login, account_info, positions_get, order_send, symbol_info_tick
else:
    # Sur Mac/Linux, on importera le stub
    pass

class Mt5Client:
    def __init__(self):
        self.connected = False

    def initialize(self, login, password, server):
        """Initialise la connexion à MT5."""
        # À implémenter pour Windows
        pass

    def get_prices(self, symbols):
        """Retourne les ticks pour une liste de symboles."""
        pass

    def place_order(self, symbol, order_type, volume, price=None, sl=None, tp=None):
        """Place un ordre sur le marché."""
        pass

    def close_order(self, ticket):
        """Ferme un ordre par ticket."""
        pass

    def is_connected(self):
        return self.connected

    def shutdown(self):
        """Ferme proprement la connexion MT5."""
        pass
