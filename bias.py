import yaml
from data import OandaClient
import pandas as pd

class MarketBias:
    """
    Detects market bias on higher timeframes (D, H4, H1) using BOS/CHoCH.
    """
    LOOKBACK = 5

    def __init__(self, config_path="config.yaml", symbols=None):
        cfg = yaml.safe_load(open(config_path))
        self.client = OandaClient(config_path)
        self.symbols = symbols or cfg.get('SYMBOLS', [])
        # Use OANDA granularity strings for HTF
        self.timeframes = ['D', 'H4', 'H1']

    def detect_bos_up(self, df: pd.DataFrame) -> bool:
        if len(df) < self.LOOKBACK + 1:
            return False
        prev_high = df['high'].iloc[-(self.LOOKBACK+1):-1].max()
        curr_close = df['close'].iloc[-1]
        return curr_close > prev_high

    def detect_bos_down(self, df: pd.DataFrame) -> bool:
        if len(df) < self.LOOKBACK + 1:
            return False
        prev_low = df['low'].iloc[-(self.LOOKBACK+1):-1].min()
        curr_close = df['close'].iloc[-1]
        return curr_close < prev_low

    def get_current_bias(self) -> dict:
        """
        Returns a dict per symbol: {
          symbol: { 'htf': {tf: bias}, 'bias': overall_bias }
        }
        overall_bias = 'UP' if all HTF are UP, 'DOWN' if all DOWN, else 'NEUTRAL'.
        """
        biases = {}
        for sym in self.symbols:
            htf_bias = {}
            for tf in self.timeframes:
                df = self.client.get_ohlc(sym, tf, count=self.LOOKBACK+1)
                up = self.detect_bos_up(df)
                down = self.detect_bos_down(df)
                if up:
                    htf_bias[tf] = 'UP'
                elif down:
                    htf_bias[tf] = 'DOWN'
                else:
                    htf_bias[tf] = 'NEUTRAL'
            # determine overall
            vals = list(htf_bias.values())
            if all(v == 'UP' for v in vals):
                overall = 'UP'
            elif all(v == 'DOWN' for v in vals):
                overall = 'DOWN'
            else:
                overall = 'NEUTRAL'
            biases[sym] = {'htf': htf_bias, 'bias': overall}
        return biases
