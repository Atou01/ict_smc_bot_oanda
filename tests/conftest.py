import sys
import os
# Add project root to sys.path for module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
import pandas as pd
import data

@pytest.fixture(autouse=True)
def patch_ohlc(monkeypatch):
    """Patch OandaClient.get_ohlc to return fake OHLC DataFrame for tests"""
    def fake_get_ohlc(self, symbol, granularity, count):
        times = pd.date_range('2025-01-01', periods=count, freq='H')
        return pd.DataFrame({
            'time': times,
            'open': list(range(count)),
            'high': list(range(count)),
            'low': list(range(count)),
            'close': list(range(count)),
            'volume': [100] * count
        })
    monkeypatch.setattr(data.OandaClient, 'get_ohlc', fake_get_ohlc)
