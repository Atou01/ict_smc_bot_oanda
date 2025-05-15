import pandas as pd

class SMCScreener:
    """
    Simple SMC screener detecting basic Break of Structure (BOS) for BUY and SELL.
    """
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.last_signals = []  # store last detected signals

    def __repr__(self):
        return f"<SMCScreener rows={len(self.df)}>"

    def detect_bos(self, lookback: int = 5) -> bool:
        """
        Detects a simple BOS: current close > max(high) of previous lookback bars.
        """
        if len(self.df) < lookback + 1:
            return False
        prev_high = self.df['high'].iloc[:-1].max()  # previous history
        curr_close = self.df['close'].iloc[-1]
        return bool(curr_close > prev_high)

    def scan(self) -> list:
        """
        Scans for BOS signals and returns a list of signals:
        [{'side': 'BUY', 'entry': float, 'stop': float, 'tp': float}]
        TP is set at 2x distance from stop.
        """
        signals = []
        lookback = 5
        curr_close = float(self.df['close'].iloc[-1])
        # BUY detection
        if self.detect_bos(lookback):
            stop = float(self.df['low'].iloc[:-1].min())  # previous history
            tp = curr_close + (curr_close - stop) * 2
            signals.append({'side': 'BUY', 'entry': curr_close, 'stop': stop, 'tp': tp})
        # SELL detection (mirror BOS)
        if len(self.df) >= 1:
            prev_low = self.df['low'].iloc[:-1].min()
            if curr_close < prev_low:
                stop = float(self.df['high'].iloc[:-1].max())
                tp = curr_close - (stop - curr_close) * 2
                signals.append({'side': 'SELL', 'entry': curr_close, 'stop': stop, 'tp': tp})
        self.last_signals = signals
        return signals


