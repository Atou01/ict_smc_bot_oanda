"""
order_manager.py
Module de gestion des ordres et du risque.
Passe les ordres selon la stratégie, gère le SL/TP, le sizing, et la sécurité du capital.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from settings import FORCE_TRADE_MINIMUM
import threading
import csv
import os
import time
import asyncio
from datetime import datetime

# Ajout Discord
try:
    from discord_utils import send_discord_notification
except ImportError:
    # Fonction de remplacement si discord_utils n'est pas disponible
    def send_discord_notification(message, type="info"):
        print(f"[Discord Notification][{type}]: {message}")
        pass


class OrderManager:
    def __init__(self, config, pnl_tracker, ib=None):
        self.ib = ib
        self.config = config
        self.pnl_tracker = pnl_tracker
        self.active_trades = {}
        self.lock = threading.Lock()
        self.closed_trades = []
        self.stats = {"win": 0, "loss": 0, "total": 0, "net_pnl": 0.0}
        self.trades_bloques = 0
        self.csv_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "../../logs/trade_history.csv"
        )
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "timestamp_entry",
                        "timestamp_exit",
                        "asset",
                        "type",
                        "strategy",
                        "sl",
                        "tp",
                        "size",
                        "pnl",
                        "capital_before",
                        "capital_after",
                        "status",
                    ]
                )

    def print_trade_plan(self, signals):
        for sig in signals:
            print(
                f"🔍 Signal détecté : {sig['type']} {sig['side']} sur {sig['timeframe']} – SL: {sig['sl']} – TP: {sig['tp']} – sizing: {sig['sizing']}"
            )

    def place_trade(self, signal, risk_pct, reset_llm_signals=False):
        symbol = signal.get("symbol", "EURUSD")
        unique_id = f"{symbol}_{signal['timeframe']}_{signal['side']}"

        # Vérifier si le trade existe déjà
        if unique_id in self.active_trades:
            # Si reset_llm_signals est activé et que c'est un signal du LLM, on réinitialise
            signal_source = signal.get("source", "").upper()
            signal_timeframe = signal.get("timeframe", "").upper()
            is_llm_signal = signal_source == "LLM" or signal_timeframe == "LLM"

            if reset_llm_signals and is_llm_signal:
                print(f"[OrderManager] Reset du trade LLM existant pour {unique_id}")
                try:
                    existing_trade = self.active_trades[unique_id]
                    self.ib.cancelOrder(existing_trade.get("trade"))
                    print(f"[OrderManager] Ordre précédent annulé pour {unique_id}")
                except Exception as e:
                    print(f"[OrderManager] Erreur lors de l'annulation: {e}")
                del self.active_trades[unique_id]
            else:
                print(f"[DEBUG EXIT] Trade déjà actif pour {unique_id}, aucun nouvel ordre envoyé.")
                self.trades_bloques += 1
                return None, self.pnl_tracker.get_risk_status()

        # Protection drawdown max
        pnl = self.pnl_tracker.get_total_pnl()
        max_dd = self.config["RISK"]["max_drawdown_pct"]
        capital = self.config["RISK"]["capital"]
        if pnl < -abs(capital * max_dd / 100):
            print(f"[DEBUG EXIT] Drawdown max dépassé : {pnl:.2f}€ < {capital * max_dd / 100:.2f}€.")
            self.trades_bloques += 1
            return None

        # Calcul de risque dynamique
        risk_status = self.pnl_tracker.get_risk_status()
        max_risk = risk_status.get("max_risk_pct", 1.0)
        dynamic_risk_pct = min(risk_pct, max_risk)
        final_risk_pct = min(risk_pct, dynamic_risk_pct)
        print(f"[RISK] Risk ajusté: {final_risk_pct*100:.2f}% (demandé: {risk_pct*100:.2f}%, dynamique: {dynamic_risk_pct*100:.2f}%)")

        # Calcul sizing
        entry = float(signal["entry"])
        sl = float(signal["sl"])
        tp = float(signal.get("tp", 0.0))
        stop_pips = abs(entry - sl) * 10000
        if stop_pips == 0:
            stop_pips = 20
        capital = float(self.config["RISK"]["capital"])
        pip_value = 10
        try:
            raw_size = (capital * final_risk_pct) / (stop_pips * pip_value)
            size = max(round(raw_size), 1)  # min 1 lot
        except Exception as e:
            print(f"[CRITICAL] Erreur dans le calcul du sizing: {e}")
            size = 1

        # Création du contrat (purge IBKR/IDEALPRO)
        contract = {"symbol": symbol}

        # Mode test (LLM/test signal)
        test_mode = signal.get("timeframe") == "LLM" and "test" in signal.get("reason", "").lower()
        if test_mode:
            print("[TEST] Mode test détecté - Simulation d'un ordre sans broker")
            trade = {
                "orderId": 999999,
                "status": "Simulated",
                "action": signal.get("side", "LONG"),
                "totalQuantity": size,
                "symbol": symbol,
            }
        else:
            try:
                print(f"[ORDER SENDING] Envoi de l’ordre : {signal.get('side', 'LONG')} {size} {contract['symbol']}")
                trade = self.ib.placeOrder(contract, size)
                print(f"[ORDER SENT] Ordre envoyé avec succès : {signal.get('side', 'LONG')} {size} {contract['symbol']}")
            except Exception as e:
                print(f"[CRITICAL] Erreur lors du placement de l'ordre: {e}")
                self.trades_bloques += 1
                return None, self.pnl_tracker.get_risk_status()

        trade_info = {
            "trade": trade,
            "signal": signal,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "side": signal.get("side", "LONG"),
            "size": size,
            "risk_pct": final_risk_pct,
            "status": "OPEN",
            "open_time": datetime.now(),
            "contract": contract,
        }
        self.active_trades[unique_id] = trade_info
        return trade_info, self.pnl_tracker.get_risk_status()

    def reset(self, only_llm_signals=False, symbol=None):
        """Réinitialise l'état du gestionnaire d'ordres (utile pour les tests).

        Args:
            only_llm_signals (bool): Si True, ne réinitialise que les signaux provenant du LLM
            symbol (str): Si spécifié, ne réinitialise que les signaux pour ce symbole
        """
        with self.lock:
            if only_llm_signals:
                # Identifier les signaux à réinitialiser
                to_remove = []
                for trade_id, trade_info in self.active_trades.items():
                    signal = trade_info.get("signal", {})
                    # Vérifier si c'est un signal LLM (timeframe = LLM ou source = LLM)
                    is_llm = (
                        signal.get("timeframe") == "LLM"
                        or signal.get("source") == "LLM"
                    )

                    # Vérifier si le symbole correspond, si spécifié
                    symbol_match = True
                    if symbol:
                        signal_symbol = signal.get("symbol", "")
                        symbol_match = signal_symbol.upper() == symbol.upper()

                    # Ajouter à la liste des trades à supprimer si les conditions sont remplies
                    if is_llm and symbol_match:
                        to_remove.append(trade_id)

                # Supprimer les signaux identifiés
                for trade_id in to_remove:
                    del self.active_trades[trade_id]

                if to_remove:
                    print(
                        f"[OrderManager] {len(to_remove)} signaux LLM réinitialisés"
                        + (f" pour {symbol}" if symbol else "")
                        + "."
                    )
                else:
                    print(
                        "[OrderManager] Aucun signal LLM actif à réinitialiser"
                        + (f" pour {symbol}" if symbol else "")
                        + "."
                    )
            else:
                # Réinitialisation complète de tous les trades actifs
                old_count = len(self.active_trades)
                self.active_trades = {}
                print(f"[OrderManager] {old_count} trades actifs effacés.")

            return True  # Confirmation de la réinitialisation

    def monitor_trades(self):
        """Surveille les trades ouverts pour gérer les SL/TP
        Gère également la création d'une boucle d'événements asyncio si nécessaire.
        """
        # Variable pour désactiver temporairement le monitoring lors des tests LLM
        self.monitoring_active = True
        # Filtrage Forex uniquement
        FOREX_SYMBOLS = {
            "EURUSD",
            "GBPUSD",
            "USDJPY",
            "AUDUSD",
            "USDCAD",
            "USDCHF",
            "NZDUSD",
            "EURGBP",
            "EURJPY",
            "GBPJPY",
            "AUDJPY",
            "CHFJPY",
            "EURCHF",
            "EURCAD",
            "EURAUD",
            "NZDJPY",
            "AUDCAD",
            "AUDNZD",
            "CADCHF",
            "CADJPY",
            "GBPAUD",
            "GBPCAD",
            "GBPCHF",
            "NZDCAD",
            "NZDCHF",
            "NZDUSD",
            "USDMXN",
            "USDNOK",
            "USDSEK",
            "USDHKD",
            "USDTRY",
            "USDZAR",
            "USDPLN",
        }
        # On ne surveille que les trades dont le symbole est dans la liste
        self.active_trades = {
            k: v
            for k, v in self.active_trades.items()
            if v.get("contract", None)
            and getattr(v["contract"], "symbol", None) in FOREX_SYMBOLS
        }

        try:
            # Configuration de la boucle d'événements asyncio pour ce thread
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # Si aucune boucle n'existe dans ce thread, en créer une nouvelle
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                print(
                    "[OrderManager] Nouvelle boucle d'événements asyncio créée pour le thread de surveillance"
                )

            # Configuration de gestion des erreurs pour la boucle d'événements
            def exception_handler(loop, context):
                print(f"[OrderManager][ERREUR] Exception asyncio: {context['message']}")
                if "exception" in context:
                    print(f"[OrderManager][ERREUR] Détails: {context['exception']}")

            loop.set_exception_handler(exception_handler)

            print("[OrderManager] Démarrage du thread de surveillance des trades")

            while self.monitoring_active:
                try:
                    with self.lock:
                        to_close = []

                        # Si aucun trade actif, attendre simplement
                        if not self.active_trades:
                            time.sleep(5)
                            continue

                        # Parcourir tous les trades actifs de manière sécurisée
                        active_trades_copy = dict(self.active_trades)
                        for unique_id, trade_info in active_trades_copy.items():
                            try:
                                # Récupérer les informations du trade
                                trade = trade_info.get("trade")
                                contract = trade_info.get("contract")
                                sl = trade_info.get("sl", 0)
                                tp = trade_info.get("tp", 0)
                                entry = trade_info.get("entry", 0)
                                side = trade_info.get("side", "")
                                size = trade_info.get("size", 0)

                                # Si la connexion est perdue, passer au trade suivant
                                if not self.ib.isConnected():
                                    print(
                                        f"[OrderManager] Connexion perdue, impossible de surveiller {unique_id}"
                                    )
                                    continue

                                # Récupérer le prix actuel avec gestion des erreurs
                                try:
                                    ticker = self.ib.reqMktData(
                                        contract, "", False, False
                                    )
                                    self.ib.sleep(1)  # Attendre les données
                                    last = ticker.last if ticker.last else ticker.close

                                    if not last:
                                        print(
                                            f"[OrderManager] Pas de prix disponible pour {unique_id}"
                                        )
                                        continue

                                    # Calcul PnL
                                    pnl = (
                                        (last - entry) * size * 10000
                                        if side == "BUY"
                                        else (entry - last) * size * 10000
                                    )
                                    print(
                                        f"[OrderManager][Suivi] {unique_id} | Prix: {last:.5f} | SL: {sl} | TP: {tp} | PnL: {pnl:.2f} | Statut: {trade_info.get('status', 'UNKNOWN')}"
                                    )

                                    # SL/TP touché
                                    if (side == "BUY" and last <= sl) or (
                                        side == "SELL" and last >= sl
                                    ):
                                        result = "LOSS"
                                        print(
                                            f"📉 SL touché pour {unique_id}, clôture du trade."
                                        )
                                        to_close.append((unique_id, pnl, result, last))
                                    elif (side == "BUY" and last >= tp) or (
                                        side == "SELL" and last <= tp
                                    ):
                                        result = "WIN"
                                        print(
                                            f"🏁 TP atteint pour {unique_id}, clôture du trade."
                                        )
                                        to_close.append((unique_id, pnl, result, last))
                                except Exception as price_error:
                                    print(
                                        f"[OrderManager] Erreur lors de la récupération du prix pour {unique_id}: {price_error}"
                                    )
                                    continue
                            except Exception as trade_error:
                                print(
                                    f"[OrderManager] Erreur générale pour le trade {unique_id}: {trade_error}"
                                )
                                continue
                    # Clôture effective des trades
                    try:
                        for unique_id, pnl, result, exit_price in to_close:
                            try:
                                if unique_id not in self.active_trades:
                                    print(
                                        f"[OrderManager] Trade {unique_id} déjà fermé ou absent"
                                    )
                                    continue

                                trade_info = self.active_trades[unique_id]
                                # Annule l'ordre broker si encore ouvert
                                try:
                                    self.ib.cancelOrder(trade_info.get("trade"))
                                except Exception as cancel_err:
                                    print(
                                        f"[OrderManager] Erreur annulation ordre: {cancel_err}"
                                    )

                                # Mise à jour du statut du trade
                                trade_info["status"] = "CLOSED"
                                trade_info["close_time"] = datetime.now()
                                trade_info["exit"] = exit_price
                                trade_info["pnl"] = pnl
                                self.closed_trades.append(trade_info)

                                # Mise à jour des statistiques
                                self.stats["total"] += 1
                                if result == "WIN":
                                    self.stats["win"] += 1
                                else:
                                    self.stats["loss"] += 1

                                # Création d'un dict avec tous les détails du trade pour le PnLTracker
                                try:
                                    detailed_trade = {
                                        "symbol": trade_info["contract"].symbol,
                                        "strategy": trade_info["signal"].get(
                                            "type", "Unknown"
                                        ),  # Type de signal
                                        "timeframe": trade_info["signal"].get(
                                            "timeframe", "M15"
                                        ),
                                        "entry": trade_info["entry"],
                                        "sl": trade_info["sl"],
                                        "tp": trade_info["tp"],
                                        "exit_price": exit_price,
                                        "side": trade_info["side"],
                                        "size": trade_info["size"],
                                        "open_time": trade_info[
                                            "open_time"
                                        ].isoformat(),
                                        "close_time": trade_info[
                                            "close_time"
                                        ].isoformat(),
                                    }
                                    # Mise à jour du pnl tracker avec les détails complets
                                    self.pnl_tracker.add_realized_trade(
                                        pnl, detailed_trade
                                    )
                                except Exception as detail_err:
                                    print(
                                        f"[OrderManager] Erreur création détails: {detail_err}"
                                    )

                                # Mise à jour du CSV
                                try:
                                    import pandas as pd

                                    df = pd.read_csv(self.csv_path)
                                    # Cherche la ligne à compléter
                                    mask = (
                                        (df["asset"] == trade_info["contract"].symbol)
                                        & (
                                            df["timestamp_entry"]
                                            == trade_info["open_time"].strftime(
                                                "%Y-%m-%d %H:%M:%S"
                                            )
                                        )
                                        & (df["timestamp_exit"] == "")
                                    )
                                    if mask.any():
                                        idx = df[mask].index[0]
                                        df.at[idx, "timestamp_exit"] = trade_info[
                                            "close_time"
                                        ].strftime("%Y-%m-%d %H:%M:%S")
                                        df.at[idx, "pnl"] = f"{pnl:.2f}"
                                        df.at[idx, "capital_after"] = (
                                            f"{getattr(self.pnl_tracker, 'realized_pnl', '')}"
                                        )
                                        df.at[idx, "status"] = (
                                            "gagné" if result == "WIN" else "perdu"
                                        )
                                    df.to_csv(self.csv_path, index=False)
                                except Exception as csv_err:
                                    print(
                                        f"[OrderManager][CSV] Erreur update clôture trade : {csv_err}"
                                    )

                                # Logs et notifications
                                print(
                                    f"[OrderManager][Clôture] {unique_id} | Résultat: {result} | PnL: {pnl:.2f} | Fermé à {exit_price}"
                                )

                                # Notification Discord clôture de trade
                                try:
                                    send_discord_notification(
                                        f"🔔 **Trade clôturé**\nInstrument : `{trade_info['contract'].symbol}`\nSens : `{trade_info['side']}`\nEntrée : `{trade_info['entry']}`\nSortie : `{exit_price}`\nSL : `{trade_info['sl']}`\nTP : `{trade_info['tp']}`\nRésultat : `{result}`\nPnL : `{pnl:.2f}€`",
                                        type="notif",
                                    )
                                except Exception as discord_err:
                                    print(
                                        f"[OrderManager] Erreur notification Discord: {discord_err}"
                                    )

                                # Suppression du trade des actifs
                                del self.active_trades[unique_id]

                            except Exception as close_err:
                                print(
                                    f"[OrderManager] Erreur clôture du trade {unique_id}: {close_err}"
                                )
                    except Exception as global_err:
                        print(
                            f"[OrderManager] Erreur générale de traitement des clôtures: {global_err}"
                        )

                # Pause entre les cycles de surveillance
                except Exception as cycle_err:
                    print(
                        f"[OrderManager] Erreur dans le cycle de surveillance: {cycle_err}"
                    )

                time.sleep(30)

        except Exception as monitor_err:
            print(
                f"[OrderManager] Erreur fatale dans le thread de surveillance: {monitor_err}"
            )
            print("[OrderManager] Arrêt du thread de surveillance des trades")
            return

    def print_trade_plan(self, signals):
        for sig in signals:
            print(
                f"🔍 Signal détecté : {sig['type']} {sig['side']} sur {sig['timeframe']} – SL: {sig['sl']} – TP: {sig['tp']} – sizing: {sig['sizing']}"
            )
