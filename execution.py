import yaml
import logging
import datetime
import csv
import os
import requests

from ibkr_client import IbkrClient

# Load config
cfg = yaml.safe_load(open('config.yaml'))
LIVE = cfg.get('LIVE', False)
MAX_DRAWDOWN = cfg.get('MAX_DRAWDOWN', 5)
MAX_SLIPPAGE = cfg.get('MAX_SLIPPAGE', 2)
RISK_PCT = cfg.get('RISK', {}).get('risk_per_trade', 1)
WEBHOOK_URL = cfg.get('DISCORD', {}).get('webhook_url', '')

# Setup trade log CSV
LOG_FILE = os.path.join(os.path.dirname(__file__), 'trades_log.csv')
PIP_SIZE = 0.0001  # adjust per instrument if needed

def init_trade_log():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp','symbol','side','units','entry','stop','tp','status','exec_price','slippage_pips'])

# Setup client
client = IbkrClient('config.yaml')
logger = logging.getLogger(__name__)

def execute_trades(signals, live_override=None):
    """
    Execute or simulate trades based on config.LIVE.
    Applies anti-drawdown and slippage constraints.
    """
    init_trade_log()
    # Determine live mode (override from UI if provided)
    local_live = live_override if live_override is not None else LIVE
    # Check drawdown
    if local_live:
        acct = client.get_account_summary()
        bal = float(acct.get('balance', 0))
        nav = float(acct.get('NAV', bal))
        drawdown = (bal - nav) / bal * 100 if bal else 0
        if drawdown > MAX_DRAWDOWN:
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
        # Build order payload
        order = {
            'order': {
                'instrument': sym,
                'units': str(units if side=='BUY' else -units),
                'type': 'MARKET',
                'timeInForce': 'FOK',
                'positionFill': 'DEFAULT',
                'priceBound': None,
                'stopLossOnFill': {'price': str(stop)},
                'takeProfitOnFill': {'price': str(tp)}
            }
        }
        if local_live:
            try:
                resp = client.place_order(order)
                logger.info(f"{datetime.datetime.now()} | ORDER EXECUTED | {sym} | {side} | units={units} | entry={entry} | stop={stop} | tp={tp} | resp={resp}")
                # extract executed price for slippage
                exec_price = float(resp.get('orderFillTransaction',{}).get('price', entry))
                slippage = abs(exec_price - entry) / PIP_SIZE
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
        # Append to trade log
        # Arrondi dynamique des niveaux selon la paire
        if any(x in sym for x in ['USD', 'EUR', 'GBP', 'AUD', 'NZD', 'CAD', 'CHF']):
            ndigits = 4 if not sym.endswith('JPY') and 'JPY' not in sym else 2
        else:
            ndigits = 2
        entry_r = round(entry, ndigits)
        stop_r = round(stop, ndigits)
        tp_r = round(tp, ndigits)

        with open(LOG_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([datetime.datetime.now(), sym, side, units, entry_r, stop_r, tp_r, status, exec_price, f"{slippage:.1f}"])
        # Send Discord notification if webhook is set
        if WEBHOOK_URL:
            mode_tag = '[LIVE]' if local_live else '[SIMU]'
            emoji = '📈' if side=='BUY' else '📉'
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            msg = f"{mode_tag} {emoji} {sym} | Entry: {entry_r} | SL: {stop_r} | TP: {tp_r} | Time: {ts}"
            try:
                requests.post(WEBHOOK_URL, json={'content': msg})
            except Exception as e:
                logger.error(f"Discord notification failed: {e}")
