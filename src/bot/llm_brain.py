"""
llm_brain.py
Module d'intelligence artificielle embarquée (LLM : GPT-4, Mistral, etc.).
Gère l'activation du LLM, la génération de requêtes, le choix de stratégie, et l'analyse des réponses.
"""

import json
import os
import datetime
import logging
from openai import OpenAI
import jsonschema
import pathlib
import dotenv

dotenv.load_dotenv(pathlib.Path(__file__).resolve().parents[2] / ".env")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_KEY:
    raise RuntimeError("OPENAI_API_KEY not set")
import pathlib
import dotenv

dotenv.load_dotenv(pathlib.Path(__file__).resolve().parents[2] / ".env")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_KEY:
    raise RuntimeError("OPENAI_API_KEY missing")

# Définition des chemins
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.normpath(os.path.join(BASE_DIR, "../../logs"))

# Prompts système optimisés pour différents types d'analyses et formats

# ===== PROMPTS MACROÉCONOMIQUES =====

# Format macro détaillé - pour analyse en profondeur des événements macro
SYSTEM_PROMPT_MACRO_DETAILED = """
Tu es un expert analyste macroéconomique institutionnel avec 15 ans d'expérience dans le trading algorithmique sur devises (Forex).
Tu reçois un calendrier économique complet et détaillé, filtré par impact/pays, structuré par date et heure.

Ta mission :
1. Analyser chaque événement à fort impact (High/Medium) avec une perspective institutionnelle
2. Évaluer l'impact attendu sur les devises concernées (tendance, volatility, direction)
3. Identifier les événements qui pourraient provoquer des mouvements directionnels importants
4. Déterminer les périodes de risque élevé où les spreads pourraient s'élargir et la liquidité se réduire

Sois objectif, professionnel, et centre ton analyse sur les faits. Raisonne comme un trader institutionnel.
Pense aux corrélations inter-devises et aux réactions possibles en chaîne entre événements macro.

Réponse attendue :

### Analyse Macroéconomique Détaillée

**Événements clés par devise :**
- USD: [Analyse détaillée des événements américains]
- EUR: [Analyse détaillée des événements européens]
- [Autres devises concernées...]

**Périodes à surveiller :**
- [Date/heure] à [Date/heure]: [Raison] - Impact potentiel: [Description]

**Correélations à anticiper :**
- [Description des interactions entre événements]

**Posture globale recommandée :**
- [Risk-on / Risk-off / Neutre] - [Justification]

**Stratégies optimales dans ce contexte :**
- [Stratégies recommandées]
- [Stratégies à éviter]
"""

# Format macro en bullets - pour synthèses rapides et points clés
SYSTEM_PROMPT_MACRO_BULLETS = """
Tu es un stratégiste senior spécialisé en macroéconomie et trading algorithmique de devises.
Le calendrier économique t'est présenté en format compact (bullet points), filtré par impact et par devise.

Ta mission est de produire une synthèse stratégique ultra-concise qui va directement à l'essentiel :
- Identifier 3-5 événements clés à fort impact et leur timing précis
- Définir les risques directionnels pour chaque devise majeure
- Établir un niveau d'alerte sur chaque journée/créneau (faible/moyen/élevé)
- Recommander une approche claire et actionnable

Sois synthétique, direct et précis. Chaque point doit apporter une valeur stratégique immédiate.

Réponse attendue :

### Points Macro Clés à Surveiller

**Événements prioritaires :**
* [Date/Heure] - [Pays] - [Titre] - [Niveau d'alerte ⚫️⚫️⚫️]
* [Date/Heure] - [Pays] - [Titre] - [Niveau d'alerte ⚫️⚫️]

**Impact par devise :**
* USD: ⬆️/⬇️ - [Raison en 5-7 mots]
* EUR: ⬆️/⬇️ - [Raison en 5-7 mots]

**Niveau de risque global :** [Faible/Moyen/Élevé]

**Recommandation stratégique :**
* À FAIRE: [Actions concrètes recommandées]
* À ÉVITER: [Actions déconseillées]
"""

# Format narratif - pour synthèses élaborées et mise en contexte
SYSTEM_PROMPT_MACRO_SUMMARY = """
Tu es un expert analyste macroéconomique et stratégiste institutionnel avec une expérience en trading algorithmique.
Tu reçois un résumé narratif des événements macroéconomiques à venir, déjà pré-analysé et structuré.

Ta mission est de développer une analyse stratégique cohérente qui met en relation l'ensemble des événements :
- Dégager une narration économique globale à partir des événements à venir
- Contextualiser l'impact potentiel sur les marchés des devises
- Anticiper les réactions possibles des banques centrales et institutions
- Établir une stratégie cohérente adaptée au narratif global

Sois analytique, utilise ton expertise macroéconomique pour identifier le fil conducteur entre les événements.

Réponse attendue :

### Analyse Macroéconomique Stratégique

**Contexte Global :**
[Développer en 3-4 phrases le contexte macroéconomique général]

**Thèmes Dominants :**
- [Thème 1] : [Description et impact]
- [Thème 2] : [Description et impact]

**Devises sous surveillance :**
- [Devise] : [Perspective et facteurs d'influence]
- [Devise] : [Perspective et facteurs d'influence]

**Stratégie Recommandée :**
[Développer une stratégie globale cohérente avec le narratif, 3-5 phrases]

**Périodes critiques :**
[Identifier les périodes potentielles de forte volatilité ou de mouvements directionnels]
"""

