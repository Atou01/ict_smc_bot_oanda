import yaml
import logging
from bias import MarketBias
from ibkr_client import IbkrClient
from strategy import MultiSMCStrategy
from execution import execute_trades
from apscheduler.schedulers.blocking import BlockingScheduler
from filter_news import filter_high_impact
from nlp_news import LLMAnalyzer

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

cfg = yaml.safe_load(open('config.yaml'))
client = IbkrClient('config.yaml')
tf_exec = cfg['TIMEFRAMES']['exec']
mb = MarketBias(config_path='config.yaml')

def run_strategy(biases):
    signals = []
    for sym in biases:
        df = client.get_ohlc(sym, tf_exec, count=20)
        strat = MultiSMCStrategy(df)
        sigs = strat.scan()
        for s in sigs:
            s['symbol'] = sym
            signals.append(s)
    return signals

def job_bias():
    bias = mb.get_current_bias()
    logger.info(f"Bias: {bias}")
    return bias

def job_strategy():
    bias = mb.get_current_bias()
    signals = run_strategy(bias)
    logger.info(f"Signals: {signals}")
    execute_trades(signals)

def job_news():
    events = filter_high_impact()
    analysis = LLMAnalyzer().analyze(events)
    logger.info(f"News analysis: {analysis}")

def create_scheduler():
    """Create and return the APScheduler scheduler with jobs registered."""
    scheduler = BlockingScheduler()
    scheduler.add_job(job_bias, 'interval', minutes=60, id='bias')
    scheduler.add_job(job_strategy, 'interval', minutes=5, id='strategy')
    scheduler.add_job(job_news, 'interval', minutes=15, id='news')
    return scheduler

def main():
    scheduler = create_scheduler()
    job_ids = [job.id for job in scheduler.get_jobs()]
    logger.info(f"Scheduler started with jobs: {job_ids}")
    scheduler.start()

if __name__ == '__main__':
    main()