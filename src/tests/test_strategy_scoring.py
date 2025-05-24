import csv
import json

"""
Module de scoring des stratégies ICT/SMC
Calcule les statistiques de performance par stratégie
"""


def compute_pnl(entry, sl, tp, outcome):
    """Calcule le gain/perte en points pour un trade."""
    entry, sl, tp = float(entry), float(sl), float(tp)
    if outcome == "WIN":
        return abs(tp - entry) * 10000  # Convertir en pips
    else:
        return -abs(entry - sl) * 10000  # Valeur négative pour les pertes


def calculate_max_drawdown(equity_curve):
    """Calcule le drawdown maximum à partir d'une courbe d'équité."""
    max_dd = 0
    peak = equity_curve[0] if equity_curve else 0
    for point in equity_curve:
        if point > peak:
            peak = point
        dd = peak - point
        if dd > max_dd:
            max_dd = dd
    return max_dd


def calculate_gain_loss_ratio(win_values, loss_values):
    """Calcule le ratio gain/perte moyen."""
    if not win_values or not loss_values:
        return 0
    avg_win = sum(win_values) / len(win_values) if win_values else 0
    avg_loss = (
        abs(sum(loss_values) / len(loss_values)) if loss_values else 1
    )  # Éviter division par zéro
    return round(avg_win / avg_loss, 2) if avg_loss else 0


def main(input_csv="simulated_signals.csv"):
    """Fonction principale pour scorer les stratégies."""
    # Structure de données pour les stats par stratégie
    stats_by_strategy = {}

    # Lecture du CSV des signaux
    with open(input_csv, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            strategy = row["strategy"]
            outcome = row["outcome"]
            pnl = compute_pnl(row["entry"], row["sl"], row["tp"], outcome)

            # Initialiser la structure pour cette stratégie si nécessaire
            if strategy not in stats_by_strategy:
                stats_by_strategy[strategy] = {
                    "trades_count": 0,
                    "wins_count": 0,
                    "losses_count": 0,
                    "win_values": [],  # Liste des gains en pips/points
                    "loss_values": [],  # Liste des pertes en pips/points
                    "pnl_total": 0,
                    "equity_curve": [],
                    "winrate": 0,
                    "avg_gain": 0,
                    "gain_loss_ratio": 0,
                    "max_drawdown": 0,
                }

            # Référence plus courte
            stats = stats_by_strategy[strategy]

            # Mettre à jour les compteurs
            stats["trades_count"] += 1

            # Ajouter le gain/perte à la liste appropriée
            if outcome == "WIN":
                stats["wins_count"] += 1
                stats["win_values"].append(pnl)
            else:  # LOSS
                stats["losses_count"] += 1
                stats["loss_values"].append(pnl)

            # PnL total et courbe d'équité
            stats["pnl_total"] += pnl
            stats["equity_curve"].append(stats["pnl_total"])

    # Calculs finaux pour chaque stratégie
    for strategy, stats in stats_by_strategy.items():
        # Pourcentage de réussite
        if stats["trades_count"] > 0:
            stats["winrate"] = round(
                100 * stats["wins_count"] / stats["trades_count"], 1
            )

        # Gain moyen par trade
        if stats["trades_count"] > 0:
            total_pnl = sum(stats["win_values"]) + sum(stats["loss_values"])
            stats["avg_gain"] = round(total_pnl / stats["trades_count"], 2)

        # Ratio gain/perte
        stats["gain_loss_ratio"] = calculate_gain_loss_ratio(
            stats["win_values"], stats["loss_values"]
        )

        # Drawdown maximum
        stats["max_drawdown"] = round(calculate_max_drawdown(stats["equity_curve"]), 2)

        # Nettoyer les données temporaires avant export
        cleaned_stats = {
            "trades": stats["trades_count"],
            "wins": stats["wins_count"],
            "losses": stats["losses_count"],
            "winrate": stats["winrate"],
            "avg_gain": stats["avg_gain"],
            "pnl_total": stats["pnl_total"],
            "gain_loss_ratio": stats["gain_loss_ratio"],
            "max_drawdown": stats["max_drawdown"],
        }

        # Remplacer les stats complètes par les stats nettoyées
        stats_by_strategy[strategy] = cleaned_stats

    # Export CSV
    with open("strategy_stats.csv", "w", newline="") as csvfile:
        fieldnames = [
            "strategy",
            "trades",
            "wins",
            "losses",
            "winrate",
            "avg_gain",
            "pnl_total",
            "gain_loss_ratio",
            "max_drawdown",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for strategy, stats in stats_by_strategy.items():
            row = {"strategy": strategy}
            row.update(stats)
            writer.writerow(row)

    # Export JSON
    with open("strategy_stats.json", "w") as f:
        json.dump(stats_by_strategy, f, indent=2)

    # Optionnel : bar chart matplotlib
    try:
        import matplotlib.pyplot as plt

        # Préparation des données
        strategies = list(stats_by_strategy.keys())
        winrates = [stats["winrate"] for stats in stats_by_strategy.values()]
        avg_gains = [stats["avg_gain"] for stats in stats_by_strategy.values()]

        # Création du graphique
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

        # Graphique des winrates
        bars1 = ax1.bar(strategies, winrates, color="skyblue")
        ax1.set_ylabel("Winrate (%)")
        ax1.set_title("Performance par stratégie")
        ax1.set_ylim(0, 100)  # Winrate de 0% à 100%

        # Ajouter les valeurs sur les barres
        for bar in bars1:
            height = bar.get_height()
            ax1.annotate(
                f"{height}%",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),  # 3 points de décalage vertical
                textcoords="offset points",
                ha="center",
                va="bottom",
            )

        # Graphique des gains moyens
        bars2 = ax2.bar(strategies, avg_gains, color="lightgreen")
        ax2.set_ylabel("Gain moyen (pips)")
        ax2.set_xlabel("Stratégie")

        # Ajouter les valeurs sur les barres
        for bar in bars2:
            height = bar.get_height()
            color = "green" if height >= 0 else "red"
            ax2.annotate(
                f"{height}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3 if height >= 0 else -15),
                textcoords="offset points",
                ha="center",
                va="bottom",
                color=color,
            )

        plt.tight_layout()
        plt.savefig("strategy_stats.png")
        plt.close()
        print("Graphique généré : strategy_stats.png")
    except Exception as e:
        print("Erreur lors de la génération du graphique:", e)

    print("Scoring terminé. Résultats : strategy_stats.csv, strategy_stats.json")
    return stats_by_strategy


if __name__ == "__main__":
    main()
