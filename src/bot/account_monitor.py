



    """
    # Module legacy IBKR désactivé (à purger ou réécrire pour MT5).
    pass
    - NetLiquidation (capital total)
    - TotalCashValue (cash dispo)
    - BuyingPower
    - UnrealizedPnL / RealizedPnL
    - Drawdown (calculé)
    """
    def __init__(self, ib, refresh_interval=60):
        """Initialise le moniteur avec une instance IB déjà connectée"""
        self.ib = ib  # Réutilisation de l'objet IB déjà connecté
        self.last_snapshot = {}
        self.account_data = {}
        self.last_update = 0
        self.refresh_interval = refresh_interval  # secondes
        self.logger = logging.getLogger(__name__)
        self._connected = ib.isConnected()

    def is_connected(self) -> bool:
        # Legacy IBKR: désactivé. À réécrire pour MT5.
        return False
        return self._connected and self.ib.isConnected()

    def get_account_data(self, force_refresh=False) -> Dict[str, Any]:
        """Renvoie les données du compte, rafraîchies uniquement si nécessaire"""
        current_time = time.time()
        if force_refresh or (current_time - self.last_update) > self.refresh_interval:
        self.account_data = {}  # Legacy IBKR désactivé
        self.last_update = time.time()
        return self.account_data
            self.last_update = current_time
        return self.account_data

    def get_metric(self, metric_name: str, default=None) -> Optional[float]:
        """Récupère une métrique spécifique du compte"""
        if not self.account_data:
            self.get_account_data()
        return self.account_data.get(metric_name, default)
    
    def get_drawdown(self) -> float:
        """Récupère le drawdown actuel"""
        return self.get_metric('Drawdown', 0.0)
    
    def get_capital(self) -> float:
        """Récupère le capital (NetLiquidation)"""
        return self.get_metric('NetLiquidation', 0.0)