class MultiSMCStrategy:
    """
    Multi-strategy ICT/SMC: Order Block, FVG, Liquidity Sweep patterns on LTF.
    """
    def __init__(self, df: pd.DataFrame, lookback: int = 20):
        self.df = df
        self.lookback = lookback

    def detect_order_blocks(self):
        """Detect large-body bars as Order Blocks anywhere in the DataFrame."""
        if self.df.empty:
            return []
        ranges = self.df['high'] - self.df['low']
        bodies = abs(self.df['close'] - self.df['open'])
        threshold = ranges.mean() * 1.5
        obs = []
        for i in range(len(self.df)):
            if bodies.iloc[i] > threshold:
                zone = (self.df['low'].iloc[i], self.df['high'].iloc[i])
                obs.append({
                    'pattern': 'order_block',
                    'type': 'bull' if self.df['close'].iloc[i] > self.df['open'].iloc[i] else 'bear',
                    'zone': zone
                })
        return obs

    def detect_fvg(self):
        """Detect Fair Value Gaps on last 3 bars."""
        if len(self.df) < 3:
            return []
        a, b, c = self.df.iloc[-3], self.df.iloc[-2], self.df.iloc[-1]
        if a['high'] < c['low']:
            return [{'pattern': 'fvg', 'zone': (a['high'], c['low'])}]
        if a['low'] > c['high']:
            return [{'pattern': 'fvg', 'zone': (c['high'], a['low'])}]
        return []

    def detect_liquidity_sweeps(self, eq_lookback=10, eq_tolerance=1e-4, min_dist=1e-4):
        """
        Détection robuste des liquidity sweeps :
        - Recherche EQH/EQL dans les eq_lookback dernières bougies
        - Confirme le sweep par mèche + clôture opposée
        - Exclut si entry ≈ stop ou incohérence directionnelle
        """
        if len(self.df) < eq_lookback + 2:
            return []
        sweeps = []
        highs = self.df['high'].iloc[-(eq_lookback+2):-1]
        lows = self.df['low'].iloc[-(eq_lookback+2):-1]
        # EQH : sommets quasiment égaux
        eqh_level = None
        eqh = [h for h in highs if abs(h - highs.max()) < eq_tolerance]
        if len(eqh) >= 2:
            eqh_level = max(eqh)
        eql_level = None
        eql = [l for l in lows if abs(l - lows.min()) < eq_tolerance]
        if len(eql) >= 2:
            eql_level = min(eql)
        last = self.df.iloc[-1]
        # Sweep au-dessus d’un EQH confirmé
        if eqh_level is not None and last['high'] > eqh_level:
            # mèche + clôture sous EQH
            if last['close'] < eqh_level and (last['high'] - last['close']) > min_dist:
                sweeps.append({'pattern': 'liquidity_sweep', 'side': 'sell', 'level': eqh_level})
        # Sweep sous un EQL confirmé
        if eql_level is not None and last['low'] < eql_level:
            if last['close'] > eql_level and (last['close'] - last['low']) > min_dist:
                sweeps.append({'pattern': 'liquidity_sweep', 'side': 'buy', 'level': eql_level})
        return sweeps

    def detect_rejection(self):
        """Detect candle rejection wicks on last bar."""
        if len(self.df) < 1:
            return []
        last = self.df.iloc[-1]
        rng = last['high'] - last['low']
        # bullish rejection: long lower wick (>=20% of range)
        if last['close'] > last['open'] and (last['open'] - last['low']) >= rng * 0.2:
            return [{'pattern': 'rejection', 'side': 'buy', 'level': last['low']}]
        # bearish rejection: long upper wick (>=20% of range)
        if last['close'] < last['open'] and (last['high'] - last['open']) >= rng * 0.2:
            return [{'pattern': 'rejection', 'side': 'sell', 'level': last['high']}]
        return []

    def scan(self):
        """Aggregate all pattern signals into trade signals."""
        signals = []
        # Rejections
        for rej in self.detect_rejection():
            side = rej['side']
            level = rej['level']
            entry = level
            stop = float(self.df['low'].iloc[-1]) if side=='buy' else float(self.df['high'].iloc[-1])
            tp = entry + (entry-stop)*2 if side=='buy' else entry - (stop-entry)*2
            if entry == stop:
                continue
            if side == 'buy' and not (tp > entry > stop):
                continue
            if side == 'sell' and not (tp < entry < stop):
                continue
            signals.append({**rej, 'entry': entry, 'stop': stop, 'tp': tp})
        # Order Blocks
        for ob in self.detect_order_blocks():
            side = 'buy' if ob['type']=='bull' else 'sell'
            entry = ob['zone'][0] if side=='buy' else ob['zone'][1]
            stop = ob['zone'][1] if side=='buy' else ob['zone'][0]
            tp = entry + (entry-stop)*2 if side=='buy' else entry - (stop-entry)*2
            if entry == stop or (side == 'buy' and not (tp > entry > stop)) or (side == 'sell' and not (tp < entry < stop)):
                continue
            signals.append({**ob, 'side': side, 'entry': entry, 'stop': stop, 'tp': tp})
        # FVG
        for fvg in self.detect_fvg():
            low, high = fvg['zone']
            side = 'buy' if low < self.df['close'].iloc[-1] else 'sell'
            entry = low if side=='buy' else high
            stop = high if side=='buy' else low
            tp = entry + (entry-stop)*2 if side=='buy' else entry - (stop-entry)*2
            if entry == stop or (side == 'buy' and not (tp > entry > stop)) or (side == 'sell' and not (tp < entry < stop)):
                continue
            signals.append({**fvg, 'side': side, 'entry': entry, 'stop': stop, 'tp': tp})
        # Liquidity Sweeps
        for ls in self.detect_liquidity_sweeps():
            level = ls['level']
            side = ls['side']
            entry = level
            stop = self.df['close'].iloc[-1]
            tp = entry + (entry-stop)*2 if side=='buy' else entry - (stop-entry)*2
            if entry == stop or (side == 'buy' and not (tp > entry > stop)) or (side == 'sell' and not (tp < entry < stop)):
                continue
            signals.append({**ls, 'entry': entry, 'stop': stop, 'tp': tp})
        return signals
