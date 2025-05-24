"""
pnl_tracker.py
Module de tracking des performances PnL.
Calcule et suit les performances financières du bot de trading.
"""

from datetime import datetime
import csv
import os
import json


class PnLTracker:
    def __init__(self, ib=None, initial_capital=10000):
        self.ib = ib
        self.initial_capital = initial_capital
        self.max_drawdown = 0
        self.realized_pnl = 0
        self.unrealized_pnl = 0
        self.total_losses = 0
        self.total_gains = 0
        self.drawdown_pct = 0
        self.history = []
        self.trade_history = (
            []
        )  # Nouvel attribut pour l'historique des trades détaillés
        import os

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        LOGS_DIR = os.path.normpath(os.path.join(BASE_DIR, "../../logs"))
        self.csv_path = os.path.join(LOGS_DIR, "pnl_history.csv")
        self.trade_log_path = os.path.join(LOGS_DIR, "trade_log.csv")
        self.json_path = os.path.join(LOGS_DIR, "pnl_history.json")
        self.trade_json_path = os.path.join(LOGS_DIR, "trade_history.json")

        # Initialisation du fichier CSV si nécessaire
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "timestamp",
                        "realized_pnl",
                        "unrealized_pnl",
                        "drawdown_pct",
                        "open_trades",
                        "winning_trades",
                        "losing_trades",
                    ]
                )

        # Initialisation du fichier de log des trades si nécessaire
        if not os.path.exists(self.trade_log_path):
            with open(self.trade_log_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "timestamp",
                        "symbol",
                        "strategy",
                        "timeframe",
                        "entry",
                        "sl",
                        "tp",
                        "exit_price",
                        "result",
                        "gain",
                    ]
                )

        # Charger les historiques existants s'ils existent
        self._load_history()

    def update(self):
        """Met à jour toutes les métriques PnL basées sur les positions du broker et l'historique des trades."""
        # 1. Calcul du PnL latent à partir des positions ouvertes
        if self.ib is not None:
            positions = self.ib.positions()
        else:
            positions = []
        unrealized = 0

        for position in positions:
            contract = position.contract
            position_size = position.position

            # Récupérer le prix actuel
            ticker = self.ib.reqMktData(contract, "", False, False)
            self.ib.sleep(
                0.2
            )  # Petite pause pour laisser le temps de récupérer les données

            # Calcul du PnL latent
            current_price = ticker.last if ticker.last else ticker.close
            avg_cost = position.avgCost

            # Calcul du PnL selon le sens de la position
            if position_size > 0:  # Position long
                unrealized += (current_price - avg_cost) * position_size
            else:  # Position short
                unrealized += (avg_cost - current_price) * abs(position_size)

        # Mise à jour du PnL latent
        self.unrealized_pnl = unrealized

        # 2. Calcul du drawdown actuel
        current_equity = self.initial_capital + self.realized_pnl + self.unrealized_pnl
        peak_equity = max(self.initial_capital, current_equity)
        current_drawdown = (
            (peak_equity - current_equity) / peak_equity * 100 if peak_equity > 0 else 0
        )

        # Mise à jour du drawdown maximum si nécessaire
        if current_drawdown > self.drawdown_pct:
            self.drawdown_pct = current_drawdown

        # 3. Enregistrement des données dans l'historique
        timestamp = datetime.now().isoformat()
        record = {
            "timestamp": timestamp,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "drawdown_pct": self.drawdown_pct,
            "open_trades": len(positions),
            "winning_trades": self.total_gains,
            "losing_trades": self.total_losses,
        }
        self.history.append(record)

        # 4. Mise à jour du fichier CSV
        with open(self.csv_path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    timestamp,
                    round(self.realized_pnl, 2),
                    round(self.unrealized_pnl, 2),
                    round(self.drawdown_pct, 2),
                    len(positions),
                    self.total_gains,
                    self.total_losses,
                ]
            )

        return record

    def _load_history(self):
        """Charge les historiques existants depuis les fichiers JSON et CSV."""
        # Charger l'historique PnL global
        if os.path.exists("pnl_history.json"):
            try:
                with open("pnl_history.json", "r") as f:
                    self.history = json.load(f)
            except Exception as e:
                print(f"[PNL] Erreur lors du chargement de l'historique PnL: {e}")

        # Charger l'historique détaillé des trades
        if os.path.exists("trade_history.json"):
            try:
                with open("trade_history.json", "r") as f:
                    self.trade_history = json.load(f)
            except Exception as e:
                print(
                    f"[PNL] Erreur lors du chargement de l'historique des trades: {e}"
                )

    def add_realized_trade(self, pnl, trade_info=None):
        """
        Ajoute un trade réalisé au tracker avec tous les détails nécessaires.

        Args:
            pnl (float): PnL du trade (positif pour gain, négatif pour perte)
            trade_info (dict, optional): Détails du trade (symbol, strategy, timeframe, entry, sl, tp, exit_price)
        """
        self.realized_pnl += pnl

        is_win = pnl > 0

        if is_win:
            self.total_gains += 1
        else:
            self.total_losses += 1

        # Enregistrement détaillé du trade si les informations sont fournies
        if trade_info:
            timestamp = datetime.now().isoformat()
            detailed_trade = {
                "timestamp": timestamp,
                "symbol": trade_info.get("symbol", "EURUSD"),
                "strategy": trade_info.get("strategy", ""),
                "timeframe": trade_info.get("timeframe", "M15"),
                "entry": trade_info.get("entry", 0),
                "sl": trade_info.get("sl", 0),
                "tp": trade_info.get("tp", 0),
                "exit_price": trade_info.get("exit_price", 0),
                "result": "WIN" if is_win else "LOSS",
                "gain": pnl,
            }

            # Ajouter à l'historique des trades
            self.trade_history.append(detailed_trade)

            # Mettre à jour le fichier CSV des trades
            with open(self.trade_log_path, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        timestamp,
                        detailed_trade["symbol"],
                        detailed_trade["strategy"],
                        detailed_trade["timeframe"],
                        detailed_trade["entry"],
                        detailed_trade["sl"],
                        detailed_trade["tp"],
                        detailed_trade["exit_price"],
                        detailed_trade["result"],
                        pnl,
                    ]
                )

            # Sauvegarder l'historique JSON des trades
            self.save_trade_history()

    def get_total_pnl(self):
        """Retourne le PnL total (réalisé + latent)."""
        return self.realized_pnl + self.unrealized_pnl

    def get_drawdown(self) -> float:
        """Retourne le niveau actuel de drawdown en pourcentage."""
        return round(self.drawdown_pct, 2)

    def get_risk_status(self) -> dict:
        """Génère le statut de risque en fonction du drawdown actuel."""
        drawdown = self.get_drawdown()

        # Déterminer le niveau de risque dynamique
        if drawdown < 1.5:
            risk_pct = 1.0
            trading_allowed = True
        elif 1.5 <= drawdown < 3.0:
            risk_pct = 0.5
            trading_allowed = True
        else:  # drawdown >= 3.0
            risk_pct = 0.0
            trading_allowed = False

        return {
            "risk_pct": risk_pct,
            "drawdown": drawdown,
            "trading_allowed": trading_allowed,
            "status_message": f"Drawdown: {drawdown}%, Risk: {risk_pct}%, Trading: {'actif' if trading_allowed else 'bloqué'}",
        }

    def export_summary(self) -> dict:
        """Exporte un résumé des métriques PnL pour affichage ou stockage."""
        open_trades = 0
        if self.ib is not None:
            try:
                open_trades = len(self.ib.positions())
            except Exception:
                open_trades = 0
        return {
            "realized": round(self.realized_pnl, 2),
            "unrealized": round(self.unrealized_pnl, 2),
            "drawdown_max": round(self.drawdown_pct, 2),
            "open_trades": open_trades,
            "winning_trades": self.total_gains,
            "losing_trades": self.total_losses,
            "last_update_timestamp": datetime.now().isoformat(),
        }

    def save_history_to_json(self, filepath="pnl_history.json"):
        """Sauvegarde l'historique PnL global au format JSON."""
        with open(filepath, "w") as f:
            json.dump(self.history, f, indent=2)

    def save_trade_history(self, filepath="trade_history.json"):
        """Sauvegarde l'historique détaillé des trades au format JSON."""
        with open(filepath, "w") as f:
            json.dump(self.trade_history, f, indent=2)