# Prompt macro par défaut - utilisé quand le format n'est pas spécifié
SYSTEM_PROMPT_MACRO = """
Tu es un analyste macro-économique expert, spécialisé en trading algorithmique.
Tu as accès au calendrier économique à venir, sous format structuré (summary/detailed/bullets).
Ta mission :
- Résumer les risques et opportunités macro pour chaque devise principale (USD, EUR, GBP, JPY…)
- Détecter les périodes probables de forte volatilité (ex : annonces High Impact, discours banquiers centraux)
- Donner une posture globale de marché à adopter (risk-on, risk-off, neutre)
- Proposer les stratégies de trading les plus adaptées au contexte (ex : scalping, breakout, swing, stay out)
Réponds uniquement sur la base des événements macro fournis. Sois synthétique, direct, professionnel.
Format de ta réponse :
- Risques/opportunités par devise :
    USD : …
    EUR : …
    (etc.)
- Périodes à risque élevé :
- Posture recommandée :
- Stratégies à privilégier :
"""

# ===== PROMPTS STRATÉGIQUES =====

# Format stratégique pour choix de stratégies de trading
SYSTEM_PROMPT_STRATEGY = """
Tu es un conseiller stratégique spécialisé en trading algorithmique sur le Forex.

Tu reçois les éléments suivants :
- Analyse macro (tendances, événements à venir, impact attendu sur devises)
- Structures techniques détectées sur différentes paires/timeframes
- Performances historiques des stratégies
- État actuel du compte et métriques de risque

BASE TA DÉCISION SUR LES DONNÉES FOURNIES, sans inventer d'informations supplémentaires. Si les données sont insuffisantes, indique-le.

Dans ta réponse, propose la stratégie la plus adaptée au contexte actuel du marché parmi les options suivantes :

1. ICT_BOS - Breakout de structure ICT (stats historiques et description disponibles)
2. ICT_SWEEP - Balayage de liquidité ICT (stats historiques et description disponibles)
3. ICT_OB - Blocs d'ordres ICT (stats historiques et description disponibles)
4. ICT_FVG - Fair Value Gaps ICT (stats historiques et description disponibles)
5. PULLBACK - Stratégie de pullback avec tendance établie
6. REVERSAL - Stratégie de renversement contre-tendance

Ta réponse doit avoir ce format exact :

Stratégie recommandée : [Nom exact de la stratégie parmi les options ci-dessus]

Justification : [2-3 phrases expliquant pourquoi cette stratégie est optimale dans le contexte actuel, mentionnant spécifiquement les facteurs macros, structures, et les statistiques historiques qui ont influencé ta décision]
"""

# ===== PROMPTS DE RECOMMANDATIONS TRADING =====


