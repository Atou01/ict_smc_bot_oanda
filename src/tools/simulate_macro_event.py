#!/usr/bin/env python
"""
simulate_macro_event.py
Script pour simuler un événement macroéconomique important et tester le système de gel.
Ce script crée un événement fictif avec impact High ou Medium et l'insère dans
le fichier macro_log.json pour tester la réaction du système.
"""

import os
import json
import argparse
import datetime
import logging
import sys

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("SimulateMacroEvent")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOGS_DIR = os.path.normpath(os.path.join(BASE_DIR, "logs"))
MACRO_LOG_PATH = os.path.join(LOGS_DIR, "macro_log.json")


def add_simulated_event(currency, impact="High", minutes_from_now=15, title=None):
    """
    Ajoute un événement macroéconomique simulé dans le fichier macro_log.json

    Args:
        currency (str): Code de la devise (USD, EUR, GBP, etc.)
        impact (str): Niveau d'impact (High, Medium)
        minutes_from_now (int): Nombre de minutes avant l'événement
        title (str): Titre de l'événement (optionnel)
    """
    try:
        # Vérifier que le dossier logs existe
        os.makedirs(LOGS_DIR, exist_ok=True)

        # Charger le fichier macro_log.json s'il existe
        macro_data = {
            "recent_events": [],
            "timestamp": datetime.datetime.now().isoformat(),
        }
        if os.path.exists(MACRO_LOG_PATH):
            try:
                with open(MACRO_LOG_PATH, "r") as f:
                    loaded_data = json.load(f)
                    # S'assurer que 'recent_events' existe
                    if "recent_events" not in loaded_data:
                        loaded_data["recent_events"] = []
                    if "timestamp" not in loaded_data:
                        loaded_data["timestamp"] = datetime.datetime.now().isoformat()
                    macro_data = loaded_data
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(
                    f"Fichier {MACRO_LOG_PATH} corrompu: {e}. Création d'un nouveau fichier."
                )

        # Générer un événement fictif
        now = datetime.datetime.now()
        event_time = now + datetime.timedelta(minutes=minutes_from_now)

        # Formatage de la date au format MM-DD-YYYY
        date_str = event_time.strftime("%m-%d-%Y")

        # Formatage de l'heure au format HH:MMam/pm
        time_str = event_time.strftime("%I:%M%p").lower()

        # Titre par défaut si non spécifié
        if not title:
            if impact == "High":
                title = f"{currency} Consumer Price Index (CPI)"
            elif currency in ["EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]:
                title = f"{currency} Interest Rate Decision"
            else:
                title = f"{currency} Economic Announcement"

        # Créer l'événement
        event = {
            "title": title,
            "country": currency,
            "date": date_str,
            "time": time_str,
            "impact": impact,
            "forecast": "N/A",
            "previous": "N/A",
            "timestamp": event_time.isoformat(),
            "simulated": True,  # Marquer comme un événement simulé
        }

        # Ajouter l'événement à la liste
        macro_data["recent_events"].insert(0, event)
        macro_data["timestamp"] = datetime.datetime.now().isoformat()

        # Sauvegarder le fichier
        with open(MACRO_LOG_PATH, "w") as f:
            json.dump(macro_data, f, indent=2)

        logger.info(
            f"Événement simulé ajouté: {currency} {impact} impact dans {minutes_from_now} minutes"
        )
        logger.info(f"Titre: {title}")
        logger.info(f"Date/heure: {date_str} {time_str}")
        logger.info(
            f"Le système devrait geler le trading sur {currency} environ {minutes_from_now-30} minutes avant l'événement"
        )

        return True
    except Exception as e:
        logger.error(f"Erreur lors de la simulation de l'événement: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Simuler un événement macroéconomique pour tester le système de gel"
    )
    parser.add_argument("currency", type=str, help="Code devise (USD, EUR, GBP, etc.)")
    parser.add_argument(
        "--impact",
        "-i",
        type=str,
        choices=["High", "Medium"],
        default="High",
        help="Niveau d'impact (High, Medium)",
    )
    parser.add_argument(
        "--minutes", "-m", type=int, default=15, help="Minutes avant l'événement"
    )
    parser.add_argument(
        "--title", "-t", type=str, default=None, help="Titre de l'événement (optionnel)"
    )

    args = parser.parse_args()

    # Validation de la devise (3 lettres majuscules)
    if (
        len(args.currency) != 3
        or not args.currency.isalpha()
        or not args.currency.isupper()
    ):
        logger.error(
            "La devise doit être un code de 3 lettres majuscules (USD, EUR, GBP, etc.)"
        )
        sys.exit(1)

    # Ajouter l'événement simulé
    if add_simulated_event(args.currency, args.impact, args.minutes, args.title):
        print(
            f"\n✅ Événement {args.impact} impact pour {args.currency} ajouté avec succès!"
        )
        print(f"⏰ L'événement aura lieu dans {args.minutes} minutes")
        print(
            f"🔒 Le système devrait automatiquement geler le trading sur {args.currency}"
        )
        print(f"   environ {max(0, args.minutes-30)} minutes avant l'événement\n")
        print("💡 Pour vérifier, exécutez le bot avec:")
        print("   DEBUG_LLM=True PYTHONPATH=src python src/bot/main.py\n")
        print("🔍 Puis ouvrez le dashboard pour voir les périodes de gel actives\n")
    else:
        print("❌ Échec de la simulation. Voir les logs pour plus de détails.")
        sys.exit(1)


if __name__ == "__main__":
    main()
