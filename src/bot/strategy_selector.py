"""
strategy_selector.py
Module de sélection de stratégie.
Analyse les inputs du LLM et active la logique de trading correspondante (FVG only, OB+Sweep, ICT scalping, BOS only, etc.).
Filtre également les signaux en fonction des biais macroéconomiques et des périodes de gel.
"""

import os
import logging
from structure_detector import StructureDetector
from macro_bias_manager import MacroBiasManager
from pnl_tracker import PnLTracker

logger = logging.getLogger("StrategySelector")


class StrategySelector:
    def __init__(
        self,
        llm,
        macro_bias_manager=None,
        freeze_before_minutes=30,
        freeze_after_minutes=10,
    ):
        self.llm = llm
        self.detector = StructureDetector()

        # Utiliser le macro_bias_manager fourni ou en créer un nouveau
        if macro_bias_manager is not None:
            self.bias_manager = macro_bias_manager
            if freeze_before_minutes != 30 or freeze_after_minutes != 10:
                logger.warning(
                    "Les paramètres freeze_before_minutes et freeze_after_minutes sont ignorés lorsqu'un macro_bias_manager est fourni"
                )
        else:
            self.bias_manager = MacroBiasManager(
                freeze_minutes_before=freeze_before_minutes,
                freeze_minutes_after=freeze_after_minutes,
            )

        # Configuration du logging
        self.debug_mode = os.environ.get("DEBUG_LLM", "False").lower() == "true"
        if self.debug_mode:
            logger.setLevel(logging.DEBUG)

    def update_macro_biases(self, currency_biases):
        """Met à jour les biais de devises basés sur l'analyse macro LLM"""
        self.bias_manager.update_currency_biases(currency_biases)
        if self.debug_mode:
            logger.debug(f"Biais macro mis à jour: {currency_biases}")

    def update_freeze_periods(self):
        """Met à jour les périodes de gel en fonction des événements macro à venir"""
        self.bias_manager.update_freeze_periods()

    def route_strategy(self, strategy_input):
        """
        Route la stratégie vers le bon détecteur et filtre les signaux
        selon les biais et périodes de gel.

        Args:
            strategy_input: Peut être une chaîne de caractères (nom de stratégie)
                           ou un tuple (stratégie complète, nom, biais)

        Returns:
            list: Signaux filtrés en fonction des biais macro et périodes de gel
        """
        # Détecter si on a reçu un tuple structure (stratégie, nom, biais)
        currency_biases = {}
        if isinstance(strategy_input, tuple) and len(strategy_input) >= 3:
            _, strategy_name, currency_biases = strategy_input
        else:
            strategy_name = strategy_input

        # Mettre à jour les biais si présents
        if currency_biases:
            self.update_macro_biases(currency_biases)

        # Mettre à jour les périodes de gel
        self.update_freeze_periods()

        # Obtenir les signaux en fonction de la stratégie
        signals = []
        strategy_lower = strategy_name.lower() if isinstance(strategy_name, str) else ""

        if "rest" in strategy_lower or "march" in strategy_lower:
            # Stratégie de repos - pas de trading
            if self.debug_mode:
                logger.debug("Stratégie de repos sélectionnée - aucun signal généré")
            return []

        # Route vers le bon détecteur en fonction de la stratégie
        if "fvg" in strategy_lower:
            signals = self.detector.detect_fvg()
        elif "ob" in strategy_lower:
            signals = self.detector.detect_ob()
        elif "bos" in strategy_lower:
            signals = self.detector.detect_bos()
        elif "sweep" in strategy_lower:
            signals = self.detector.detect_sweep()
        else:
            # Stratégie non reconnue ou composite, on utilise tous les détecteurs
            signals = (
                self.detector.detect_fvg()
                + self.detector.detect_ob()
                + self.detector.detect_bos()
                + self.detector.detect_sweep()
            )

        # Filtrer les signaux selon les biais et périodes de gel
        filtered_signals = self.bias_manager.filter_signals_by_bias_and_freeze(signals)

        if self.debug_mode:
            original_count = len(signals)
            filtered_count = len(filtered_signals)
            if original_count != filtered_count:
                logger.debug(
                    f"Filtrage macro: {original_count} signaux détectés -> {filtered_count} signaux validés"
                )

        return filtered_signals

    def should_trade_from_llm(self, llm_response: dict):
        """
        Valide une recommandation de trading structurée provenant du LLM

        Args:
            llm_response (dict): Réponse structurée du LLM avec des champs comme symbol, action, strategy, etc.

        Returns:
            dict or None: Un objet de signal validé prêt à être transmis à OrderManager.place_trade(), ou None si invalide
        """
        # Validation des champs requis
        required_fields = ["symbol", "action", "strategy"]
        for field in required_fields:
            if field not in llm_response or not llm_response[field]:
                logger.warning(f"[LLM Validation] Champ requis manquant: {field}")
                return None

        # Normalisation du symbole
        symbol = llm_response["symbol"].replace("/", "").upper()
        action = llm_response["action"].upper()

        # Validation de l'action (BUY ou SELL seulement)
        if action not in ["BUY", "SELL"]:
            logger.warning(
                f"[LLM Validation] Action invalide: {action} (doit être BUY ou SELL)"
            )
            return None

        # Conversion de l'action en direction pour le signal
        side = "LONG" if action == "BUY" else "SHORT"

        # Récupérer la stratégie et la raison
        strategy = llm_response.get("strategy", "LLM_AUTO")
        reason = llm_response.get("reason", "Recommandation LLM automatique")
        confidence = float(
            llm_response.get("confidence", 0.75)
        )  # Valeur par défaut si non fournie

        # Vérifier la confiance minimale requise (configurable)
        min_confidence = 0.7  # À déplacer dans la config plus tard
        if confidence < min_confidence:
            logger.warning(
                f"[LLM Validation] Confiance trop basse: {confidence} (min requis: {min_confidence})"
            )
            return None

        # Vérifier les biais macroéconomiques si disponibles
        currency_pairs = [c for c in symbol if c.isalpha()]
        currency_1, currency_2 = symbol[:3], symbol[3:]

        # Vérifier la cohérence avec les biais macro
        current_biases = self.bias_manager.get_currency_biases()

        # Si on a des biais et qu'ils contredisent l'ordre, on peut bloquer ou réduire la confiance
        if current_biases:
            c1_bias = current_biases.get(currency_1, "neutral")
            c2_bias = current_biases.get(currency_2, "neutral")

            # Convertir les biais textuels en indicateurs numériques
            def bias_to_numeric(bias_str):
                if not bias_str:
                    return 0
                bias_str = bias_str.lower()
                if "bull" in bias_str:
                    return 1
                elif "bear" in bias_str:
                    return -1
                else:
                    return 0

            c1_numeric = bias_to_numeric(c1_bias)
            c2_numeric = bias_to_numeric(c2_bias)

            # Si on veut acheter EUR/USD mais EUR est bearish et USD bullish, c'est contradictoire
            if side == "LONG" and c1_numeric < 0 and c2_numeric > 0:
                logger.warning(
                    f"[LLM Validation] Ordre contredit par les biais macro: {currency_1}({c1_bias}) vs {currency_2}({c2_bias})"
                )
                return None
            # Si on veut vendre EUR/USD mais EUR est bullish et USD bearish, c'est contradictoire
            elif side == "SHORT" and c1_numeric > 0 and c2_numeric < 0:
                logger.warning(
                    f"[LLM Validation] Ordre contredit par les biais macro: {currency_1}({c1_bias}) vs {currency_2}({c2_bias})"
                )
                return None

        # Vérifier les périodes de gel
        frozen, end_time = self.bias_manager.is_frozen(currency_1)
        if frozen:
            logger.warning(
                f"[LLM Validation] Ordre rejeté - période de gel pour {currency_1} jusqu'à {end_time}"
            )
            return None

        frozen, end_time = self.bias_manager.is_frozen(currency_2)
        if frozen:
            logger.warning(
                f"[LLM Validation] Ordre rejeté - période de gel pour {currency_2} jusqu'à {end_time}"
            )
            return None

        # Créer un signal standard comme attendu par place_trade
        # À adapter selon les paramètres attendus par votre OrderManager
        current_price = 0.0  # À remplacer par le prix réel du marché

        # Structure du signal compatible avec place_trade
        signal = {
            "symbol": symbol,
            "side": side,
            "type": strategy,
            "timeframe": "LLM",  # Pas de timeframe spécifique pour les suggestions LLM
            "entry": current_price,  # Prix actuel, à remplacer par le prix réel
            "sl": 0.0,  # À calculer selon votre logique de risk management
            "tp": 0.0,  # À calculer selon votre logique de risk management
            "sizing": 0.01,  # Taille par défaut, à ajuster selon votre risk management
            "reason": reason,
            "confidence": confidence,
            "source": "LLM",
        }

        # Log de la décision
        logger.info(
            f"[LLM Trade] Signal validé: {symbol} {side} via {strategy} (confiance: {confidence})"
        )

        return signal
