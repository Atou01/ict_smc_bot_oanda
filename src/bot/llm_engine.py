"""
llm_engine.py
Module d'intelligence artificielle encapsé et découplé du reste du code.
Analyse les données de marché, signaux ICT et événements macro pour générer
une recommandation de trading unique, sans biais directionnel.
"""

import os
import csv
import json
import time
import logging
from typing import Optional, Tuple
from datetime import datetime

import openai
import portalocker

__version__ = "1.0.0"
__all__ = ["decide_trade", "update_trade_outcome"]

# Configuration du logger
logger = logging.getLogger("llm_engine")
logger.setLevel(logging.INFO)

# Configurer le handler de logging s'il n'existe pas déjà
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(h)

# Exemple de prompts pour LONG et SHORT
EXAMPLE_BLOCK = """
### EXEMPLE LONG
INPUT:
    EURUSD:
        HTF_structure: bullish
        OB_H4: 1.0825
        BOS_H1: 1.0860
    Macro: 
        USD: CPI moins élevé que prévu (impact élevé)
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

# Template de prompt système final
PROMPT_SYSTEM_TEMPLATE = """
Tu es « ICT-SMC Autonomous Trader v1 ».  
But : choisir UN seul trade optimal sur le marché FX à partir des données fournies.

Contraintes :
1. Analyse au minimum 3 paires majeures avant de décider.  
2. Évalue systématiquement LONG **et** SHORT, prouve-le dans `reasoning`.  
3. Tiens compte : sessions (Asia/Ldn/Ny), spread actuel & prochaines news.  
4. Réponds EXCLUSIVEMENT en JSON conforme : 
   {{symbol, direction, strategy, entry, sl, tp, confidence, reasoning}}  
5. `reasoning` ≤ 300 car., style télégraphique (phrases courtes, pas de blabla).

{examples}

### Rappel sessions & spread  
- Évite d'ouvrir un trade 5 min avant/after une high-impact news.  
- Ignore les paires dont le spread > 2× leur moyenne.

