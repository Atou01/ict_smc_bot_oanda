#!/usr/bin/env python3
"""
update_strategy_stats.py
Script qui met à jour automatiquement les statistiques de performance des stratégies
à partir de l'historique des trades réels.
"""

import os
import csv
import json
import datetime
import sys
from tests.test_strategy_scoring import main as run_scoring


def load_trade_history(
    pnl_history_path="pnl_history.json", trade_log_path="trade_log.csv"
):
    """
    Charge l'historique des trades depuis le fichier de log CSV ou JSON.
    Retourne une liste de trades formatée pour le scoring.
    """
    trades = []

    # Essayer d'abord trade_log.csv (source préférée car plus détaillée)
    if os.path.exists(trade_log_path) and os.path.getsize(trade_log_path) > 10:
        try:
            with open(trade_log_path, "r", newline="") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if not row.get("symbol") or not row.get("entry"):
                        continue  # Ignorer les lignes incomplètes

                    # Convertir le résultat (WIN/LOSS) ou déduire à partir du PnL
                    if "result" in row and row["result"]:
                        outcome = row["result"].upper()
                    else:
                        outcome = "WIN" if float(row.get("pnl", 0)) > 0 else "LOSS"

                    # Déterminer la stratégie (si disponible ou à partir d'un paramètre enrichi)
                    strategy = row.get("strategy", "Unknown")

                    # Créer un dictionnaire avec les champs nécessaires pour simulated_signals.csv
                    trade = {
                        "date": row.get(
                            "timestamp", datetime.datetime.now().strftime("%Y-%m-%d")
                        ),
                        "symbol": row.get("symbol"),
                        "strategy": strategy,
                        "timeframe": row.get(
                            "timeframe", "M15"
                        ),  # Valeur par défaut si non spécifiée
                        "entry": row.get("entry"),
                        "sl": row.get("sl"),
                        "tp": row.get("tp"),
                        "outcome": outcome,
                    }
                    trades.append(trade)

            print(f"[INFO] Chargé {len(trades)} trades depuis {trade_log_path}")

        except Exception as e:
            print(f"[ERREUR] Lecture de {trade_log_path}: {e}")

    # Si aucun trade n'a été chargé, essayer avec pnl_history.json (moins détaillé)
    if not trades and os.path.exists(pnl_history_path):
        try:
            with open(pnl_history_path, "r") as f:
                pnl_data = json.load(f)

            # PnL history ne contient pas les détails des trades, on va générer des données synthétiques
            # pour le scoring basé sur les compteurs winning_trades et losing_trades

            print(
                f"[AVERTISSEMENT] {pnl_history_path} ne contient pas les détails des trades (entry, sl, tp)."
            )
            print(
                "[AVERTISSEMENT] Les statistiques seront basées uniquement sur les résultats agrégés."
            )

            # On utilise les entrées les plus récentes si disponibles
            if pnl_data:
                latest_entry = pnl_data[-1]
                wins = latest_entry.get("winning_trades", 0)
                losses = latest_entry.get("losing_trades", 0)

                # Génération de données synthétiques pour le scoring
                strategies = ["OB", "FVG", "BOS", "Sweep"]
                for i in range(wins):
                    strategy = strategies[i % len(strategies)]
                    trades.append(
                        {
                            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                            "symbol": "EURUSD",
                            "strategy": strategy,
                            "timeframe": "M15",
                            "entry": "1.0800",
                            "sl": "1.0750",
                            "tp": "1.0900",
                            "outcome": "WIN",
                        }
                    )

                for i in range(losses):
                    strategy = strategies[i % len(strategies)]
                    trades.append(
                        {
                            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                            "symbol": "EURUSD",
                            "strategy": strategy,
                            "timeframe": "M15",
                            "entry": "1.0800",
                            "sl": "1.0750",
                            "tp": "1.0900",
                            "outcome": "LOSS",
                        }
                    )

                print(
                    f"[INFO] Généré {wins+losses} trades synthétiques pour le scoring."
                )

        except Exception as e:
            print(f"[ERREUR] Lecture de {pnl_history_path}: {e}")

    return trades


