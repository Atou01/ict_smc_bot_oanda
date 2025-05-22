import yaml
import json
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path="C:/bot-vantage/.env")
import platform
print("[DEBUG] OPENAI_API_KEY =", os.getenv("OPENAI_API_KEY"))
if platform.system() == "Windows":
    from mt5_client import Mt5Client
else:
    from mt5_stub import Mt5Client

# Compteurs globaux pour la traçabilité
signals_recus = 0
trades_envoyes = 0
trades_bloques = 0
import datetime
import sys
import subprocess
import threading
import time
import atexit
import argparse

from llm_brain import LLMBrain
from config_validator import print_config_status
from macro_collector import MacroCollector

from structure_detector import StructureDetector
from strategy_selector import StrategySelector
from order_manager import OrderManager
from pnl_tracker import PnLTracker
from discord_utils import send_discord_notification

# [TEMP] Désactivation du bias macro : import et gestionnaire
# from macro_bias_manager import MacroBiasManager

# Chemins relatifs aux fichiers d'état/log/config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.normpath(os.path.join(BASE_DIR, '../../logs'))
CONFIG_DIR = os.path.normpath(os.path.join(BASE_DIR, '../../config'))

# Traitement des arguments de ligne de commande
parser = argparse.ArgumentParser(description="Trading Bot avec intégration LLM")
parser.add_argument('--test-llm', action='store_true', help='Simuler une réponse LLM pour tester la pipeline de trading')
args = parser.parse_args()

SHARED_STATE_PATH = os.path.join(LOGS_DIR, "shared_state.json")
TRIGGER_LLM_PATH = os.path.join(LOGS_DIR, "trigger_llm.json")
LLM_QUERY_PATH = os.path.join(LOGS_DIR, "llm_query.json")
MACRO_LOG_PATH = os.path.join(LOGS_DIR, "macro_log.json")

