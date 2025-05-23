"""
llm_engine.py
Module d'intelligence artificielle encapsé et découplé du reste du code.
Analyse les données de marché, signaux ICT et événements macro pour générer
une recommandation de trading unique, sans biais directionnel.
"""

import json
import os
import csv
import logging
from datetime import datetime
import jsonschema
from typing import Dict, Any, Optional
import openai

# Configuration du logger
logger = logging.getLogger("LLMEngine")
logger.setLevel(logging.INFO)

# Schéma JSON pour validation des réponses LLM
TRADE_DECISION_SCHEMA = {
    "type": "object",
    "required": ["symbol", "direction", "strategy", "entry", "sl", "tp", "confidence", "reasoning"],
    "properties": {
        "symbol": {"type": "string"},
        "direction": {"type": "string", "enum": ["LONG", "SHORT"]},
        "strategy": {"type": "string"},
        "entry": {"type": "number"},
        "sl": {"type": "number"},
        "tp": {"type": "number"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reasoning": {"type": "string", "maxLength": 300}
    }
}

# Bloc d'exemples LONG/SHORT pour le prompt
EXAMPLE_BLOCK = """
### EXEMPLE LONG
INPUT:
    EURUSD:
        HTF_structure: bullish
        OB_H4: 1.0780
        BOS_H4: 1.0805
    Macro:
        USD: CPI en baisse, impact modéré
        EUR: Pas d'événement
OUTPUT:
    {
        "symbol": "EURUSD",
        "direction": "LONG",
        "strategy": "ICT_OB",
        "entry": 1.0782,
        "sl": 1.0760,
        "tp": 1.0835,
        "confidence": 0.79,
        "reasoning": "BOS H4 + OB frais + macro USD soft"
    }

### EXEMPLE SHORT
INPUT:
    GBPUSD:
        HTF_structure: bearish
        OB_H1: 1.2740
        BOS_H1: 1.2720
    Macro:
        GBP: Retail Sales négatif (impact élevé)
OUTPUT:
    {
        "symbol": "GBPUSD",
        "direction": "SHORT",
        "strategy": "ICT_OB",
        "entry": 1.2735,
        "sl": 1.2760,
        "tp": 1.2670,
        "confidence": 0.84,
        "reasoning": "OB H1 + news GBP négative"
    }
"""

def decide_trade(payload: dict) -> Optional[dict]:
    """
    Analyse les données de marché, signaux ICT et événements macro pour
    générer une recommandation de trading unique.
    
    Paramètres
    ----------
    payload : dict
        market_data, ict_signals, macro_events, history

    Retour
    ------
    dict
        symbol, direction, strategy, entry, sl, tp, confidence, reasoning
        ou None si erreur de validation
    """
    prompt = _construct_prompt(payload)
    llm_reply = _call_llm(prompt)
    if llm_reply is None:
        return None
    if not _validate_llm_response(llm_reply):
        return None
    _log_decision_to_csv(llm_reply)
    return llm_reply

def _construct_prompt(payload: dict) -> str:
    """
    Construit le prompt système + user :
      – section système (règles, exemples LONG/SHORT)
      – section user (données réelles du jour)
    """
    system_block = """
Tu es "ICT-SMC Autonomous Trader v1".
Objectif : analyser {market_len} paires, leurs signaux ICT et le contexte macro pour formuler **UN** trade optimal.
Contraintes :
1. Compare au moins 3 paires avant de choisir.
2. Pas de biais : prouve que LONG et SHORT ont été évalués.
3. Réponds EXCLUSIVEMENT en JSON conforme au schéma : {{symbol, direction, strategy, entry, sl, tp, confidence, reasoning}}.
4. `reasoning` ≤ 300 car., style télégraphique.

### EXEMPLES
{examples}
""".strip()

    examples = EXAMPLE_BLOCK  # la chaîne que tu as déjà mise
    system_prompt = system_block.format(
        market_len=len(payload.get("market_data", {})),
        examples=examples
    )

    # on sérialise les vraies données sous forme compacte YAML-like pour le modèle
    user_prompt = json.dumps(payload, ensure_ascii=False, indent=2)

    full_prompt = f"{system_prompt}\n\n### DONNÉES RÉELLES\n{user_prompt}"
    logger.debug("[LLM PROMPT]\n%s", full_prompt[:800])  # tronqué
    return full_prompt

def _call_llm(prompt: str) -> Optional[dict]:
    """Interroge OpenAI, renvoie la réponse JSON décodée ou None."""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt.split("### DONNÉES")[0]},
                {"role": "user",   "content": prompt.split("### DONNÉES")[1]},
            ],
            temperature=0.2,
            max_tokens=250
        )
        raw_content = response.choices[0].message["content"]
        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError as e:
            logger.error("Décodage JSON impossible : %s\nRéponse brute :\n%s", e, raw_content)
            return None
        return parsed
    except Exception as e:
        logger.error(f"Erreur lors de l'appel au LLM: {e}")
        return None

def _validate_llm_response(response: dict) -> bool:
    """
    Valide la réponse du LLM selon le schéma défini.
    
    Paramètres
    ----------
    response : dict
        Réponse JSON du LLM
    
    Retour
    ------
    bool
        True si la validation réussit, False sinon
    """
    try:
        jsonschema.validate(response, TRADE_DECISION_SCHEMA)
        return True
    except jsonschema.exceptions.ValidationError as e:
        logger.error(f"Validation JSON échouée: {e}")
        return False

def _log_decision_to_csv(decision: dict, outcome: str = "pending") -> None:
    """
    Enregistre la décision du LLM dans un fichier CSV.
    
    Paramètres
    ----------
    decision : dict
        Décision du LLM validée
    outcome : str, optional
        Résultat du trade, par défaut "pending"
    """
    csv_path = os.path.join("logs", "llm_decisions.csv")
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    header = [
        "timestamp", "symbol", "direction", "strategy",
        "entry", "sl", "tp", "confidence", "reasoning", "outcome"
    ]
    row = [
        datetime.utcnow().isoformat(timespec="seconds") + "Z",
        decision["symbol"], decision["direction"], decision["strategy"],
        decision["entry"], decision["sl"], decision["tp"],
        decision["confidence"], decision["reasoning"], outcome
    ]

    write_header = not os.path.isfile(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(header)
        writer.writerow(row)
    
    logger.info(f"Décision LLM enregistrée dans {csv_path}: {decision['symbol']} {decision['direction']}")
