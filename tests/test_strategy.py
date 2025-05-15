import pandas as pd
import pytest
from strategy import SMCScreener

@ pytest.mark.parametrize("lookback,close_values,expected", [
    (5, [1,2,3,4,5,6,8], True),   # 8 > max(high prev 5 bars =6)
    (5, [1,2,3,4,5,6,5], False),  # 5 <=6, no BOS
])
def test_detect_bos(lookback, close_values, expected):
    # Build DataFrame with increasing highs and current close
    length = len(close_values)
    data = {
        'time': pd.date_range('2025-01-01', periods=length, freq='T'),
        'open': close_values,
        'high': close_values,
        'low': [min(close_values) - 1] * length,
        'close': close_values,
        'volume': [100] * length
    }
    df = pd.DataFrame(data)
    screener = SMCScreener(df)
    assert screener.detect_bos(lookback=lookback) is expected


def test_scan_signal_structure():
    # Create a scenario with detectable BOS
    close_vals = [1,2,3,4,5,6,10]
    low_vals = [0.5,0.5,0.5,0.5,0.5,0.5,0.5]
    df = pd.DataFrame({
        'time': pd.date_range('2025-01-01', periods=len(close_vals), freq='T'),
        'open': close_vals,
        'high': close_vals,
        'low': low_vals,
        'close': close_vals,
        'volume': [100] * len(close_vals)
    })
    screener = SMCScreener(df)
    signals = screener.scan()
    assert isinstance(signals, list)
    assert len(signals) == 1
    sig = signals[0]
    assert sig['side'] == 'BUY'
    assert sig['entry'] == 10
    # stop is min(low of last 6 bars) = 0.5
    assert sig['stop'] == 0.5
    # tp = entry + 2*(entry - stop)
    assert sig['tp'] == pytest.approx(10 + 2 * (10 - 0.5))
    # last_signals updated
    assert screener.last_signals == signals

def test_scan_signal_structure_sell():
    # Create a scenario with detectable SELL BOS
    close_vals = [10,9,8,7,6,5,3]
    high_vals = close_vals.copy()
    low_vals = close_vals.copy()
    df = pd.DataFrame({
        'time': pd.date_range('2025-01-01', periods=len(close_vals), freq='T'),
        'open': close_vals,
        'high': high_vals,
        'low': low_vals,
        'close': close_vals,
        'volume': [100] * len(close_vals)
    })
    screener = SMCScreener(df)
    signals = screener.scan()
    assert isinstance(signals, list)
    assert len(signals) == 1
    sig = signals[0]
    assert sig['side'] == 'SELL'
    assert sig['entry'] == 3
    # stop is max(high of previous 6 bars)
    assert sig['stop'] == max(high_vals[:-1])
    expected_tp = sig['entry'] - (sig['stop'] - sig['entry']) * 2
    assert sig['tp'] == pytest.approx(expected_tp)
    # last_signals updated
    assert screener.last_signals == signals

def test_repr_and_last_signals():
    # test __repr__ and last_signals attribute
    close_vals = [1,2,3,4,5,6,7]
    df = pd.DataFrame({
        'time': pd.date_range('2025-01-01', periods=7, freq='T'),
        'open': close_vals,
        'high': close_vals,
        'low': [0.5] * 7,
        'close': close_vals,
        'volume': [100] * 7
    })
    screener = SMCScreener(df)
    assert repr(screener) == '<SMCScreener rows=7>'
    signals = screener.scan()
    assert hasattr(screener, 'last_signals')
    assert screener.last_signals == signals