def write_signals_csv(trades, output_path="simulated_signals.csv"):
    """
    Écrit les trades au format CSV pour le scoring des stratégies.
    """
    if not trades:
        print("[ERREUR] Aucun trade à écrire dans le fichier CSV.")
        return False

    try:
        with open(output_path, "w", newline="") as csvfile:
            fieldnames = [
                "date",
                "symbol",
                "strategy",
                "timeframe",
                "entry",
                "sl",
                "tp",
                "outcome",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for trade in trades:
                writer.writerow(trade)

        print(f"[INFO] {len(trades)} trades écrits dans {output_path}")
        return True

    except Exception as e:
        print(f"[ERREUR] Écriture dans {output_path}: {e}")
        return False


def update_stats():
    """
    Fonction principale: charge les trades, génère le CSV, puis calcule les statistiques.
    """
    print("\n=== MISE À JOUR DES STATISTIQUES DE STRATÉGIES ===")

    # Charger l'historique des trades
    trades = load_trade_history()

    if not trades:
        print(
            "[AVERTISSEMENT] Aucun trade trouvé dans l'historique. Utilisation des données simulées existantes."
        )
        # Si aucun trade réel n'est trouvé, le scoring utilisera le fichier simulated_signals.csv existant
        if os.path.exists("simulated_signals.csv"):
            run_scoring()
            return True
        else:
            print("[ERREUR] Aucune donnée disponible pour le scoring des stratégies.")
            return False

    # Écrire le fichier simulated_signals.csv pour le scoring
    if write_signals_csv(trades):
        # Exécuter le scoring
        print("\n[INFO] Exécution du scoring des stratégies...")
        stats = run_scoring()
        print("[INFO] Statistiques mises à jour avec succès.")
        return True

    return False


def update_stats_if_needed(trade_count=None, min_trades=50):
    """
    Met à jour les statistiques si le nombre de trades dépasse un certain seuil.
    Utilisé pour les appels depuis main.py.

    Args:
        trade_count: Nombre de trades exécutés (si None, sera calculé à partir des fichiers)
        min_trades: Fréquence minimale de mise à jour (tous les X trades)

    Returns:
        bool: True si une mise à jour a été effectuée, False sinon
    """
    # Si le nombre de trades n'est pas spécifié, essayer de le calculer
    if trade_count is None:
        # Tenter de lire depuis pnl_history.json
        if os.path.exists("pnl_history.json"):
            with open("pnl_history.json", "r") as f:
                pnl_data = json.load(f)
            if pnl_data:
                latest = pnl_data[-1]
                trade_count = latest.get("winning_trades", 0) + latest.get(
                    "losing_trades", 0
                )

        # Si toujours pas de trade_count, vérifier le CSV
        if trade_count is None and os.path.exists("trade_log.csv"):
            with open("trade_log.csv", "r") as f:
                reader = csv.reader(f)
                # Soustraire 1 pour l'en-tête
                trade_count = sum(1 for _ in reader) - 1

    # Si aucun nombre de trades n'a pu être calculé, sortir
    if trade_count is None:
        print(
            "[INFO] Impossible de déterminer le nombre de trades, mise à jour des stats ignorée."
        )
        return False

    # Vérifier si une mise à jour est nécessaire
    if trade_count % min_trades == 0 and trade_count > 0:
        print(
            f"[INFO] {trade_count} trades enregistrés, mise à jour des statistiques..."
        )
        return update_stats()

    return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        # Mode de vérification automatique (pour intégration dans main.py)
        min_trades = 50
        if len(sys.argv) > 2:
            try:
                min_trades = int(sys.argv[2])
            except ValueError:
                pass

        update_stats_if_needed(min_trades=min_trades)
    else:
        # Mode manuel: force la mise à jour des statistiques
        update_stats()
