#!/usr/bin/env python3
"""
generate_trade_history.py
Script pour générer un historique de trades simulés afin de tester le système de scoring.
"""

import json
from datetime import datetime, timedelta
import random

# Générer 10 trades simulés
strategies = ["OB", "FVG", "Sweep", "BOS"]
results = ["WIN", "LOSS"]
timeframes = ["M15", "M5", "H1"]

trades = []
base_time = datetime(2025, 5, 10, 9, 0, 0)

# Distribution biaisée pour avoir des statistiques intéressantes
# OB: bon winrate (70%)
# FVG: mauvais winrate (30%)
# Sweep: moyen winrate (50%)
# BOS: moyen winrate (50%)
strategy_bias = {
    "OB": 0.7,  # 70% de chance de gagner
    "FVG": 0.3,  # 30% de chance de gagner
    "Sweep": 0.5,  # 50% de chance de gagner
    "BOS": 0.5,  # 50% de chance de gagner
}

# Générer 20 trades (pour avoir assez de données)
for i in range(20):
    strategy = random.choice(strategies)
    # Déterminer le résultat selon le biais de la stratégie
    win_chance = strategy_bias[strategy]
    result = "WIN" if random.random() < win_chance else "LOSS"

    tf = random.choice(timeframes)
    entry = round(random.uniform(1.0800, 1.0900), 4)

    # Pour des trades plus réalistes
    sl_distance = round(random.uniform(0.0030, 0.0070), 4)
    tp_distance = round(random.uniform(0.0060, 0.0100), 4)

    sl = round(entry - sl_distance, 4) if "BUY" else round(entry + sl_distance, 4)
    tp = round(entry + tp_distance, 4) if "BUY" else round(entry - tp_distance, 4)

    exit_price = tp if result == "WIN" else sl

    # Calcul du gain en pips
    gain_pips = round((abs(exit_price - entry) * 10000), 1)
    gain = gain_pips if result == "WIN" else -gain_pips

    trade = {
        "timestamp": (base_time + timedelta(hours=i * 3)).isoformat(),
        "symbol": "EURUSD",
        "strategy": strategy,
        "timeframe": tf,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "exit_price": exit_price,
        "result": result,
        "gain": gain,
    }
    trades.append(trade)

# Sauvegarder dans le fichier d'historique de trades
file_path = "trade_history.json"
with open(file_path, "w") as f:
    json.dump(trades, f, indent=2)

print(f"Généré {len(trades)} trades simulés dans {file_path}")
print("Distribution des stratégies:")
for strategy in strategies:
    win_count = sum(
        1 for t in trades if t["strategy"] == strategy and t["result"] == "WIN"
    )
    loss_count = sum(
        1 for t in trades if t["strategy"] == strategy and t["result"] == "LOSS"
    )
    total = win_count + loss_count
    winrate = (win_count / total * 100) if total > 0 else 0
    print(f"  {strategy}: {win_count}/{total} trades gagnants ({winrate:.1f}%)")

# Aussi mettre à jour trade_log.csv pour compatibilité
with open("trade_log.csv", "w", newline="") as f:
    import csv

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
    for trade in trades:
        writer.writerow(
            [
                trade["timestamp"],
                trade["symbol"],
                trade["strategy"],
                trade["timeframe"],
                trade["entry"],
                trade["sl"],
                trade["tp"],
                trade["exit_price"],
                trade["result"],
                trade["gain"],
            ]
        )

print("Mis à jour trade_log.csv avec les mêmes données")
