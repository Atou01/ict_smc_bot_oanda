import pytest
import pandas as pd
from bias import MarketBias

@pytest.fixture(autouse=True)
def fake_ohlc(monkeypatch):
    # Return a DataFrame with monotonic increasing data for up bias
    data = {
        'time': pd.date_range('2025-01-01', periods=6, freq='H'),
        'open': [1,2,3,4,5,6],
        'high': [1,2,3,4,5,6],
        'low':  [0.5,1.5,2.5,3.5,4.5,5.5],
        'close':[1,2,3,4,5,6],
        'volume':[100]*6
    }
    df = pd.DataFrame(data)
    # patch get_ohlc on OandaClient in data module
    import data
    monkeypatch.setattr(data.OandaClient, 'get_ohlc', lambda self, sym, tf, count: df)
    yield

def test_get_current_bias_all_up():
    mb = MarketBias(config_path='config.yaml', symbols=['EUR_USD'])
    biases = mb.get_current_bias()
    assert 'EUR_USD' in biases
    assert biases['EUR_USD']['bias'] == 'UP'
    # Each timeframe htfs should be UP
    for v in biases['EUR_USD']['htf'].values():
        assert v == 'UP'

def test_get_current_bias_mixed(monkeypatch):
    # simulate D and H4 up, H1 neutral
    def side_effect(self, sym, tf, count):
        import pandas as pd
        data = {'time': pd.date_range('2025-01-01', periods=6, freq='H'),
                'open': [1,2,3,4,5,3],
                'high': [1,2,3,4,5,3],
                'low':  [0.5,1.5,2.5,3.5,4.5,2.5],
                'close':[1,2,3,4,5,3],
                'volume':[100]*6}
        return pd.DataFrame(data)
    # patch varying returns per tf
    import data
    monkeypatch.setattr(data.OandaClient, 'get_ohlc', side_effect)
    mb = MarketBias(config_path='config.yaml', symbols=['EUR_USD'])
    biases = mb.get_current_bias()
    assert biases['EUR_USD']['bias'] == 'NEUTRAL'
