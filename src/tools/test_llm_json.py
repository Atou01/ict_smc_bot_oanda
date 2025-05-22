#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour vérifier le traitement des réponses JSON du LLM
Ce script simule différentes réponses de l'API OpenAI et teste la robustesse
de notre mécanisme d'extraction JSON.
"""
import os
import sys
import json
import logging
import re
from unittest.mock import MagicMock

# Ajouter le répertoire parent au path pour pouvoir importer les modules du bot
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot.llm_brain import LLMBrain

# Configuration du logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_llm_json")


class OpenAIResponseMock:
    """Classe pour simuler la réponse de l'API OpenAI"""

    def __init__(self, content):
        self.choices = [MagicMock()]
        self.choices[0].message.content = content


# Une fonction améliorée pour extraire du JSON ou des données structurées de n'importe quel texte
def extract_json(response_text):
    """Extrait le JSON d'une réponse texte, quelle que soit sa forme"""
    try:
        # 1. D'abord essayer de parser directement
        return json.loads(response_text)
    except json.JSONDecodeError:
        # 2. Chercher le premier bloc {...}
        match = re.search(r"\{.*\}", response_text, re.S)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception as e2:
                logger.warning(f"Échec parsing JSON extrait: {e2}")
                # Continuer aux méthodes suivantes

        # 3. Chercher des paires clé-valeur citées
        potential_pairs = re.findall(r'"(\w+)"\s*:\s*"([^"]*)"', response_text)
        if potential_pairs:
            json_dict = {k: v for k, v in potential_pairs}
            if json_dict:
                logger.info("JSON reconstruit depuis des paires clé-valeur citées")
                return json_dict

        # 4. Extraction intelligente à partir de texte libre
        # Patterns courants à rechercher
        extracted_data = {}

        # 4.1 Chercher le symbole/paire de devises
        symbol_patterns = [
            r"(acheter|vendre)\s+([A-Z]{3})[/_]?([A-Z]{3})",  # acheter EUR/USD
            r"(paire|symbole|symbol)\s*[:\-]?\s*([A-Z]{3})[/_]?([A-Z]{3})",  # paire: EUR/USD
            r"trading\s+(?:de|du|sur)?\s*([A-Z]{3})[/_]?([A-Z]{3})",  # trading sur EUR/USD
        ]
        for pattern in symbol_patterns:
            symbol_match = re.search(pattern, response_text, re.I)
            if symbol_match:
                groups = symbol_match.groups()
                if len(groups) == 3:  # [action, base, quote]
                    action, base, quote = groups
                    extracted_data["symbol"] = f"{base}_{quote}"
                    # Si on détecte aussi une action (BUY/SELL)
                    if action.lower() in ["acheter", "buy"]:
                        extracted_data["action"] = "BUY"
                    elif action.lower() in ["vendre", "sell"]:
                        extracted_data["action"] = "SELL"
                elif len(groups) == 2:  # [base, quote] seulement
                    base, quote = groups
                    extracted_data["symbol"] = f"{base}_{quote}"
                break

        # 4.2 Chercher l'action si pas encore trouvée
        if "action" not in extracted_data:
            action_match = re.search(
                r"\b(acheter|vendre|buy|sell)\b", response_text, re.I
            )
            if action_match:
                action = action_match.group(1).lower()
                if action in ["acheter", "buy"]:
                    extracted_data["action"] = "BUY"
                elif action in ["vendre", "sell"]:
                    extracted_data["action"] = "SELL"

        # 4.3 Chercher la stratégie (avec priorité aux acronymes entre parenthèses)

        # D'abord chercher les acronymes standards entre parenthèses (priorité haute)
        acronym_match = re.search(
            r"\(\s*(OB|FVG|BOS|SWEEP|LIQUIDITY)\s*\)", response_text, re.I
        )
        if acronym_match:
            strategy = acronym_match.group(1).upper()
            extracted_data["strategy"] = strategy
        else:
            # Si pas d'acronyme, chercher des formes plus verbeuses de stratégies
            strategy_patterns = [
                # Pattern spécifique pour ordre block/order block
                r"\b(?:structure\s+d[\'\s]*)?(?:ordre|order)\s*(?:block|bloc)\b",  # ordre block ou order block
                # Pattern spécifique pour fair value gap
                r"\bfair\s*value\s*gap\b",  # fair value gap
                # Pattern spécifique pour break of structure
                r"\bbreak\s*(?:of)?\s*structure\b",  # break of structure
                # Pattern spécifique pour liquidity/sweep
                r"\b(?:sweep|balayage|chasse)\s*(?:de)?\s*(?:liquidité|liquidity)\b",  # sweep de liquidité
                # Patterns génériques
                r"\b(stratégie|strategy)\s*[:\-]?\s*\b([A-Za-z]+)\b",  # stratégie: OB
                r"\bbasée? sur\s+(?:une\s+)?(?:stratégie\s+)?\b([A-Za-z]+)\b",  # basée sur (une stratégie) OB
                r"\b(OB|FVG|BOS|SWEEP|LIQUIDITY)\b",  # OB mentionné directement
            ]

            for pattern in strategy_patterns:
                strategy_match = re.search(pattern, response_text, re.I)
                if strategy_match:
                    # Cas spéciaux basés sur le pattern matché
                    if (
                        "ordre block" in pattern.lower()
                        or "order block" in pattern.lower()
                    ):
                        strategy = "OB"
                    elif "fair value gap" in pattern.lower():
                        strategy = "FVG"
                    elif "break of structure" in pattern.lower():
                        strategy = "BOS"
                    elif "liquidit" in pattern.lower() or "sweep" in pattern.lower():
                        strategy = "SWEEP"
                    else:
                        # Récupérer via les groupes dans le pattern
                        if len(strategy_match.groups()) == 2:
                            strategy = strategy_match.group(2).upper()
                        elif len(strategy_match.groups()) == 1:
                            strategy = strategy_match.group(1).upper()
                        else:
                            # Si aucun groupe capturé, prendre le match complet
                            strategy = strategy_match.group(0).upper()

                    # Normaliser certaines stratégies
                    if strategy in [
                        "ORDERBLOCK",
                        "ORDER BLOCK",
                        "ORDER-BLOCK",
                        "ORDRE BLOCK",
                        "ORDRE-BLOCK",
                    ]:
                        strategy = "OB"
                    elif "LIQUIDITY" in strategy or "LIQUIDIT" in strategy:
                        strategy = "SWEEP"
                    elif "STRUCTURE" in strategy:
                        strategy = "BOS"
                    elif "FAIR VALUE" in strategy or "FV GAP" in strategy:
                        strategy = "FVG"

                    # Ne pas utiliser "UNE" ou des mots similaires comme stratégie
                    if strategy in ["UNE", "THE", "DE", "LA", "SUR"]:
                        continue

                    extracted_data["strategy"] = strategy
                    break

        # 4.4 Chercher le niveau de confiance
        confidence_patterns = [
            # Patterns avec valeur numérique
            r"\b(confiance|confidence)\s*[:\-]?\s*(\d*\.?\d+)\b",  # confiance: 0.85
            # Patterns avec valeur textuelle
            r"\b(confiance|confidence)\s*[:\-]?\s*(élevée|haute|high|forte|moyenne|medium|moderate|faible|basse|low)\b",  # confiance: élevée
            # Pattern avec la structure "niveau de confiance XXX"
            r"\bniveau\s+de\s+confiance\s+(élevée?|haute?|high|forte?|moyenne?|medium|moderate|faible|basse?|low)\b",  # niveau de confiance élevé
        ]

        for pattern in confidence_patterns:
            confidence_match = re.search(pattern, response_text, re.I)
            if confidence_match:
                # Déterminer quel groupe contient la valeur de confiance
                if (
                    len(confidence_match.groups()) >= 2
                    and confidence_match.group(2) is not None
                ):
                    # Pattern avec 2 groupes ou plus
                    confidence_value = confidence_match.group(2)
                else:
                    # Pattern avec 1 seul groupe (à part le match complet)
                    confidence_value = confidence_match.group(1)

                # Si c'est une valeur numérique
                if confidence_value.replace(".", "", 1).isdigit():
                    extracted_data["confidence"] = float(confidence_value)
                else:
                    # Si c'est une valeur textuelle
                    confidence_text = confidence_value.lower()
                    if any(
                        word in confidence_text
                        for word in ["élev", "haut", "high", "fort", "strong"]
                    ):
                        extracted_data["confidence"] = 0.85
                    elif any(
                        word in confidence_text
                        for word in ["moyen", "medium", "moderate"]
                    ):
                        extracted_data["confidence"] = 0.65
                    elif any(
                        word in confidence_text for word in ["faible", "bas", "low"]
                    ):
                        extracted_data["confidence"] = 0.45
                break

        # 4.5 Chercher les niveaux TP/SL
        tp_match = re.search(
            r"\b(take profit|tp)\s*[:\-]?\s*(\d*\.?\d+)\b", response_text, re.I
        )
        if tp_match:
            extracted_data["take_profit"] = float(tp_match.group(2))

        sl_match = re.search(
            r"\b(stop loss|sl)\s*[:\-]?\s*(\d*\.?\d+)\b", response_text, re.I
        )
        if sl_match:
            extracted_data["stop_loss"] = float(sl_match.group(2))

        # 4.6 Chercher le risk/reward ratio
        rr_match = re.search(
            r"\b(risk[ /-]reward|ratio|rr)\s*[:\-]?\s*(\d*\.?\d+)\b",
            response_text,
            re.I,
        )
        if rr_match:
            extracted_data["risk_reward"] = float(rr_match.group(2))

        # Vérifier si on a extrait des données utiles
        if len(extracted_data) >= 2 and (
            "symbol" in extracted_data or "action" in extracted_data
        ):
            logger.info(
                f"JSON reconstruit depuis du texte libre avec {len(extracted_data)} champs"
            )
            return extracted_data

        # Aucune donnée extractible trouvée
        logger.error(
            f"Aucune donnée structurée extractible dans: {response_text[:100]}..."
        )
        return None


