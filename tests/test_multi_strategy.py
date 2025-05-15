import pandas as pd
import pytest
from strategy import MultiSMCStrategy

@pytest.fixture
def base_df():
    # Create a base DataFrame with 25 bars of simple range
    times = pd.date_range('2025-01-01', periods=25, freq='T')
    data = {
        'time': times,
        'open': list(range(25)),
        'high': [o + 1 for o in range(25)],
        'low': list(range(25)),
        'close': [o + 0.5 for o in range(25)],
        'volume': [100] * 25
    }
    return pd.DataFrame(data)

def test_detect_order_blocks(base_df):
    # make the penultimate bar large-bodied
    df = base_df.copy()
    df.at[23, 'open'] = 0
    df.at[23, 'high'] = 50
    df.at[23, 'low'] = 0
    df.at[23, 'close'] = 50
    strat = MultiSMCStrategy(df, lookback=20)
    obs = strat.detect_order_blocks()
    assert len(obs) == 1
    ob = obs[0]
    assert ob['pattern'] == 'order_block'
    assert ob['type'] == 'bull'
    assert ob['zone'] == (0, 50)

def test_detect_fvg():
    # pattern where a.high < c.low
    df = pd.DataFrame({
        'high': [1,2,3],
        'low': [0,1,2],
        'open': [0,1,2],
        'close': [0,1,2]
    })
    strat = MultiSMCStrategy(df)
    fvg = strat.detect_fvg()
    assert len(fvg) == 1
    assert fvg[0]['pattern'] == 'fvg'
    assert fvg[0]['zone'] == (1, 2)

def test_detect_liquidity_sweeps(base_df):
    df = base_df.copy()
    # set last high above previous max
    df.at[24, 'high'] = df['high'][:-1].max() + 10
    strat = MultiSMCStrategy(df, lookback=20)
    sweeps = strat.detect_liquidity_sweeps()
    assert any(s['pattern']=='liquidity_sweep' for s in sweeps)

def test_detect_rejection_bull():
    # create a candle with long lower wick
    df = pd.DataFrame({
        'high': [10],
        'low': [0],
        'open': [5],
        'close': [8]
    })
    strat = MultiSMCStrategy(df)
    rej = strat.detect_rejection()
    assert len(rej) == 1
    assert rej[0]['side'] == 'buy'
    assert rej[0]['level'] == 0

def test_detect_rejection_bear():
    # create a candle with long upper wick
    df = pd.DataFrame({
        'high': [10],
        'low': [0],
        'open': [8],
        'close': [5]
    })
    strat = MultiSMCStrategy(df)
    rej = strat.detect_rejection()
    assert len(rej) == 1
    assert rej[0]['side'] == 'sell'
    assert rej[0]['level'] == 10

def test_scan_combined(base_df):
    # integrate all patterns: inject a FVG and OB and LS and rejection
    df = base_df.copy()
    # OB
    df.loc[23, ['open','high','low','close']] = [0,50,0,50]
    # FVG via last three (use concat instead of deprecated append)
    extra = pd.DataFrame({
        'high': [1,2], 'low': [0,1], 'open': [1,2], 'close': [1,2], 'volume': [100,100]
    })
    df2 = pd.concat([df, extra], ignore_index=True)
    strat = MultiSMCStrategy(df2, lookback=20)
    signals = strat.scan()
    assert isinstance(signals, list)
    # at minimum one each
    patterns = [s['pattern'] for s in signals]
    assert 'order_block' in patterns
    assert 'fvg' in patterns or 'liquidity_sweep' in patterns or 'rejection' in patterns
