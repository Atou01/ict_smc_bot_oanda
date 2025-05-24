"""
structure_detector.py
Module de détection des structures de marché ICT/SMC (BOS, FVG, OB, Sweep, EQH/EQL).
Fonctionne en multi-timeframe avec validation de structure et indices de confiance.
"""

import datetime
import logging

# Configuration du logging pour les signaux rejetés
logging.basicConfig(
    level=logging.INFO,
    filename="rejected_signals.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class StructureDetector:
    def __init__(self, data=None):
        self.data = data  # données OHLCV (optionnel pour la simulation)
        self.trend_bias = {}  # bias de tendance par timeframe
        self.last_bos = {"H4": None, "H1": None, "M15": None, "M5": None, "M1": None}
        self.last_sweep = {}
        self.timeframes = ["H4", "H1", "M15", "M5", "M1"]
        self.rejected_signals = []

    def _get_higher_timeframe(self, timeframe):
        """Retourne le timeframe supérieur."""
        tf_index = self.timeframes.index(timeframe)
        if tf_index > 0:
            return self.timeframes[tf_index - 1]
        return timeframe  # déjà au plus haut

    def _get_trend_bias(self, timeframe):
        """Retourne le biais de tendance pour un timeframe donné (simulé)."""
        if timeframe not in self.trend_bias:
            # Simulation: Tendance haussier pour H4 et H1, baissier pour M15 et M5, neutre pour M1
            if timeframe in ["H4", "H1"]:
                self.trend_bias[timeframe] = "LONG"
            elif timeframe in ["M15", "M5"]:
                self.trend_bias[timeframe] = "SHORT"
            else:
                self.trend_bias[timeframe] = "NEUTRAL"
        return self.trend_bias[timeframe]

    def _align_with_higher_tf(self, signal):
        """Vérifie si le signal est aligné avec le timeframe supérieur."""
        current_tf = signal["timeframe"]
        higher_tf = self._get_higher_timeframe(current_tf)
        higher_bias = self._get_trend_bias(higher_tf)

        if higher_bias == "NEUTRAL":
            return True  # neutral bias, alignment not important

        return signal["side"] == higher_bias

    def _validate_signal(self, signal):
        """Valide un signal selon des critères de confiance."""
        signal_type = signal["type"]
        timeframe = signal["timeframe"]
        side = signal["side"]
        confidence = "moyenne"  # confiance par défaut
        valid = True
        reject_reason = None

        # Vérification d'alignement avec un timeframe supérieur
        aligned_with_higher_tf = self._align_with_higher_tf(signal)

        # Règles spécifiques par type de structure
        if signal_type == "FVG":
            # Un FVG est plus fiable s'il est précédé d'un BOS dans la même direction
            if self.last_bos.get(timeframe) == side:
                confidence = "forte"
            elif not aligned_with_higher_tf:
                confidence = "faible"
                if (
                    self._get_trend_bias(timeframe) != "NEUTRAL"
                    and self._get_trend_bias(timeframe) != side
                ):
                    valid = False
                    reject_reason = f"FVG {side} non aligné avec tendance {self._get_trend_bias(timeframe)} sur {timeframe}"

        elif signal_type == "OB":
            # Un OB est plus fiable s'il est accompagné d'un Sweep récent
            if self.last_sweep.get(timeframe) == side:
                confidence = "forte"
            elif not aligned_with_higher_tf:
                confidence = "faible"

        elif signal_type == "BOS":
            # Un BOS est valide s'il est aligné avec le biais du timeframe supérieur
            if aligned_with_higher_tf:
                confidence = "forte"
            else:
                confidence = "faible"
                higher_tf = self._get_higher_timeframe(timeframe)
                if (
                    self._get_trend_bias(higher_tf) != "NEUTRAL"
                    and self._get_trend_bias(higher_tf) != side
                ):
                    valid = False
                    reject_reason = f"BOS {side} contredit tendance {self._get_trend_bias(higher_tf)} sur {higher_tf}"

        elif signal_type == "Sweep":
            # Un Sweep est plus fiable s'il se produit à proximité d'un OB
            if aligned_with_higher_tf:
                confidence = "forte"
            else:
                confidence = "faible"

        # Stocker les informations de confiance et validité
        signal["confidence"] = confidence
        signal["valid"] = valid

        # Loguer les signaux rejetés
        if not valid:
            signal_copy = signal.copy()
            signal_copy["reject_reason"] = reject_reason
            signal_copy["timestamp"] = datetime.datetime.now().isoformat()
            self.rejected_signals.append(signal_copy)
            logging.info(f"Signal rejeté: {signal_copy}")

        return valid, confidence

    def _update_structure_history(self, signals):
        """Met à jour l'historique des structures détectées."""
        for signal in signals:
            if signal.get("valid", True):
                tf = signal["timeframe"]
                if signal["type"] == "BOS":
                    self.last_bos[tf] = signal["side"]
                elif signal["type"] == "Sweep":
                    self.last_sweep[tf] = signal["side"]

    def detect_fvg(self):
        """Détecte les Fair Value Gaps."""
        # Simule la détection d'un FVG
        signals = [
            {
                "type": "FVG",
                "side": "LONG",
                "timeframe": "M15",
                "entry": 1.083,
                "sl": 1.078,
                "tp": 1.093,
                "sizing": "1% capital",
            }
        ]

        # Validation des signaux
        valid_signals = []
        for signal in signals:
            valid, confidence = self._validate_signal(signal)
            if valid:
                valid_signals.append(signal)

        self._update_structure_history(valid_signals)
        return valid_signals

    def detect_ob(self):
        """Détecte les Order Blocks."""
        # Simule la détection d'un OB
        signals = [
            {
                "type": "OB",
                "side": "LONG",
                "timeframe": "M15",
                "entry": 1.0835,
                "sl": 1.0785,
                "tp": 1.0935,
                "sizing": "1% capital",
            }
        ]

        # Validation des signaux
        valid_signals = []
        for signal in signals:
            valid, confidence = self._validate_signal(signal)
            if valid:
                valid_signals.append(signal)

        self._update_structure_history(valid_signals)
        return valid_signals

    def detect_bos(self):
        """Détecte les Break of Structure."""
        # Simule la détection d'un BOS
        signals = [
            {
                "type": "BOS",
                "side": "LONG",
                "timeframe": "H1",
                "entry": 1.084,
                "sl": 1.079,
                "tp": 1.094,
                "sizing": "1% capital",
            }
        ]

        # Validation des signaux
        valid_signals = []
        for signal in signals:
            valid, confidence = self._validate_signal(signal)
            if valid:
                valid_signals.append(signal)

        self._update_structure_history(valid_signals)
        return valid_signals

    def detect_sweep(self):
        """Détecte les Sweeps (liquidity sweeps)."""
        # Simule la détection d'un Sweep
        signals = [
            {
                "type": "Sweep",
                "side": "LONG",
                "timeframe": "M5",
                "entry": 1.0825,
                "sl": 1.0775,
                "tp": 1.0925,
                "sizing": "1% capital",
            }
        ]

        # Validation des signaux
        valid_signals = []
        for signal in signals:
            valid, confidence = self._validate_signal(signal)
            if valid:
                valid_signals.append(signal)

        self._update_structure_history(valid_signals)
        return valid_signals

    def get_rejected_signals(self):
        """Retourne les signaux qui ont été rejetés par la validation."""
        return self.rejected_signals