### DONNÉES RÉELLES
{payload}
""".strip()

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
    logger.info(f"[LLM Engine] Module appelé avec payload contenant {len(payload.get('market_data', {}))} paires")
    
    # Construire le prompt
    system_prompt, user_prompt = _construct_prompt(payload)
    logger.debug(f"[LLM Engine] Prompt construit avec succès ({len(system_prompt) + len(user_prompt)} caractères)")
    
    # Appeler le LLM
    raw_json = _call_llm(system_prompt, user_prompt)
    if raw_json is None:
        logger.error("[LLM Engine] Échec de l'appel LLM ou réponse invalide")
        return None
    
    # Valider la réponse
    if not _validate_llm_response(raw_json):
        logger.error("[LLM Engine] Réponse LLM invalide")
        return None
    
    # Enregistrer dans le CSV
    _log_decision_to_csv(raw_json)
    
    return raw_json

def _construct_prompt(payload: dict) -> Tuple[str, str]:
    """
    Construit le prompt système + user :
      – section système (règles, exemples LONG/SHORT)
      – section user (données réelles du jour)
      
    Retourne un tuple (system_prompt, user_prompt)
    """
    system_prompt = PROMPT_SYSTEM_TEMPLATE.format(
        examples=EXAMPLE_BLOCK,
        payload=json.dumps(payload, ensure_ascii=False, indent=2)
    )
    
    # On sépare clairement les rôles
    return system_prompt, ""  # user prompt vide, car tout est déjà inclus

def _call_llm(system_prompt: str, user_prompt: str) -> Optional[dict]:
    """
    Appelle le LLM avec le prompt construit et gère les erreurs
    avec un mécanisme de retry/back-off exponentiel
    """
    delays = [2, 4, 8]  # expo back-off
    
    for attempt, delay in enumerate(delays, 1):
        try:
            # Utilisation de l'API OpenAI selon la version disponible
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=250,
                response_format={"type": "json_object"}
            )
            return json.loads(resp.choices[0].message["content"])
            
        except openai.error.RateLimitError as e:
            logger.warning("Retry %s/3 après erreur OpenAI (rate limit) : %s", attempt, e)
            time.sleep(delay)
            
        except openai.error.APIError as e:
            logger.warning("Retry %s/3 après erreur OpenAI (API) : %s", attempt, e)
            time.sleep(delay)
            
        except Exception as e:
            logger.error("Erreur LLM non récupérable : %s", e)
            break
            
    return None

def _validate_llm_response(response: dict) -> bool:
    """
    Valide que la réponse du LLM contient tous les champs requis
    et que les valeurs sont du bon type
    """
    required_fields = [
        "symbol", "direction", "strategy", 
        "entry", "sl", "tp", "confidence", "reasoning"
    ]
    
    # Vérifier que tous les champs requis sont présents
    for field in required_fields:
        if field not in response:
            logger.error(f"Champ requis manquant dans la réponse LLM: {field}")
            return False
    
    # Vérifier le type des champs numériques
    numeric_fields = ["entry", "sl", "tp", "confidence"]
    for field in numeric_fields:
        if not isinstance(response[field], (int, float)):
            logger.error(f"Le champ {field} doit être un nombre, reçu: {type(response[field])}")
            return False
    
    # Vérifier les contraintes spécifiques
    if response["direction"] not in ["LONG", "SHORT"]:
        logger.error(f"Direction invalide: {response['direction']}")
        return False
    
    if not (0 <= response["confidence"] <= 1):
        logger.error(f"Confidence doit être entre 0 et 1, reçu: {response['confidence']}")
        return False
    
    # Vérifier la cohérence des prix (SL/TP par rapport à l'entrée selon direction)
    if response["direction"] == "LONG":
        if response["sl"] >= response["entry"]:
            logger.error(f"SL doit être inférieur à l'entrée pour un LONG")
            return False
        if response["tp"] <= response["entry"]:
            logger.error(f"TP doit être supérieur à l'entrée pour un LONG")
            return False
    else:  # SHORT
        if response["sl"] <= response["entry"]:
            logger.error(f"SL doit être supérieur à l'entrée pour un SHORT")
            return False
        if response["tp"] >= response["entry"]:
            logger.error(f"TP doit être inférieur à l'entrée pour un SHORT")
            return False
    
    return True

def _log_decision_to_csv(decision: dict, outcome: str = "pending") -> None:
    """
    Enregistre la décision dans un fichier CSV avec file-lock pour éviter les collisions
    Format: timestamp, symbol, direction, strategy, entry, sl, tp, confidence, reasoning, outcome
    """
    csv_path = os.path.join("logs", "llm_decisions.csv")
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    header = ["timestamp", "symbol", "direction", "strategy",
              "entry", "sl", "tp", "confidence", "reasoning", "outcome"]
    row = [datetime.utcnow().isoformat(timespec="seconds")+"Z",
           decision["symbol"], decision["direction"], decision["strategy"],
           decision["entry"], decision["sl"], decision["tp"],
           decision["confidence"], decision["reasoning"], outcome]

    mode = "a" if os.path.isfile(csv_path) else "w"
    try:
        with portalocker.Lock(csv_path, mode, timeout=5) as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            if mode == "w":
                writer.writerow(header)
            writer.writerow(row)
        logger.info("Décision LLM enregistrée: %s %s", decision["symbol"], decision["direction"])
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement CSV: {e}")

def update_trade_outcome(symbol: str, ts_iso: str, result: str) -> None:
    """
    Remplit la colonne outcome après clôture (result=win/loss/be).
    
    Paramètres
    ----------
    symbol : str
        Symbole de la paire
    ts_iso : str
        Timestamp ISO de la décision à mettre à jour
    result : str
        Résultat du trade (win/loss/be)
    """
    csv_path = os.path.join("logs", "llm_decisions.csv")
    tmp_path = csv_path + ".tmp"

    try:
        with portalocker.Lock(csv_path, "r", timeout=5) as fin, \
             portalocker.Lock(tmp_path, "w", timeout=5) as fout:
            reader, writer = csv.reader(fin), csv.writer(fout)
            header = next(reader)
            writer.writerow(header)
            
            updated = False
            for row in reader:
                if row[0] == ts_iso and row[1] == symbol:
                    row[-1] = result
                    updated = True
                writer.writerow(row)
                
        os.replace(tmp_path, csv_path)
        if updated:
            logger.info(f"Outcome mis à jour pour {symbol} ({ts_iso}): {result}")
        else:
            logger.warning(f"Aucune décision trouvée pour {symbol} ({ts_iso})")
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de l'outcome: {e}")
        # Nettoyage en cas d'erreur
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
