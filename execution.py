import yaml
from loguru import logger
import datetime
import csv
import os
import requests

from ibkr_client import IbkrClient

# Load config
try:
    cfg = yaml.safe_load(open('config.yaml'))
except Exception as e:
    logger.error(f"Erreur lecture config.yaml : {e}")
    cfg = {}
LIVE = cfg.get('LIVE', False)
MAX_DRAWDOWN = cfg.get('MAX_DRAWDOWN', 5)
MAX_SLIPPAGE = cfg.get('MAX_SLIPPAGE', 2)
RISK_PCT = cfg.get('RISK', {}).get('risk_per_trade', 1)
WEBHOOK_URL = cfg.get('DISCORD', {}).get('webhook_url', '')

# Setup trade log CSV
LOG_FILE = os.path.join(os.path.dirname(__file__), 'trades_log.csv')
PIP_SIZE = 0.0001  # adjust per instrument if needed

def init_trade_log():
    """
    Initialise le fichier de log des trades si absent.
    """
    try:
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp','symbol','side','units','entry','stop','tp','status','exec_price','slippage_pips'])
    except Exception as e:
        logger.error(f"Erreur init_trade_log: {e}")

# Setup client
try:
    client = IbkrClient('config.yaml')
    IBKR_ONLINE = True
except Exception as e:
    logger.warning(f"API IBKR indisponible, fallback simulation: {e}")
    client = None
    IBKR_ONLINE = False

def check_drawdown(bal, nav, max_drawdown=MAX_DRAWDOWN):
    """
    Vérifie si le drawdown dépasse la limite autorisée.
    Retourne (bool, drawdown_pct)
    """
    drawdown = (bal - nav) / bal * 100 if bal else 0
    return drawdown > max_drawdown, drawdown

def check_slippage(entry, exec_price, pip_size=PIP_SIZE):
    """
    Calcule la slippage en pips.
    """
    return abs(exec_price - entry) / pip_size


def execute_trades(signals, live_override=None):
    """
    Execute ou simule les trades.
    - Bloc try/except sur chaque I/O (API, CSV, Discord)
    - Simulation si API offline
    - Logging harmonisé loguru + CSV
    - Docstring usage/exceptions
    """
    init_trade_log()
    local_live = live_override if live_override is not None else LIVE
    bal, nav = 10000, 10000  # fallback valeurs
    if local_live and IBKR_ONLINE:
        try:
            acct = client.get_account_summary()
            bal = float(acct.get('balance', 0))
            nav = float(acct.get('NAV', bal))
        except Exception as e:
            logger.error(f"Erreur API get_account_summary: {e}")
            local_live = False  # fallback simulation
    # Check drawdown
    if local_live:
        over, drawdown = check_drawdown(bal, nav)
        if over:
            logger.warning(f"Drawdown {drawdown:.2f}% > limit {MAX_DRAWDOWN}%. Aborting orders.")
            return
    for sig in signals:
        sym = sig['symbol']
        entry = sig['entry']
        stop = sig['stop']
        tp = sig['tp']
        side = sig['side']
        # Size calculation
        units = 1
        if local_live and stop and entry:
            risk_amt = bal * (RISK_PCT/100)
            pip_diff = abs(entry - stop)
            units = int(risk_amt / pip_diff) if pip_diff > 0 else 1
        # Build order payload (adapté IBKR)
        order = {
            'symbol': sym,
            'action': side,
            'quantity': units
        }
        if local_live and IBKR_ONLINE:
            try:
                resp = client.place_order(sym, side, units)
                logger.info(f"{datetime.datetime.now()} | ORDER EXECUTED | {sym} | {side} | units={units} | entry={entry} | stop={stop} | tp={tp} | resp={resp}")
                exec_price = float(getattr(resp, 'avgFillPrice', entry) or entry)
                slippage = check_slippage(entry, exec_price)
                status = 'EXECUTED'
                if slippage > MAX_SLIPPAGE:
                    logger.warning(f"Slippage {slippage:.1f} pips > limit {MAX_SLIPPAGE}.")
            except Exception as e:
                logger.error(f"Order error for {sym} {side}: {e}")
                exec_price = entry
                slippage = 0
                status = 'REJECTED'
        else:
            # simulation mode
            status = 'SIMULATED'
            exec_price = entry
            slippage = 0
            logger.info(f"SIMULATED TRADE | {sym} | {side} | units={units} | entry={entry} | stop={stop} | tp={tp}")
        # Arrondi dynamique des niveaux selon la paire
        if any(x in sym for x in ['USD', 'EUR', 'GBP', 'AUD', 'NZD', 'CAD', 'CHF']):
            ndigits = 4 if not sym.endswith('JPY') and 'JPY' not in sym else 2
        else:
            ndigits = 2
        entry_r = round(entry, ndigits)
        stop_r = round(stop, ndigits)
        tp_r = round(tp, ndigits)
        # Log CSV
        try:
            with open(LOG_FILE, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([datetime.datetime.now(), sym, side, units, entry_r, stop_r, tp_r, status, exec_price, f"{slippage:.1f}"])
        except Exception as e:
            logger.error(f"Erreur écriture CSV trade log: {e}")
        # Discord notification
        if WEBHOOK_URL:
            mode_tag = '[LIVE]' if local_live else '[SIMU]'
            emoji = '📈' if side=='BUY' else '📉'
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            msg = f"{mode_tag} {emoji} {sym} | Entry: {entry_r} | SL: {stop_r} | TP: {tp_r} | Time: {ts}"
            try:
                requests.post(WEBHOOK_URL, json={'content': msg})
            except Exception as e:
                logger.error(f"Discord notification failed: {e}")
