"""
macro_bias_manager.py
Module de gestion des biais macroéconomiques et des périodes de gel de trading.
Filtre les signaux techniques en fonction des biais identifiés par le LLM et gère
les périodes d'inactivité avant/après des événements économiques importants.
"""

import json
import os
import datetime
import logging
from typing import Dict, List, Optional, Tuple, Any

# Configuration du logging
logger = logging.getLogger("MacroBiasManager")


class MacroBiasManager:
    """Gère les biais macroéconomiques et les périodes de gel de trading"""

    def __init__(self, freeze_minutes_before=30, freeze_minutes_after=10):
        """
        Initialise le gestionnaire de biais macroéconomiques.

        Args:
            freeze_minutes_before (int): Minutes de gel avant un événement important
            freeze_minutes_after (int): Minutes de gel après un événement important
        """
        self.freeze_minutes_before = freeze_minutes_before
        self.freeze_minutes_after = freeze_minutes_after
        self.currency_biases = {}  # {"USD": "bearish", "EUR": "bullish", ...}
        self.freeze_periods = {}  # {"GBP": [(start_time, end_time), ...], ...}

        # Statistiques de filtrage
        self.filter_stats = {
            "accepted": 0,  # Signaux acceptés par le filtre macro
            "filtered": 0,  # Signaux rejetés par le filtre macro
            "filtered_by_bias": 0,  # Rejetés en raison du biais
            "filtered_by_freeze": 0,  # Rejetés en raison d'une période de gel
        }

        # Chemins des fichiers
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logs_dir = os.path.normpath(os.path.join(base_dir, "../../logs"))
        self.bias_file = os.path.join(logs_dir, "macro_bias.json")
        self.macro_log_file = os.path.join(logs_dir, "macro_log.json")
        self.shared_state_path = os.path.join(logs_dir, "shared_state.json")

        # Charger l'état initial s'il existe
        self.load_biases()
        self.update_freeze_periods()

    def load_biases(self) -> None:
        """Charge les biais de devises depuis le fichier macro_bias.json"""
        try:
            if os.path.exists(self.bias_file):
                with open(self.bias_file, "r") as f:
                    data = json.load(f)
                    self.currency_biases = data.get("currency_biases", {})
                    logger.info(f"Biais chargés: {self.currency_biases}")
            else:
                logger.info("Aucun fichier de biais existant, création d'un nouveau.")
                self.save_biases()
        except Exception as e:
            logger.error(f"Erreur lors du chargement des biais: {e}")

    def save_biases(self) -> None:
        """Sauvegarde les biais de devises dans le fichier macro_bias.json"""
        try:
            with open(self.bias_file, "w") as f:
                json.dump(
                    {
                        "currency_biases": self.currency_biases,
                        "last_update": datetime.datetime.now().isoformat(),
                    },
                    f,
                    indent=2,
                )

            # Mise à jour du shared_state pour le dashboard
            self.update_shared_state()
            logger.info(f"Biais sauvegardés: {self.currency_biases}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des biais: {e}")

    def update_shared_state(self) -> None:
        """Met à jour shared_state.json avec les informations de biais et statistiques"""
        try:
            if os.path.exists(self.shared_state_path):
                with open(self.shared_state_path, "r") as f:
                    shared_state = json.load(f)
            else:
                shared_state = {}

            # Ajouter les biais et périodes de gel au shared_state
            shared_state["macro_biases"] = self.currency_biases
            shared_state["freeze_periods"] = {
                currency: [
                    {"start": start.isoformat(), "end": end.isoformat()}
                    for start, end in periods
                ]
                for currency, periods in self.freeze_periods.items()
            }

            # Ajouter les statistiques de filtrage
            shared_state["macro_filter_stats"] = self.filter_stats

            with open(self.shared_state_path, "w") as f:
                json.dump(shared_state, f, indent=2)
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du shared_state: {e}")

    def update_currency_biases(self, biases: Dict[str, str]) -> None:
        """
        Met à jour les biais de devises à partir de l'analyse LLM.

        Args:
            biases (dict): Dictionnaire des biais par devise {"USD": "bearish", "EUR": "bullish", ...}
        """
        self.currency_biases.update(biases)
        self.save_biases()
        logger.info(f"Biais mis à jour: {self.currency_biases}")

    def get_currency_biases(self) -> Dict[str, str]:
        """Retourne le dictionnaire des biais de devises actuels."""
        return self.currency_biases

    def update_freeze_periods(self) -> None:
        """Met à jour les périodes de gel en fonction des événements macroéconomiques à venir"""
        try:
            if not os.path.exists(self.macro_log_file):
                logger.warning("Fichier de log macro non trouvé")
                return

            with open(self.macro_log_file, "r") as f:
                macro_data = json.load(f)

            now = datetime.datetime.now()
            self.freeze_periods = {}

            # Parcourir les événements macroéconomiques
            for event in macro_data.get("recent_events", []):
                impact = event.get("impact", "").lower()
                if impact not in ("high", "medium"):
                    continue

                country = event.get("country", "")
                if not country or len(country) != 3:  # Format USD, EUR, GBP, etc.
                    continue

                # Extraire la date/heure de l'événement
                event_time = None
                try:
                    if event.get("timestamp"):
                        event_time = datetime.datetime.fromisoformat(event["timestamp"])
                    elif event.get("date") and event.get("time"):
                        # Conversion approximative - selon le format utilisé dans macro_collector
                        date_str = event["date"]
                        time_str = event["time"]
                        # Hypothèse : format "MM-DD-YYYY HH:MM AM/PM"
                        date_parts = date_str.split("-")
                        if len(date_parts) == 3:
                            month, day, year = date_parts

                            # Parse time
                            is_pm = "pm" in time_str.lower()
                            time_clean = (
                                time_str.lower()
                                .replace("am", "")
                                .replace("pm", "")
                                .strip()
                            )
                            if ":" in time_clean:
                                hour, minute = time_clean.split(":")[:2]
                            else:
                                hour, minute = time_clean, "00"

                            hour = int(hour)
                            if is_pm and hour < 12:
                                hour += 12
                            elif not is_pm and hour == 12:
                                hour = 0

                            event_time = datetime.datetime(
                                int(year), int(month), int(day), hour, int(minute)
                            )
                except Exception as e:
                    logger.warning(f"Impossible de parser la date/heure: {e}")
                    continue

                if not event_time:
                    continue

                # Calculer la période de gel
                freeze_start = event_time - datetime.timedelta(
                    minutes=self.freeze_minutes_before
                )
                freeze_end = event_time + datetime.timedelta(
                    minutes=self.freeze_minutes_after
                )

                # Si l'événement est dans le futur et moins de 24h
                if now < freeze_end and (event_time - now).total_seconds() < 86400:
                    if country not in self.freeze_periods:
                        self.freeze_periods[country] = []
                    self.freeze_periods[country].append((freeze_start, freeze_end))
                    logger.info(
                        f"Période de gel ajoutée pour {country}: {freeze_start} à {freeze_end}"
                    )

            # Mise à jour du shared_state avec les stats de filtrage
            self.update_shared_state()
            logger.info(f"Périodes de gel mises à jour: {self.freeze_periods}")

        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des périodes de gel: {e}")

    def is_frozen(self, currency: str) -> Tuple[bool, Optional[datetime.datetime]]:
        """
        Vérifie si une devise est actuellement en période de gel.

        Args:
            currency (str): Code de la devise (USD, EUR, etc.)

        Returns:
            tuple: (est_en_gel, fin_du_gel) - si en gel, retourne aussi la fin du gel
        """
        now = datetime.datetime.now()

        # Si la devise n'a pas de périodes de gel
        if currency not in self.freeze_periods:
            return False, None

        # Vérifier chaque période de gel
        for start, end in self.freeze_periods[currency]:
            if start <= now <= end:
                return True, end

        return False, None

    def filter_signals_by_bias_and_freeze(
        self, signals: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filtre les signaux de trading en fonction des biais et périodes de gel.

        Args:
            signals (list): Liste des signaux de trading détectés

        Returns:
            list: Signaux filtrés selon les biais macro et périodes de gel
        """
        filtered_signals = []
        initial_count = len(signals)
        frozen_count = 0
        bias_count = 0

        for signal in signals:
            # Extraire les devises du symbole (ex: EURUSD -> EUR et USD)
            symbol = signal.get("symbol", "")
            if len(symbol) != 6:  # Format standard pour les paires de devises
                filtered_signals.append(signal)  # Conserver les signaux non-forex
                continue

            base_currency = symbol[:3]  # Première devise (EUR dans EURUSD)
            quote_currency = symbol[3:]  # Seconde devise (USD dans EURUSD)

            # Vérifier les périodes de gel
            base_frozen, _ = self.is_frozen(base_currency)
            quote_frozen, _ = self.is_frozen(quote_currency)

            if base_frozen or quote_frozen:
                logger.info(f"Signal ignoré (période de gel): {signal}")
                frozen_count += 1
                continue

            # Vérifier la cohérence avec les biais
            side = signal.get("side", "").lower()

            base_bias = self.currency_biases.get(base_currency, "").lower()
            quote_bias = self.currency_biases.get(quote_currency, "").lower()

            # Si pas de biais défini, on conserve le signal
            if not base_bias and not quote_bias:
                filtered_signals.append(signal)
                continue

            # Validation LONG: base bullish OU quote bearish
            if side == "long" and (base_bias == "bullish" or quote_bias == "bearish"):
                filtered_signals.append(signal)
                continue

            # Validation SHORT: base bearish OU quote bullish
            if side == "short" and (base_bias == "bearish" or quote_bias == "bullish"):
                filtered_signals.append(signal)
                continue

            # Si le signal ne correspond pas aux biais, on l'ignore
            logger.info(f"Signal ignoré (biais macro incompatible): {signal}")
            bias_count += 1

        # Mettre à jour les statistiques de filtrage
        self.filter_stats["accepted"] += len(filtered_signals)
        self.filter_stats["filtered"] += initial_count - len(filtered_signals)
        self.filter_stats["filtered_by_freeze"] += frozen_count
        self.filter_stats["filtered_by_bias"] += bias_count

        # Mettre à jour le shared_state avec les nouvelles statistiques
        self.update_shared_state()

        # Log des statistiques
        if initial_count > 0:
            logger.info(
                f"Statistiques de filtrage: {len(filtered_signals)}/{initial_count} signaux acceptés "
                f"({frozen_count} gelés, {bias_count} biais incompatibles)"
            )

        return filtered_signals