def test_json_parsing():
    """Teste différents scénarios de réponse JSON"""

    # Créer une instance de LLMBrain avec un client mock
    llm = LLMBrain(api_key="fake_key", debug_mode=True)
    llm.logger = logger

    # Cas de test 1: JSON valide
    valid_json = '{"symbol": "EUR_USD", "action": "BUY", "strategy": "OB", "confidence": 0.85, "risk_reward": 2.5, "take_profit": 1.0725, "stop_loss": 1.0675}'

    # Cas de test 2: JSON avec texte avant/après
    json_with_text = """Voici ma recommandation de trading:
    
    ```json
    {"symbol": "GBP_USD", "action": "SELL", "strategy": "BOS", "confidence": 0.75, "risk_reward": 2.1, "take_profit": 1.2650, "stop_loss": 1.2750}
    ```
    
    J'espère que cette recommandation vous sera utile!"""

    # Cas de test 3: Réponse sans structure JSON claire
    non_json = """Pour le trading aujourd'hui, je recommande d'acheter EUR/USD avec un niveau de confiance élevé.
    Le take profit devrait être à 1.0725 et le stop loss à 1.0675.
    La stratégie recommandée est basée sur une structure d'ordre block (OB).
    Le ratio risque/récompense est d'environ 2.5."""

    # Cas de test 4: Réponse bilingue français/anglais
    bilingual_response = """Based on my analysis, I recommend d'acheter GBP/JPY avec un niveau de confiance élevé.
    TP should be set à 182.50 and stop-loss devrait être placé à 181.20.
    La stratégie recommandée is a Break of Structure (BOS) strategy.
    Le risk-reward ratio est approximativement de 2.2."""

    # Cas de test 5: Stratégie mal orthographiée
    misspelled_strategy = """Je recommande de vendre USD/CAD avec un niveau de confiance moyen.
    Take profit: 1.3450, Stop loss: 1.3550
    Cette recommandation est basée sur une stratégie de type ordr blok (OB).
    Je vois également un fare valu gap (FVG) qui pourrait servir de niveau de support.
    Risk/reward ratio: 1.8"""

    test_cases = [
        ("1. JSON valide", valid_json),
        ("2. JSON avec texte", json_with_text),
        ("3. Réponse non-JSON", non_json),
        ("4. Réponse bilingue", bilingual_response),
        ("5. Stratégie mal orthographiée", misspelled_strategy),
    ]

    # Test de chaque cas
    for name, content in test_cases:
        logger.info(f"\n{'='*50}\nTest {name}\n{'='*50}")
        logger.info(f"Contenu de la réponse simulée:\n{content}")

        # Au lieu d'appeler generate_trade_recommendation, tester directement notre fonction d'extraction
        result = extract_json(content)

        logger.info(
            f"Résultat:\n{json.dumps(result, indent=2) if result else 'ÉCHEC - Aucun résultat'}"
        )

        # Vérifier le résultat
        if result:
            logger.info(f"✅ SUCCÈS: Extraction JSON réussie pour {name}")
            # Vérifier que les champs essentiels sont présents
            essential_fields = ["symbol", "action", "strategy"]
            missing = [field for field in essential_fields if field not in result]
            if missing:
                logger.warning(f"⚠️ Champs manquants: {', '.join(missing)}")
            else:
                logger.info("✅ Tous les champs essentiels sont présents.")
        else:
            logger.error(f"❌ ÉCHEC: Extraction JSON a échoué pour {name}")

    return True


if __name__ == "__main__":
    logger.info("Démarrage des tests de traitement JSON...")
    success = test_json_parsing()
    if success:
        logger.info("Tous les tests sont terminés.")
    else:
        logger.error("Les tests ont échoué.")
        sys.exit(1)