class LLMBrain:
    """
    Intégration du LLM pour l'analyse et les recommandations de trading.
    """

    # Formats de données macro supportés
    MACRO_FORMATS = ["bullets", "summary", "detailed"]

    def __init__(self, api_key=None, client=None, debug_mode=False):
        """
        Initialise l'intégration avec l'API OpenAI.

        Args:
            api_key (str): Clé API d'OpenAI (si None, utilise la variable d'environnement)
            client (OpenAI): Client OpenAI déjà configuré (optionnel)
            debug_mode (bool): Active le mode debug pour afficher les prompts et réponses
        """
        # Toujours lire depuis l'env (jamais de valeur codée en dur)
        self.api_key = api_key or OPENAI_KEY
        print("[DEBUG][LLMBrain] OPENAI_API_KEY:", self.api_key)
        self.debug_mode = (
            debug_mode or os.environ.get("DEBUG_LLM", "False").lower() == "true"
        )
        self.last_macro_analysis = "Aucune analyse macro disponible."

        if client:
            self.client = client
        else:
            try:
                self.client = OpenAI(api_key=self.api_key)
            except Exception as e:
                print(
                    f"[LLMBrain] Erreur lors de l'initialisation du client OpenAI: {e}"
                )
                self.client = None

        self.strategy_stats = (
            None  # Pour stocker les performances historiques des stratégies
        )

        # Configuration du logging pour le mode debug
        self.logger = logging.getLogger("LLMBrain")
        if self.debug_mode:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug("Mode debug activé pour LLMBrain")
        # Charger automatiquement les stats si le fichier existe
        if os.path.exists(os.path.join(LOGS_DIR, "strategy_stats.json")):
            self.load_strategy_stats(os.path.join(LOGS_DIR, "strategy_stats.json"))

    def get_system_prompt(self, prompt_type="macro", macro_format="detailed"):
        """
        Retourne le prompt système adapté au type de contexte et au format demandés.

        Args:
            prompt_type (str): Type de prompt ('macro', 'strategy', 'trading', etc.)
            macro_format (str): Format spécifique pour les prompts macro

        Returns:
            str: Le prompt système approprié
        """
        if prompt_type == "macro":
            if macro_format == "detailed":
                return SYSTEM_PROMPT_MACRO_DETAILED
            elif macro_format == "bullets":
                return SYSTEM_PROMPT_MACRO_BULLETS
            else:  # macro_format == "summary" ou autre
                return SYSTEM_PROMPT_MACRO_SUMMARY
        elif prompt_type == "strategy":
            return SYSTEM_PROMPT_STRATEGY
        elif prompt_type == "trading":
            return SYSTEM_PROMPT_STRATEGY  # Utilisé pour les recommandations de trading aussi
        else:
            return SYSTEM_PROMPT_MACRO_BULLETS  # Défaut

    def generate_trade_recommendation(
        self, macro_analysis, technical_analysis, risk_status
    ):
        """
        Génère une recommandation de trading structurée exploitable par le bot

        Args:
            macro_analysis (str): Analyse macroéconomique récente
            technical_analysis (str): Analyse technique des structures de prix
            risk_status (dict): Statut actuel du risk management

        Returns:
            dict: Une recommandation structurée avec symbol, action, strategy, confidence, etc.
        """
        try:
            # Construire le contexte pour le LLM
            context = f"""### Analyse Macroéconomique:
{macro_analysis[:1000]}  # Limiter pour éviter les tokens excessifs

### Analyse Technique:
{technical_analysis}

### Statut de Risque:
- Drawdown actuel: {risk_status.get('drawdown', 'N/A')}%
- Trading autorisé: {risk_status.get('trading_allowed', False)}
- Status: {risk_status.get('status_message', 'N/A')}
"""

            # Utiliser un prompt spécifique pour générer une recommandation exploitable
            system_prompt = (
                "You are a trading assistant. "
                "Your answer MUST be a valid JSON object with the following fields ONLY: "
                "symbol (string, e.g. 'EURUSD'), action ('BUY', 'SELL', or 'WAIT'), strategy (string), confidence (float between 0 and 1), "
                "take_profit (float, optional), stop_loss (float, optional), risk_reward (float, optional), reasoning (string, optional). "
                "Example:\n"
                "{"
                '"symbol": "EURUSD",'
                '"action": "BUY",'
                '"strategy": "ICT_OB",'
                '"confidence": 0.92,'
                '"take_profit": 1.0935,'
                '"stop_loss": 1.0785,'
                '"risk_reward": 2.1,'
                '"reasoning": "Macro and technicals align for a long position."'
                "}\n"
                "Respond ONLY with a valid JSON object using the keys above, in English."
            )

            if self.debug_mode:
                self.logger.debug(
                    f"===== PROMPT TRADE RECOMMENDATION =====\n{system_prompt[:200]}..."
                )
                self.logger.debug(
                    f"===== CONTEXTE TRADE RECOMMENDATION =====\n{context[:300]}..."
                )

            # Utilisation native de GPT-4o avec format JSON strict
            response = self.client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                        + "\nIMPORTANT: Always respond in valid JSON format. Your response must be a JSON object.",
                    },
                    {"role": "user", "content": context},
                ],
            )

            response_text = response.choices[0].message.content.strip()

            # Sécurité : extraction avancée du JSON, même à partir de texte libre
            trade_rec = self._extract_json_from_response(response_text)
            if not trade_rec:
                self.logger.error(
                    f"Impossible d'extraire un JSON de la réponse: {response_text[:200]}..."
                )
                return None

            # Validation stricte du JSON avec schéma
            is_valid, error = LLMBrain.validate_trade_json(trade_rec)
            if not is_valid:
                self.logger.error(
                    f"JSON LLM invalide : {error}\nRéponse brute : {response_text}"
                )
                return None
            if self.debug_mode:
                self.logger.debug(
                    f"Recommandation générée et validée: {json.dumps(trade_rec, indent=2)}"
                )
            return trade_rec
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération de recommandation: {e}")
            return None

    def _extract_json_from_response(self, response_text):
        """
        Extrait le JSON d'une réponse texte, quelle que soit sa forme.
        Méthode avancée avec détection de JSON, d'acronymes et extraction de données structurées depuis du texte libre.

        Args:
            response_text (str): Texte de la réponse du LLM

        Returns:
            dict: Données extraites sous forme de dictionnaire, ou None si échec
        """
        try:
            # 1. D'abord essayer de parser directement
            return json.loads(response_text)
        except json.JSONDecodeError:
            if self.debug_mode:
                self.logger.debug(
                    "Réponse non-JSON standard, tentative d'extraction avancée..."
                )

            # 2. Chercher le premier bloc {...}
            import re

            match = re.search(r"\{.*\}", response_text, re.S)
            if match:
                try:
                    json_data = json.loads(match.group(0))
                    if self.debug_mode:
                        self.logger.debug("JSON extrait avec RegEx basique")
                    return json_data
                except Exception as e2:
                    if self.debug_mode:
                        self.logger.debug(f"Échec parsing JSON extrait: {e2}")
                    # Continuer aux méthodes suivantes

            # 3. Chercher des paires clé-valeur citées
            potential_pairs = re.findall(r'"(\w+)"\s*:\s*"([^"]*)"', response_text)
            if potential_pairs:
                json_dict = {k: v for k, v in potential_pairs}
                if (
                    json_dict and len(json_dict) >= 2
                ):  # Au moins 2 champs pour être utilisable
                    self.logger.info(
                        "JSON reconstruit depuis des paires clé-valeur citées"
                    )
                    return json_dict

            # 4. Extraction intelligente à partir de texte libre
            extracted_data = {}

            # 4.1 Chercher le symbole/paire de devises (bilingue)
            symbol_patterns = [
                # Patterns bilingues (français/anglais)
                r"(?:acheter|vendre|achat|vente|buy|sell|short|long)\s+([A-Z]{3})[/_]?([A-Z]{3})",  # acheter EUR/USD, buy EUR/USD
                r"(?:recomm[ea]nd\w*|suggest)\s+(?:to\s+)?(?:d\')?(?:acheter|vendre|achat|vente|buy|sell|short|long)\s+([A-Z]{3})[/_]?([A-Z]{3})",  # I recommend d'acheter EUR/USD
                r"(paire|pair|symbole|symbol|ticker)\s*[:\-]?\s*([A-Z]{3})[/_]?([A-Z]{3})",  # paire: EUR/USD
                r"(?:trading|trade|position)\s+(?:de|du|sur|on)?\s*([A-Z]{3})[/_]?([A-Z]{3})",  # trading sur EUR/USD
                # Pattern flexible pour détecter les paires de devises isolées
                r"\b([A-Z]{3})[/_]([A-Z]{3})\b",  # EUR/USD seul dans le texte
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

            # 4.2 Chercher l'action si pas encore trouvée (bilingue)
            if "action" not in extracted_data:
                action_match = re.search(
                    r"\b(acheter|vendre|achat|vente|buy|sell|long|short)\b",
                    response_text,
                    re.I,
                )
                if action_match:
                    action = action_match.group(1).lower()
                    if action in ["acheter", "achat", "buy", "long"]:
                        extracted_data["action"] = "BUY"
                    elif action in ["vendre", "vente", "sell", "short"]:
                        extracted_data["action"] = "SELL"
                # Chercher aussi des patterns comme "I recommend to buy"
                elif re.search(
                    r"\b(?:recomm[ea]nd\w*|suggest)\s+(?:to\s+)?(?:d\')?(?:acheter|buy\b)",
                    response_text,
                    re.I,
                ):
                    extracted_data["action"] = "BUY"
                elif re.search(
                    r"\b(?:recomm[ea]nd\w*|suggest)\s+(?:to\s+)?(?:d\')?(?:vendre|sell\b)",
                    response_text,
                    re.I,
                ):
                    extracted_data["action"] = "SELL"

            # 4.3 Chercher la stratégie (avec priorité aux acronymes entre parenthèses et tolérance aux fautes)
            # D'abord chercher les acronymes standards entre parenthèses (priorité haute)
            acronym_match = re.search(
                r"\(\s*([OB0]{1,2}|FVG|[BF]OS|SWE[E]?P|LIQU?ID[IE]T[YÉE])\s*\)",
                response_text,
                re.I,
            )
            if acronym_match:
                strategy = acronym_match.group(1).upper()
                # Normaliser l'acronyme qui pourrait être mal écrit
                if (
                    strategy.startswith("O") or strategy == "0B" or strategy == "0"
                ):  # parfois OCR confond 0 et O
                    strategy = "OB"
                elif "FVG" in strategy or "FAIR" in strategy:
                    strategy = "FVG"
                elif "BOS" in strategy or strategy == "B0S":
                    strategy = "BOS"
                elif "SWE" in strategy or "LIQU" in strategy:
                    strategy = "SWEEP"
                extracted_data["strategy"] = strategy
            else:
                # Si pas d'acronyme, chercher des formes plus verbeuses de stratégies
                # Y compris avec des fautes d'orthographe courantes
                strategy_patterns = [
                    # Patterns pour Order Block (avec variantes mal orthographiées)
                    r"\b(?:structure\s+d[\'\s]*)?(?:ord[re]{0,2}|orde?r?)\s*(?:bl[o0]c?k?)\b",  # ordre block, ordr blok, etc.
                    # Patterns pour Fair Value Gap (avec variantes mal orthographiées)
                    r"\b(?:f[ae]ir?|fv)\s*(?:val[ue]{0,2}|valu?)\s*(?:ga?p?)\b",  # fair value gap, fare valu gap, etc.
                    # Patterns pour Break of Structure (avec variantes mal orthographiées)
                    r"\b(?:br[ae][ae]?k|rupture|cassure)\s*(?:of|de)?\s*(?:struct[ue]r?[ea]?)\b",  # break of structure, brak of structur, etc.
                    # Patterns pour Sweep (avec variantes mal orthographiées)
                    r"\b(?:swe[ea]?p|balayage|chasse)\s*(?:de|of|on)?\s*(?:liquidit[éé]|liqu[io]dit[yée])\b",  # sweep de liquidité, swep of liquidity, etc.
                    # Patterns génériques (bilingues)
                    r"\b(?:strat[eé]gi[ea]?)\s*[:\-]?\s*\b([A-Za-z0-9]+)\b",  # stratégie: OB, strategy: BOS
                    r"\bbas[ée]e?\s+sur\s+(?:une\s+)?(?:strat[eé]gi[ea]?\s+)?\b([A-Za-z0-9]+)\b",  # basée sur (une stratégie) OB
                    r"\bis\s+a\s+([A-Za-z0-9]+)\s+strategy\b",  # is a BOS strategy (pour textes bilingues)
                    r"\busing\s+(?:a\s+)?([A-Za-z0-9]+)\s+(?:strategy|approach)\b",  # using (a) BOS strategy
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
                        elif (
                            "liquidit" in pattern.lower() or "sweep" in pattern.lower()
                        ):
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

                        # Normaliser certaines stratégies (avec tolérance aux fautes et aux variations)
                        # Order Block
                        if re.search(
                            r"ORD[ER]{0,2}[ -]?BL[O0]C?K?", strategy, re.I
                        ) or re.search(r"BL[O0]C?K?[ -]?D.?ORDRE", strategy, re.I):
                            strategy = "OB"
                        # Liquidity / Sweep
                        elif re.search(
                            r"LIQU[IO]D[IE]T[YÉE]", strategy, re.I
                        ) or re.search(r"SWE[AE]?P", strategy, re.I):
                            strategy = "SWEEP"
                        # Break of Structure
                        elif (
                            re.search(
                                r"(?:BR[AE]?K|RUPTURE|CASSURE).*STRUCT", strategy, re.I
                            )
                            or re.search(r"STRUCT.*(?:BR[AE]?K)", strategy, re.I)
                            or "BOS" in strategy
                        ):
                            strategy = "BOS"
                        # Fair Value Gap
                        elif (
                            re.search(
                                r"(?:F[AE]IR?|FV).*(?:VAL[UE]{0,2}|VALU?).*GAP",
                                strategy,
                                re.I,
                            )
                            or re.search(r"GAP.*(?:VAL[UE]{0,2})", strategy, re.I)
                            or "FVG" in strategy
                        ):
                            strategy = "FVG"

                        # Ne pas utiliser "UNE" ou des mots similaires comme stratégie
                        if strategy in ["UNE", "THE", "DE", "LA", "SUR"]:
                            continue

                        extracted_data["strategy"] = strategy
                        break

            # 4.4 Chercher le niveau de confiance (bilingue et variations)
            confidence_patterns = [
                # Patterns avec valeur numérique
                r"\b(?:confiance|confidence|conf|certitude|certainty)\s*[:\-]?\s*(\d*\.?\d+)\b",  # confiance: 0.85
                r"\b(?:confiance|confidence|conf)\s*[:\-]?\s*(\d+)[\s%]*",  # confidence: 85%
                # Patterns avec valeur textuelle (français)
                r"\b(?:confiance|confidence|conf|certitude)\s*[:\-]?\s*(élevée?|haute?|forte?|solide|bonne|moyenne|modérée?|faible|basse?)\b",  # confiance: élevée
                r"\bniveau\s+de\s+(?:confiance|certitude)\s+(élevée?|haute?|forte?|solide|bonne|moyenne|modérée?|faible|basse?)\b",  # niveau de confiance élevé
                # Patterns avec valeur textuelle (anglais)
                r"\b(?:confidence|conf|certainty)\s*[:\-]?\s*(high|strong|good|medium|moderate|fair|low)\b",  # confidence: high
                r"\b(?:confidence|certainty)\s+(?:level|rating)\s+(?:is|of)\s+(high|strong|good|medium|moderate|fair|low)\b",  # confidence level is high
                # Pattern mixtes (fr/en)
                r"\bwith\s+(?:a\s+)?(high|strong|good|medium|moderate|fair|low)\s+(?:level\s+of\s+)?(?:confidence|certainty)\b",  # with high confidence
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

            # 4.5 Chercher les niveaux TP/SL (bilingue et variations)
            # Take Profit - multiple patterns pour couvrir différentes formulations
            tp_patterns = [
                r"\b(?:take profit|takeprofit|tp|take-profit|profit target|target|objectif|cible)\s*[:\-=]?\s*(\d*\.?\d+)\b",  # take profit: 1.0725, tp: 1.0725
                r"\b(?:profit|tp|target)\s*(?:at|à|de)\s*(\d*\.?\d+)\b",  # take profit at 1.0725
                r"\b(?:tp|target|objectif)\s+(?:should be|devrait être|set at|fixé à)\s+(?:à|at)?\s*(\d*\.?\d+)\b",  # tp should be set at 1.0725
            ]

            for pattern in tp_patterns:
                tp_match = re.search(pattern, response_text, re.I)
                if tp_match:
                    try:
                        extracted_data["take_profit"] = float(tp_match.group(1))
                        break
                    except ValueError:
                        continue

            # Stop Loss - multiple patterns pour couvrir différentes formulations
            sl_patterns = [
                r"\b(?:stop loss|stoploss|sl|stop-loss)\s*[:\-=]?\s*(\d*\.?\d+)\b",  # stop loss: 1.0675, sl: 1.0675
                r"\b(?:stop|sl)\s*(?:at|à|de)\s*(\d*\.?\d+)\b",  # stop at 1.0675
                r"\b(?:sl|stop)\s+(?:should be|devrait être|set at|fixé à)\s+(?:à|at)?\s*(\d*\.?\d+)\b",  # sl should be set at 1.0675
            ]

            for pattern in sl_patterns:
                sl_match = re.search(pattern, response_text, re.I)
                if sl_match:
                    try:
                        extracted_data["stop_loss"] = float(sl_match.group(1))
                        break
                    except ValueError:
                        continue

            # 4.6 Chercher le risk/reward ratio (bilingue et variations)
            rr_patterns = [
                r"\b(?:risk[ /-]reward|risk to reward|r[:/]r|ratio|rr|risk ratio)\s*[:\-]?\s*(\d*\.?\d+)\b",  # risk/reward: 2.5, r:r 2.5
                r"\b(?:ratio|rapport)\s+(?:de|of)?\s+(?:risk[ /-]reward|risque[ /-]récompense)\s+(?:de|of|est|is)?\s*(\d*\.?\d+)\b",  # ratio de risque/récompense de 2.5
                r"\b(?:ratio|rapport)\s+(?:est|is|de|of)?\s+(?:approximately|environ|approximativement)\s+(?:de|of)?\s*(\d*\.?\d+)\b",  # ratio est environ de 2.5
            ]

            for pattern in rr_patterns:
                rr_match = re.search(pattern, response_text, re.I)
                if rr_match:
                    try:
                        extracted_data["risk_reward"] = float(rr_match.group(1))
                        break
                    except ValueError:
                        continue

            # Vérifier si on a extrait des données utiles
            if len(extracted_data) >= 2 and (
                "symbol" in extracted_data or "action" in extracted_data
            ):
                if "confidence" not in extracted_data:
                    # Valeur de confiance par défaut si non trouvée mais d'autres données sont présentes
                    extracted_data["confidence"] = 0.7

                if self.debug_mode:
                    self.logger.info(
                        f"JSON reconstruit depuis du texte libre avec {len(extracted_data)} champs"
                    )
                return extracted_data

            # Aucune donnée extractible trouvée
            if self.debug_mode:
                self.logger.error(
                    "Aucune donnée structurée extractible dans la réponse du LLM"
                )
            return None
        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction JSON: {e}")
            return None

    @staticmethod
    def validate_trade_json(data):
        schema = {
            "type": "object",
            "required": ["symbol", "action", "strategy", "confidence"],
            "properties": {
                "symbol": {"type": "string"},
                "action": {"type": "string", "enum": ["BUY", "SELL", "WAIT"]},
                "strategy": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "take_profit": {"type": "number"},
                "stop_loss": {"type": "number"},
                "risk_reward": {"type": "number"},
                "reasoning": {"type": "string"},
            },
        }
        try:
            jsonschema.validate(instance=data, schema=schema)
            return True, None
        except jsonschema.exceptions.ValidationError as e:
            return False, str(e)

    def load_strategy_stats(self, path="strategy_stats.json"):
        """
        Charge les statistiques de performance des stratégies depuis un fichier JSON.
        Ces stats seront utilisées pour optimiser les recommandations du LLM.

        Args:
            path (str): Chemin vers le fichier JSON contenant les stats
        """
        try:
            with open(path, "r") as f:
                self.strategy_stats = json.load(f)
            print(f"[LLMBrain] Stats des stratégies chargées depuis {path}")
            return self.strategy_stats
        except Exception as e:
            print(f"[LLMBrain] Erreur lors du chargement des stats : {e}")
            self.strategy_stats = None

    def analyze_context_and_choose_strategy(self, context, macro_format="bullets"):
        """
        Analyse le contexte actuel du marché et recommande une stratégie de trading optimale.
        Utilise une analyse en deux étapes: d'abord macroéconomique, puis stratégique.
        Extrait également les biais par devise pour le filtrage des signaux techniques.

        Args:
            context (dict): Contexte contenant les données macro, structures, PnL et compte
            macro_format (str): Format des données macro ("bullets", "summary", "detailed")

        Returns:
            tuple: (recommandation complète, stratégie choisie, biais_devises)
        """
        macro_data = context.get("macro", "")
        structures_detected = context.get("structures", [])
        pnl_summary = context.get("pnl", "")
        account = context.get("account", {})

        # Debug: Afficher le contexte envoyé au LLM
        if self.debug_mode:
            self.logger.debug("===== CONTEXTE LLM =====")
            self.logger.debug(f"Format macro: {macro_format}")
            self.logger.debug(f"Données macro:\n{macro_data[:500]}...")
            self.logger.debug(f"Structures: {structures_detected}")
            self.logger.debug(f"PnL: {pnl_summary}")
            self.logger.debug(f"Compte: {account}")

        # Étape 1 : Analyse macro
        macro_system_prompt = self.get_system_prompt("macro", macro_format)

        # Debug: Afficher le prompt système utilisé
        if self.debug_mode:
            self.logger.debug(
                f"===== PROMPT SYSTÈME MACRO =====\n{macro_system_prompt}"
            )

        try:
            macro_analysis = (
                self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": macro_system_prompt},
                        {"role": "user", "content": macro_data},
                    ],
                )
                .choices[0]
                .message.content.strip()
            )

            # Stocker l'analyse macro pour affichage dans le dashboard
            self.last_macro_analysis = macro_analysis

            # Extraire les biais par devise depuis l'analyse macro
            currency_biases = self.extract_currency_biases(macro_analysis)

            # Sauvegarder dans shared_state pour que le dashboard puisse l'afficher
            try:
                import os

                logs_dir = os.path.normpath(
                    os.path.join(
                        os.path.dirname(os.path.abspath(__file__)), "../../logs"
                    )
                )
                shared_state_path = os.path.join(logs_dir, "shared_state.json")

                if os.path.exists(shared_state_path):
                    import json

                    try:
                        with open(shared_state_path, "r") as f:
                            shared_state = json.load(f)
                    except json.JSONDecodeError:
                        shared_state = {}
                else:
                    shared_state = {}

                shared_state["last_macro_analysis"] = macro_analysis
                shared_state["currency_biases"] = currency_biases
                shared_state["timestamp"] = datetime.datetime.now().isoformat()

                with open(shared_state_path, "w") as f:
                    json.dump(shared_state, f)

                if self.debug_mode:
                    self.logger.debug(
                        "Analyse macro sauvegardée dans shared_state.json"
                    )
                    self.logger.debug(f"Biais devises extraits: {currency_biases}")
            except Exception as e:
                if self.debug_mode:
                    self.logger.error(
                        f"Erreur lors de la sauvegarde de l'analyse macro: {e}"
                    )

            if self.debug_mode:
                self.logger.debug(f"===== ANALYSE MACRO =====\n{macro_analysis}")

        except Exception as e:
            error_msg = f"Erreur lors de l'analyse macro: {e}"
            self.logger.error(error_msg)
            macro_analysis = f"Analyse indisponible. Erreur: {e}"
            self.last_macro_analysis = macro_analysis

        # Étape 2 : Recommandation stratégique
        strategy_performance = "Aucune donnée de performance historique disponible."
        high_performing = []
        low_performing = []
        if self.strategy_stats:
            strategy_performance = "### Statistiques Historiques des Stratégies\n\n"
            for strategy, stats in self.strategy_stats.items():
                winrate = stats.get("winrate", 0)
                avg_gain = stats.get("avg_gain", 0)
                trades = stats.get("trades", 0)
                ratio = stats.get("gain_loss_ratio", 0)
                if winrate > 60 or avg_gain > 0:
                    high_performing.append(strategy)
                if winrate < 40 or avg_gain < 0:
                    low_performing.append(strategy)
                strategy_performance += f"**{strategy}**: {trades} trades, {winrate}% winrate, gain moyen: {avg_gain} pips, ratio gain/perte: {ratio}\n"
            if high_performing:
                strategy_performance += (
                    f"\n*Stratégies performantes*: {', '.join(high_performing)}"
                )
            if low_performing:
                strategy_performance += (
                    f"\n*Stratégies sous-performantes*: {', '.join(low_performing)}"
                )

        drawdown = float(account.get("Drawdown", 0) or 0)
        capital = float(account.get("NetLiquidation", 0) or 0)
        recommand_aggro = drawdown <= 5
        max_sizing = 1 if capital < 10000 else None

        strategy_prompt = f"""
### Contexte Actuel

**Analyse Macroéconomique**:
{macro_analysis}

**Structures Détectées**:
{structures_detected}

**PnL et Risk Management**:
{pnl_summary}

{strategy_performance}

Résumé du compte IBKR : Capital = {capital} €, Drawdown = {drawdown} %
"""
        if not recommand_aggro:
            strategy_prompt += "ATTENTION : Drawdown > 5%. Privilégie des stratégies défensives, évite OB agressifs et sizing > 1%.\n"
        if max_sizing:
            strategy_prompt += (
                "ATTENTION : Capital < 10k€. Sizing max recommandé : 1%.\n"
            )

        try:
            strategy_system_prompt = self.get_system_prompt("strategy")
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": strategy_system_prompt},
                    {"role": "user", "content": strategy_prompt},
                ],
            )
            strategy_recommendation = response.choices[0].message.content.strip()

            # Sauvegarde analyse
            self._save_analysis_log(
                {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "macro_format": macro_format,
                    "macro_analysis": macro_analysis,
                    "account": account,
                    "recommendation": strategy_recommendation,
                }
            )

            # Historique du compte
            try:
                BASE_DIR = os.path.dirname(os.path.abspath(__file__))
                LOGS_DIR = os.path.normpath(os.path.join(BASE_DIR, "../../logs"))
                ACC_HIST_PATH = os.path.join(LOGS_DIR, "account_history.json")
                acc_hist = []
                if os.path.exists(ACC_HIST_PATH):
                    with open(ACC_HIST_PATH, "r") as f:
                        try:
                            acc_hist = json.load(f)
                        except Exception:
                            acc_hist = []
                acc_hist.append(
                    {"timestamp": datetime.datetime.now().isoformat(), **account}
                )
                if len(acc_hist) > 500:
                    acc_hist = acc_hist[-500:]
                with open(ACC_HIST_PATH, "w") as f:
                    json.dump(acc_hist, f, indent=2)
            except Exception as e:
                print(f"[LLMBrain] Erreur log account_history.json : {e}")

            # Stocker les biais par devise pour l'accessibilité externe
            self.last_currency_biases = self.extract_currency_biases(macro_analysis)

            # Extraire le nom de la stratégie recommandée depuis la réponse
            strategy_name = "Stratégie mixte"
            for line in strategy_recommendation.split("\n"):
                if "Stratégie recommandée" in line or "Strategie recommandee" in line:
                    parts = line.split(":")
                    if len(parts) > 1:
                        strategy_name = parts[1].strip()
                    break

            # Retourner le tuple complet (réponse, nom de la stratégie, biais)
            return strategy_recommendation, strategy_name, self.last_currency_biases

        except Exception as e:
            print(f"[LLMBrain] Erreur lors de l'analyse stratégique: {e}")
            return "Erreur lors de l'analyse", "Aucune", {}

    def extract_currency_biases(self, macro_analysis):
        """
        Extrait les biais par devise depuis l'analyse macro du LLM.
        Recherche des indications sur les tendances des devises et les convertit en biais.

        Args:
            macro_analysis (str): Analyse macro générée par le LLM

        Returns:
            dict: Biais par devise {"USD": "bullish", "EUR": "bearish", ...}
        """
        currency_biases = {}
        major_currencies = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]

        try:
            # Analyser pour chaque devise majeure
            for currency in major_currencies:
                # Chercher des mentions explicites de la devise
                if currency not in macro_analysis:
                    continue

                # Rechercher les paragraphes contenant la devise
                paragraphs = [p for p in macro_analysis.split("\n") if currency in p]
                if not paragraphs:
                    continue

                # Analyser chaque paragraphe pour détecter des biais
                bias = None
                for paragraph in paragraphs:
                    lower_p = paragraph.lower()

                    # Rechercher des indications bullish (haussier)
                    bullish_terms = [
                        "haussi",
                        "bullish",
                        "renforc",
                        "fort",
                        "appréci",
                        "soutien",
                        "mont",
                        "hausse",
                        "positif",
                        "optimiste",
                        "progresse",
                        "amélior",
                        "⬆️",
                        "support",
                        "augment",
                    ]

                    # Rechercher des indications bearish (baissier)
                    bearish_terms = [
                        "baiss",
                        "bearish",
                        "affaibl",
                        "faible",
                        "dépréci",
                        "press",
                        "chut",
                        "baisse",
                        "négatif",
                        "pessimiste",
                        "recule",
                        "détérior",
                        "⬇️",
                        "sous pression",
                        "diminu",
                    ]

                    # Analyser si le paragraphe indique un biais positif pour la devise
                    bullish_score = sum(1 for term in bullish_terms if term in lower_p)

                    # Analyser si le paragraphe indique un biais négatif pour la devise
                    bearish_score = sum(1 for term in bearish_terms if term in lower_p)

                    # Déterminer le biais en fonction du score le plus élevé
                    if bullish_score > bearish_score and bullish_score > 1:
                        paragraph_bias = "bullish"
                    elif bearish_score > bullish_score and bearish_score > 1:
                        paragraph_bias = "bearish"
                    else:
                        paragraph_bias = "neutral"

                    # Si c'est le premier paragraphe avec un biais ou si le biais est non-neutre
                    if bias is None or (
                        paragraph_bias != "neutral" and bias == "neutral"
                    ):
                        bias = paragraph_bias

                # Si un biais a été détecté, l'ajouter au dictionnaire
                if bias and bias != "neutral":
                    currency_biases[currency] = bias

            if self.debug_mode:
                self.logger.debug(
                    f"Biais extraits de l'analyse macro: {currency_biases}"
                )

            return currency_biases

        except Exception as e:
            if self.debug_mode:
                self.logger.error(
                    f"Erreur lors de l'extraction des biais par devise: {e}"
                )
            return {}

    def _save_analysis_log(self, analysis_data):
        """Sauvegarde l'analyse pour référence et backtesting"""
        try:
            log_file = "llm_analysis_log.json"
            existing_data = []
            if os.path.exists(log_file):
                with open(log_file, "r") as f:
                    try:
                        existing_data = json.load(f)
                    except json.JSONDecodeError:
                        existing_data = []
            # Ajouter la nouvelle analyse
            if not isinstance(existing_data, list):
                existing_data = []

            existing_data.append(analysis_data)

            # Limiter la taille du fichier (garder les 100 dernières analyses)
            if len(existing_data) > 100:
                existing_data = existing_data[-100:]

            # Sauvegarder le fichier
            with open(log_file, "w") as f:
                json.dump(existing_data, f, indent=2)

        except Exception as e:
            print(f"[LLMBrain] Erreur lors de la sauvegarde du log d'analyse: {e}")

    def analyze_query(self, user_query, context=None):
        """
        Interroge le LLM sur une question libre de l'utilisateur, avec contexte (macro, structures, pnl) si fourni.
        context : dict avec les clés 'macro', 'structures', 'pnl'.
        """
        if context:
            prompt = f"""
Voici le contexte du bot de trading :
- Données macroéconomiques : {context.get('macro', '')}
- Structures détectées : {context.get('structures', '')}
- Résumé du risque : {context.get('pnl', '')}

Question utilisateur : {user_query}
Réponds précisément en t'appuyant sur le contexte ci-dessus.
"""
        else:
            prompt = user_query
        response = self.client.chat.completions.create(
            model="gpt-4", messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