def read_shared_state():
    try:
        with open(SHARED_STATE_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {"bot_on": False}

def update_shared_state(state_data):
    with open(SHARED_STATE_PATH, 'w') as f:
        json.dump(state_data, f, indent=2)
    print(f"[BOT] Shared state mis à jour: {datetime.datetime.now().strftime('%H:%M:%S')}")

def log_bot_status(message):
    with open("bot.log", "a") as logf:
        logf.write(f"[{datetime.datetime.now().isoformat()}] {message}\n")

def check_llm_trigger():
    if os.path.exists(TRIGGER_LLM_PATH):
        with open(TRIGGER_LLM_PATH, 'r') as f:
            try:
                data = json.load(f)
                if data.get('trigger', False):
                    with open(TRIGGER_LLM_PATH, 'w') as f:
                        json.dump({"trigger": False, "timestamp": datetime.datetime.now().isoformat()}, f)
                    return True
            except json.JSONDecodeError:
                pass
    else:
        with open(TRIGGER_LLM_PATH, 'w') as f:
            json.dump({"trigger": False, "timestamp": datetime.datetime.now().isoformat()}, f)
    return False

def check_llm_query():
    if os.path.exists(LLM_QUERY_PATH):
        try:
            with open(LLM_QUERY_PATH, 'r') as f:
                data = json.load(f)
                query = data.get("query")
                timestamp = data.get("timestamp")
                context = data.get("context")
                if query and timestamp:
                    query_time = datetime.datetime.fromisoformat(timestamp)
                    now = datetime.datetime.now()
                    if (now - query_time).total_seconds() < 300:
                        return query, context
        except Exception as e:
            print(f"[BOT][ERREUR] Impossible de lire la requête LLM: {e}")
    return None, None

def smart_llm_trigger():
    """ Détecte une news macro HIGH/MEDIUM imminente (<10min) dans macro_log.json """
    try:
        if not os.path.exists(MACRO_LOG_PATH):
            return False
        with open(MACRO_LOG_PATH, "r") as f:
            log = json.load(f)
        now = datetime.datetime.now()
        for ev in log.get("recent_events", []):
            if ev.get("impact", "").lower() in ("high", "medium"):
                ev_time = datetime.datetime.fromisoformat(ev["date"] if "date" in ev else ev.get("timestamp"))
                if 0 <= (ev_time - now).total_seconds() < 600:
                    print(f"[BOT] Appel LLM forcé : news macroéconomique majeure imminente (impact: {ev['impact']})")
                    return True
    except Exception as e:
        print(f"[BOT][ERREUR] smart_llm_trigger: {e}")
    return False

def cleanup():
    print("\n[BOT] Arrêt du bot en cours...")
    try:
        macro_collector.stop_auto_update()
        print("[BOT] Collecteur de données macroéconomiques arrêté")
    except:
        pass

atexit.register(cleanup)

# ----------------- CONFIGURATION INITIALE -----------------

# --- Initialisation du client MT5 (Windows ou Stub Mac) ---
mt5_login = os.getenv("VANTAGE_LOGIN")
mt5_pwd = os.getenv("VANTAGE_PWD")
mt5_server = os.getenv("VANTAGE_SERVER")

# Fallback sur config.yaml si .env absent
if not (mt5_login and mt5_pwd and mt5_server):
    try:
        with open(os.path.join(CONFIG_DIR, "config.yaml")) as f:
            config_yaml = yaml.safe_load(f)
        mt5_login = mt5_login or config_yaml.get("MT5_LOGIN")
        mt5_pwd = mt5_pwd or config_yaml.get("MT5_PWD")
        mt5_server = mt5_server or config_yaml.get("MT5_SERVER")
        print("[MT5][INFO] Paramètres chargés depuis config.yaml (fallback)")
    except Exception as e:
        print(f"[MT5][ERREUR] Impossible de charger les identifiants MT5 : {e}")

mt5 = Mt5Client()
connected = mt5.initialize(mt5_login, mt5_pwd, mt5_server)

import platform
if platform.system() != "Windows":
    print("[MT5][INFO] Stub Mac/Linux activé : pas de connexion réelle à MT5 (développement/simulation)")
else:
    if connected:
        print(f"[MT5][OK] Connexion MT5 établie pour le compte {mt5_login} sur {mt5_server}")
    else:
        print("[MT5][ERREUR] Connexion MT5 échouée : vérifiez les identifiants et la plateforme.")

try:
    with open(os.path.join(CONFIG_DIR, "config.yaml")) as f:
        cfg = yaml.safe_load(f)
    if not print_config_status(cfg):
        print("[ERREUR] Configuration invalide. Arrêt du bot.")
        sys.exit(1)
    print("[CONFIG] ✅ Tous les paramètres obligatoires sont présents.")
except Exception as e:
    print(f"[ERREUR] Problème lors du chargement de la configuration: {e}")
    sys.exit(1)

# --- Initialisation composants ---
api_key = cfg["OPENAI"]["api_key"]

# Vérifier si le mode debug est activé
debug_llm = os.environ.get("DEBUG_LLM", "False").lower() == "true"

# Initialiser le LLM avec OpenAI
llm = LLMBrain(api_key=api_key, debug_mode=debug_llm)

# Créer une instance globale pour le partage entre modules
import sys
sys.modules['llm_brain']._llm_instance = llm

# [TEMP] Désactivation du bias macro : initialisation du gestionnaire
macro_bias_manager = None  # Pour réactiver : décommentez la ligne ci-dessous
# macro_bias_manager = MacroBiasManager(
#     freeze_minutes_before=30,  # 30 minutes avant l'événement
#     freeze_minutes_after=10    # 10 minutes après l'événement
# )
# print(f"[BOT] Gestionnaire de biais macro initialisé")

macro_collector = MacroCollector(
    xml_url=cfg["XML_FEED_URL"],
    update_interval=cfg.get("XML_UPDATE_INTERVAL", 1800),
    filter_impact=cfg.get("XML_FILTER_IMPACT", []),
    filter_countries=cfg.get("XML_FILTER_COUNTRIES", []),
    filter_keywords=cfg.get("XML_FILTER_KEYWORDS", []),
    output_format=cfg.get("XML_OUTPUT_FORMAT", "detailed")
)
print(f"[BOT] Collecteur macro (XML) initialisé")
macro_collector.start_auto_update()





initial_capital = float(cfg.get('RISK', {}).get('capital', 10000))
pnl_tracker = PnLTracker(initial_capital=initial_capital)
order_manager = OrderManager(cfg, pnl_tracker, ib=None)
detector = StructureDetector()
selector = StrategySelector(llm, macro_bias_manager=macro_bias_manager)


# Utilisation de la même instance IB déjà connectée


# -- Lancement suivi trades en thread
trade_monitor_thread = threading.Thread(target=order_manager.monitor_trades, daemon=True)
trade_monitor_thread.start()

# ----------------- MAIN LOOP -----------------

last_llm_call = datetime.datetime.now() - datetime.timedelta(hours=1)
llm_interval = 1800  # 30 minutes par défaut

# Initialisation correcte de l'état initial du bot
state = read_shared_state()
last_bot_on = state.get("bot_on", False)
while True:
    # Contrôle centralisé via dashboard
    state = read_shared_state()
    bot_on = state.get("bot_on", False)
    # Détection de changement d'état AVANT le bloc pause
    if bot_on != last_bot_on:
        print(f"[DEBUG] Changement d'état bot_on détecté : {last_bot_on} -> {bot_on}")
        if not bot_on:
            print("[DEBUG] Appel send_discord_notification (pause)")
            send_discord_notification(" **Bot mis en pause.** Toutes les opérations sont suspendues.", type="security")
        else:
            print("[DEBUG] Appel send_discord_notification (reprise)")
            send_discord_notification(" **Bot réactivé.** Reprise des opérations.", type="security")
        last_bot_on = bot_on
    if not bot_on:
        print("[BOT] Désactivé (pause). En attente du signal ON...")
        log_bot_status("[BOT] Désactivé (pause). En attente du signal ON…")
        time.sleep(3)
        continue

    
    

    # Récupération contexte macro - uniquement les événements des prochaines 24h
    macro_format = cfg.get("XML_OUTPUT_FORMAT", "summary")
    macro_data = macro_collector.get_macro_context(format=macro_format, hours_ahead=24)

    # Détection structures
    fvg_signals = detector.detect_fvg()
    ob_signals = detector.detect_ob()
    bos_signals = detector.detect_bos()
    sweep_signals = detector.detect_sweep()
    structures_text = [
        f"{s['type']} {s['side']} sur {s['timeframe']}"
        for s in (fvg_signals + ob_signals + bos_signals + sweep_signals)
    ]
    pnl_summary = "Risque défini à 1%, drawdown max 3% atteint hier."

    # Déclenchement LLM : timer, smart trigger, ou bouton dashboard
    now = datetime.datetime.now()
    # Contrôle strict de la fréquence des appels LLM :
    # - Toutes les 30 minutes (llm_interval)
    # - OU si un événement macro HIGH/MEDIUM imminent est détecté (smart_llm_trigger)
    force_macro = smart_llm_trigger()
    force_dashboard = check_llm_trigger()
    force_test = args.test_llm
    if (now - last_llm_call).total_seconds() > llm_interval or force_macro or force_dashboard or force_test:
        if force_test:
            print(f"[BOT] Simulation LLM pour test de la pipeline de trading")
            # Générer une recommandation simulée pour le test
            
            # Obtenir le prix actuel pour EUR_USD
            current_price = 1.0750  # Prix fictif pour le test, idéalement récupéré du broker
            
            # Générer une recommandation avec des prix réalistes
            
            simulated_response = {
                "symbol": "EURUSD",
                "action": "BUY",
                "strategy": "ICT_BOS",
                "confidence": 0.85,
                "reason": "Test de la pipeline d'exécution LLM",
                "risk_reward": 2.5,
                "stop_loss": 25,  # en pips
                "take_profit": 62,  # en pips
                "entry_price": current_price  # Prix d'entrée pour le test
            }
            
            # Vérifier si la recommandation est valide via StrategySelector
            trade_validity = selector.should_trade_from_llm(simulated_response)
            
            print(f"[BOT][TEST] Recommandation LLM simulée: {json.dumps(simulated_response, indent=2)}")
            print(f"[BOT][TEST] Validation StrategySelector: {trade_validity}")
            
            if trade_validity:
                print(f"[BOT][TEST] La recommandation LLM est valide, tentative de placement d'ordre...")
                # Préparation du signal formaté pour l'OrderManager
                entry_price = simulated_response.get('entry_price', 1.0750)  # Prix fictif si non spécifié
                stop_pips = simulated_response.get('stop_loss', 25)
                take_pips = simulated_response.get('take_profit', 62)
                
                # Calcul des niveaux de SL et TP en fonction de l'action (BUY/SELL)
                is_buy = simulated_response['action'].upper() == 'BUY'
                
                # Pour un achat: SL = entry - pips, TP = entry + pips
                # Pour une vente: SL = entry + pips, TP = entry - pips
                sl_price = entry_price - (stop_pips / 10000) if is_buy else entry_price + (stop_pips / 10000)
                tp_price = entry_price + (take_pips / 10000) if is_buy else entry_price - (take_pips / 10000)
                
                print(f"[DEBUG] Prix calculés pour test LLM: Entry={entry_price}, SL={sl_price:.5f}, TP={tp_price:.5f}")
                
                signal = {
                    'symbol': simulated_response['symbol'],
                    'side': simulated_response['action'],
                    'timeframe': 'LLM',  # Pour le test LLM
                    'strategy': simulated_response['strategy'],
                    'confidence': simulated_response['confidence'],
                    'reason': f"LLM: {simulated_response['reason']}",
                    'sl_pips': stop_pips,
                    'tp_pips': take_pips,
                    'entry': entry_price,  # Prix d'entrée simulé
                    'sl': sl_price,    # Prix de stop loss calculé
                    'tp': tp_price     # Prix de take profit calculé
                }
                
                # Tentative de placement d'ordre si en mode non-simulation
                if cfg.get('BROKER', {}).get('mode', 'Simulation').lower() not in ['simulation', 'backtest']:
                    try:
                        print(f"[BOT][TEST] Tentative de placement d'ordre en mode {cfg.get('BROKER', {}).get('mode')}...")
                        # Afficher les détails du signal avant placement
                        print(f"[BOT][TEST] Détails du signal: \n{json.dumps(signal, indent=2)}")
                        # Réinitialiser les signaux LLM précédents pour éviter le message "Trade déjà actif"
                        if force_test:
                            print(f"[BOT][TEST] Réinitialisation des signaux LLM précédents...")
                            order_manager.reset(only_llm_signals=True)
                        # Tester la connexion au broker avant placement
                        
                        
                        try:
                            
                            print(f"[BOT][TEST] Compte actif: {account_details['account']}")
                        except Exception as e:
                            import traceback
                            print(f"[BOT][TEST] Erreur lors du placement d'ordre: {e}")
                            print(f"[BOT][TEST] Détails de l'erreur:\n{traceback.format_exc()}")
                            # Essayer de récupérer plus d'informations
                            if hasattr(e, 'reqId') and hasattr(e, 'errorCode'):
                                pass
                            if hasattr(e, '__dict__'):
                                print(f"[BOT][TEST] Attributs erreur: {e.__dict__}")
                            # Vérifier si l'erreur vient d'une mauvaise configuration du contrat
                            print(f"[BOT][TEST] Vérification du contrat pour {signal['symbol']}...")
                    except Exception as e:
                        import traceback
                        print(f"[BOT][TEST] Erreur critique lors du placement d'ordre: {e}")
                        print(traceback.format_exc())
                    # ici tu peux ajouter un else: si tu veux du code qui ne s'exécute qu'en cas de succès total
                else:
                    print(f"[BOT][TEST] Mode simulation: ordre non placé mais signal validé: {json.dumps(signal, indent=2)}")
                    log_bot_status(f"TEST LLM: Recommandation validée et traitée - {simulated_response['symbol']} {simulated_response['action']}")
            else:
                print(f"[BOT][TEST] La recommandation LLM n'a pas passé la validation")
                log_bot_status(f"TEST LLM: Recommandation rejetée - {simulated_response['symbol']} {simulated_response['action']}")

            # On arrête après ce test pour éviter de continuer le flux normal
            if force_test and not (force_macro or force_dashboard):
                print("[BOT][TEST] Test LLM terminé, attente du prochain cycle...")
                time.sleep(10)  # Pause courte avant de continuer
                continue
                
        elif force_macro:
            print(f"[BOT] Appel LLM déclenché par événement macroéconomique majeur")
        elif force_dashboard:
            print(f"[BOT] Appel LLM déclenché manuellement via le dashboard")
        else:
            print(f"[BOT] Appel LLM périodique ({int((now - last_llm_call).total_seconds() // 60)} minutes écoulées)")
        context = {
            'macro': macro_data,
            'structures': structures_text,
            'pnl': pnl_summary,
            'account': {}
        }
        # Récupérer la stratégie, le nom et les biais par devise
        # Déclencher l'intelligence artificielle
        strategie_complete, strategie_nom, currency_biases = llm.analyze_context_and_choose_strategy(
            context,
            macro_format=macro_format
        )
        strategie = strategie_complete  # Pour compatibilité arrière
        last_llm_call = now
        
        # Mettre à jour shared_state avec les biais actuels
        state["currency_biases"] = currency_biases
        state["llm_strategy_nom"] = strategie_nom
        update_shared_state(state)
        
        # ****** DÉBUT PIPELINE D'EXÉCUTION AUTOMATIQUE ******
        # Récupérer le statut de risque depuis le pnl_tracker
        risk_status = pnl_tracker.get_risk_status()
        
        # Si on est en mode test, ajout de max_risk_pct pour éviter KeyError dans order_manager
        if force_test:
            risk_pct = float(cfg.get('RISK', {}).get('risk_pct', 1.0))
            risk_status["max_risk_pct"] = risk_pct  # Ajout de la clé manquante pour le test
            print(f"[BOT][TEST] Risk status complété avec max_risk_pct={risk_pct}%")
            
        # Générer une recommandation de trading structurée
        print(f"[BOT][LLM] Génération de recommandation de trading basée sur l'analyse...")
        trade_recommendation = llm.generate_trade_recommendation(
            macro_analysis=strategie_complete,
            technical_analysis=f"Structures détectées: {structures_text}",
            risk_status=risk_status
        )
        
        if trade_recommendation:
            print(f"[BOT][LLM] Recommandation de trading reçue: {json.dumps(trade_recommendation, indent=2)}")
            
            # Vérifier si la recommandation est valide via StrategySelector
            trade_validity = selector.should_trade_from_llm(trade_recommendation)
            
            if trade_validity:
                print(f"[BOT][LLM] La recommandation a passé la validation, exécution de l'ordre...")
                
                # Préparation du signal formaté pour l'OrderManager
                signal = {
                    'pair': trade_validity.get('symbol', ''),
                    'direction': trade_validity.get('side', ''),
                    'strategy': trade_validity.get('type', 'LLM_AUTO'),
                    'confidence': trade_validity.get('confidence', 0.75),
                    'reason': f"LLM: {trade_validity.get('reason', 'Recommandation automatique')}",
                    'sl_pips': trade_recommendation.get('stop_loss', 30),  # Valeur par défaut si non spécifiée
                    'tp_pips': trade_recommendation.get('take_profit', 60)  # Valeur par défaut si non spécifiée
                }
                
                # Exécution de l'ordre si en mode demo ou live
                if cfg.get('BROKER', {}).get('mode', 'Simulation').lower() not in ['simulation', 'backtest']:
                    try:
                        result = order_manager.place_trade(signal, float(cfg['RISK']['risk_pct'])/100)
                        log_bot_status(f"LLM Trade: Exécution automatique - {signal['pair']} {signal['direction']} via {signal['strategy']}")
                        print(f"[BOT][LLM] Ordre placé avec succès: {result}")
                    except Exception as e:
                        print(f"[BOT][LLM][ERREUR] Placement d'ordre échoué: {e}")
                        log_bot_status(f"LLM Trade: Erreur d'exécution - {signal['pair']} {signal['direction']} - {e}")
                else:
                    print(f"[BOT][LLM][SIMULATION] Ordre simulé: {json.dumps(signal, indent=2)}")
                    log_bot_status(f"LLM Trade: SIMULATION - {signal['pair']} {signal['direction']} via {signal['strategy']}")
            else:
                print(f"[BOT][LLM] La recommandation n'a pas passé la validation, aucun ordre placé")
                log_bot_status(f"LLM Trade: Recommandation rejetée - Validation échouée")
        else:
            print(f"[BOT][LLM] Aucune recommandation de trading générée pour le contexte actuel")
            log_bot_status("LLM Trade: Aucune recommandation générée")
        last_llm_call = now
    else:
        print(f"[BOT] Pas d'appel LLM cette boucle (next in {(llm_interval - (now - last_llm_call).total_seconds()):.0f}s)")
        strategie = state.get("llm_strategy", "[LLM] En attente de prochaine analyse...")

    # Routage stratégie / génération signaux
    # Utiliser le tuple complet (stratégie, nom, biais) s'il est disponible
    if 'llm_strategy_nom' in state and 'currency_biases' in state:
        strategy_input = (strategie, state['llm_strategy_nom'], state['currency_biases'])
    else:
        strategy_input = strategie
        
    signals = selector.route_strategy(strategy_input)

    # --- Affichage intelligent du plan de trade ---
    # On affiche seulement si la stratégie OU les signaux changent
    if not hasattr(order_manager, '_last_strategy_used'):
        order_manager._last_strategy_used = None
        order_manager._last_signals_used = None

    # Utilisation d'un hash simple pour les signaux (tuple de dicts triés)
    def signals_hash(signals):
        return tuple(sorted(str(s) for s in signals)) if signals else None

    changed = False
    if strategie != order_manager._last_strategy_used:
        changed = True
    elif signals_hash(signals) != order_manager._last_signals_used:
        changed = True

    if changed:
        order_manager.print_trade_plan(signals)
        # Notification Discord changement de stratégie ou nouveaux signaux
        try:
            msg = f" **Changement de stratégie détecté !**\nNouvelle stratégie : `{strategie}`"
            if signals:
                msg += f"\n\n**Signaux détectés :**\n"
                for sig in signals:
                    msg += f"- {sig['type']} {sig['side']} sur {sig['timeframe']} (SL: {sig['sl']} / TP: {sig['tp']} / sizing: {sig['sizing']})\n"
            send_discord_notification(msg, type="notif")
        except Exception:
            pass
        order_manager._last_strategy_used = strategie
        order_manager._last_signals_used = signals_hash(signals)
    last_signal = signals[0] if signals else None

    # PnL & risk
    try:
        pnl_tracker.update()
        pnl_data = pnl_tracker.export_summary()
        risk_status = pnl_tracker.get_risk_status()
        print(f"[BOT][PnL] Réalisé: {pnl_data['realized']}€ | Non réalisé: {pnl_data['unrealized']}€ | DD Max: {pnl_data['drawdown_max']}% | Trades: {pnl_data['winning_trades']}/{pnl_data['losing_trades']}")
        print(f"[BOT][RISK] {risk_status['status_message']} | Trading autorisé: {'OUI' if risk_status['trading_allowed'] else 'NON'}")
    except Exception as e:
        print(f"[BOT][ERREUR] Impossible de mettre à jour le PnL: {e}")
        pnl_data = {
            "open_trades": len(order_manager.active_trades),
            "realized": 0.0,
            "unrealized": 0.0,
            "drawdown_max": float(cfg.get('MAX_DRAWDOWN', 5)),
            "winning_trades": 0,
            "losing_trades": 0,
            "error": str(e)
        }
        risk_status = {
            "risk_pct": 0.5,
            "drawdown": 0.0,
            "trading_allowed": False,
            "status_message": "Erreur dans le calcul du risque"
        }

    # Vérification des événements macroéconomiques imminents toutes les 60 secondes environ
    if round(time.time()) % 60 == 0:
        try:
            # Vérifier s'il y a des événements importants dans les 45 prochaines minutes
            imminent_events = macro_collector.check_imminent_events(minutes_threshold=45)
            if imminent_events:
                print(f"[BOT] {len(imminent_events)} événements macroéconomiques imminents détectés")
                # Mettre à jour les périodes de gel via le MacroBiasManager
                for event in imminent_events:
                    country = event.get('country', '')
                    impact = event.get('impact', '')
                    title = event.get('title', '')
                    time_str = event.get('time', '')
                    date_str = event.get('date', '')
                    
                    if country and impact in ['High', 'Medium']:
                        # Extraire le timestamp de l'événement
                        event_time = None
                        if 'timestamp' in event and event['timestamp']:
                            try:
                                event_time = datetime.datetime.fromisoformat(event['timestamp'])
                            except ValueError:
                                pass
                        
                        if not event_time and date_str and time_str:
                            # Essayer de reconstruire le timestamp à partir de date et time
                            event_time = macro_collector._parse_event_datetime(date_str, time_str)
                            if event_time:
                                try:
                                    event_time = datetime.datetime.fromisoformat(event_time)
                                except ValueError:
                                    event_time = None
                        
                        if event_time:
                            # Ajouter la période de gel
                            macro_bias_manager.add_freeze_period(country, event_time)
                            print(f"[BOT] Période de gel ajoutée pour {country}: {title} ({impact}) à {time_str}")
        except Exception as e:
            print(f"[BOT][ERREUR] Vérification des événements imminents: {e}")

    # Synchronisation dashboard
    shared_state = {
        "mode": cfg.get('MODE', 'Simulation'),
        "timestamp": datetime.datetime.now().isoformat(),
        "bot_on": state.get("bot_on", True),
        "macro_context": macro_data,
        "structures_detected": {
            "fvg": fvg_signals,
            "ob": ob_signals,
            "bos": bos_signals,
            "sweep": sweep_signals
        },
        "llm_strategy": strategie,
        "last_signal": last_signal,
        "pnl_summary": pnl_data,
        "risk_status": risk_status,
        "account_summary": None
    }
    update_shared_state(shared_state)

    # Passage mode LIVE/DEMO
    mode = cfg.get('MODE', 'Simulation')
    if mode.lower() != 'simulation':
        for signal in signals:
            try:
                order_manager.place_trade(signal, float(cfg['RISK']['risk_pct'])/100)
            except Exception as e:
                print(f"[BOT][ERREUR] Impossible de placer l'ordre : {e}")

    # Traitement requête LLM (depuis dashboard)
    query, context = check_llm_query()
    if query:
        print(f"[BOT][LLM] Traitement de la requête utilisateur: {query[:50]}...")
        try:
            if not context:
                context = {
                    'macro': macro_data,
                    'structures': structures_text,
                    'pnl': pnl_summary,
                    'account': {}
                }
            response = llm.analyze_query(query, context=context)
            with open(os.path.join(LOGS_DIR, "llm_response.json"), 'w') as f:
                json.dump({
                    "query": query,
                    "response": response,
                    "timestamp": datetime.datetime.now().isoformat()
                }, f, indent=2)
            print(f"[BOT][LLM] Réponse générée et sauvegardée")
            if os.path.exists(LLM_QUERY_PATH):
                os.remove(LLM_QUERY_PATH)
        except Exception as e:
            print(f"[BOT][ERREUR] Impossible de traiter la requête LLM: {e}")

    # Sauvegarde PnL
    if hasattr(pnl_tracker, 'save_history_to_json') and round(time.time()) % 5 == 0:
        try:
            pnl_tracker.save_history_to_json()
        except Exception as e:
            print(f"[BOT][ERREUR] Impossible de sauvegarder l'historique PnL: {e}")

    # Mise à jour stats toutes les 50 trades
    total_trades = pnl_data.get('winning_trades', 0) + pnl_data.get('losing_trades', 0)
    if total_trades > 0 and total_trades % 50 == 0:
        try:
            print(f"[BOT] {total_trades} trades exécutés, mise à jour des statistiques de stratégies...")
            subprocess.run([sys.executable, os.path.join(BASE_DIR, "update_strategy_stats.py")], check=True)
            llm.load_strategy_stats()
            print(f"[BOT] Statistiques de stratégies mises à jour.")
        except Exception as e:
            print(f"[BOT][ERREUR] Impossible de mettre à jour les stats de stratégies: {e}")

    # Reload config si modifiée (mode switch, etc.)
    if os.path.exists(os.path.join(CONFIG_DIR, 'config.yaml')):
        try:
            with open(os.path.join(CONFIG_DIR, 'config.yaml')) as f:
                current_cfg = yaml.safe_load(f)
                if current_cfg.get('MODE') != cfg.get('MODE'):
                    cfg = current_cfg
                    print(f"[BOT] Mode changé vers : {cfg.get('MODE')}")
        except Exception as e:
            print(f"[BOT][ERREUR] Impossible de recharger la config : {e}")

    # Si en mode test et c'était le premier cycle, on sort après le test
    if args.test_llm and now - datetime.datetime.fromtimestamp(0) < datetime.timedelta(minutes=2):
        print("[BOT][TEST] Test LLM terminé avec succès, arrêt du bot.")
        break
        
    time.sleep(30 if 'demo' in mode.lower() else 30)  # 30s pour plus de réactivité

# ----------------- FONCTIONS UTILITAIRES -----------------

def place_manual_order(symbol="EURUSD", side="BUY", stop_loss_pips=20, take_profit_pips=40, size=0.01):
    """
    Place un ordre manuel pour tester l'intégration broker sans passer par le LLM.
    
    Args:
        symbol (str): Symbole de la paire de devises (ex: "EURUSD")
        side (str): Direction du trade ("BUY" ou "SELL")
        stop_loss_pips (int): Distance du stop loss en pips
        take_profit_pips (int): Distance du take profit en pips
        size (float): Taille de position en lots (0.01 = 1000 unités) 
    """
    from datetime import datetime
    
    print(f"\n{'='*50}")
    print(f"PLACEMENT D'ORDRE MANUEL POUR TEST BROKER")
    print(f"{'='*50}")
    
    # S'assurer que le broker est connecté
    try:
        print("\n[TEST] Vérification de la connexion broker...")
        
        
        
        if not is_connected:
            print("[TEST] ERREUR: Le broker n'est pas connecté!")
            print("[TEST] Assurez-vous que les API sont activées et que le port est correct.")
            return False
            
        print(f"[TEST] Connexion broker établie: {is_connected}")
        
        # Obtention des détails du compte
        try:
            
            print(f"[TEST] Compte actif: {account_details['account']}")
            print(f"[TEST] Balance: {account_details['balance']}")
        except Exception as account_err:
            print(f"[TEST] Erreur lors de la récupération du compte: {account_err}")
        
        # Construction du signal manuel
        
        if not current_price:
            print(f"[TEST] ERREUR: Impossible d'obtenir le prix actuel pour {symbol}")
            return False
            
        print(f"[TEST] Prix actuel de {symbol}: {current_price}")
        
        # Calcul des niveaux en fonction de la direction
        if side.upper() == "BUY":
            sl_price = round(current_price - (stop_loss_pips / 10000), 5)
            tp_price = round(current_price + (take_profit_pips / 10000), 5)
        else:  # SELL
            sl_price = round(current_price + (stop_loss_pips / 10000), 5)
            tp_price = round(current_price - (take_profit_pips / 10000), 5)
        
        # Création du signal avec toutes les informations nécessaires
        manual_signal = {
            "symbol": symbol,
            "side": side.upper(),
            "strategy": "MANUAL_TEST",  # Type de stratégie
            "confidence": 1.0,  # Confiance maximale
            "reason": "Test manuel d'ordre via broker",
            "risk_reward": take_profit_pips / stop_loss_pips,
            "sl_pips": stop_loss_pips,
            "tp_pips": take_profit_pips,
            "entry": current_price,
            "sl": sl_price,
            "tp": tp_price,
            "timeframe": "MANUAL",
            "source": "MANUAL",
            "sizing": size  # Taille en lots
        }
        
        # Affichage des détails
        print("\n[TEST] Détails de l'ordre manuel:")
        for key, value in manual_signal.items():
            print(f"  {key}: {value}")
            
        # Confirmation
        print("\n[TEST] Envoi de l'ordre au broker...")
        
        # Initialisation du gestionnaire d'ordres
        from order_manager import OrderManager
        order_manager = OrderManager(config)
        
        # Placement de l'ordre
        risk_pct = float(config['RISK']['risk_pct']) / 100
        print(f"[TEST] Risque configuré: {risk_pct*100}%")
        
        # Tentative de placement de l'ordre
        result = order_manager.place_trade(manual_signal, risk_pct)
        
        if result:
            print(f"\n[TEST] SUCCÈS: Ordre placé avec succès!")
            print(f"[TEST] Identifiant de l'ordre: {result}")
            print(f"[TEST] L'ordre est maintenant en surveillance par le système.")
            return True
        else:
            print(f"\n[TEST] ÉCHEC: Impossible de placer l'ordre! Voir les logs pour plus de détails.")
            return False
            
    except Exception as e:
        import traceback
        print(f"\n[TEST] ERREUR CRITIQUE lors du placement de l'ordre manuel:")
        print(traceback.format_exc())
        return False

# ----------------- FIN MAIN -----------------
