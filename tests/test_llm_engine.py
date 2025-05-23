import json, time, builtins, types
import pytest
import sys
import os

# Ajout du chemin pour l'importation depuis src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.bot import llm_engine as le

# Simuler le module d'erreur OpenAI
class OpenAIErrorMock:
    class RateLimitError(Exception): pass
    class APIError(Exception): pass
    class Timeout(Exception): pass

# Patch le module d'erreur OpenAI
if not hasattr(le.openai, 'error'):
    le.openai.error = OpenAIErrorMock

def mock_resp(content):
    class Choice: 
        message = {"content": content}
    class Resp: 
        choices = [Choice()]
    return Resp()

def test_valid_json(monkeypatch, sample_payload, tmp_csv):
    good = json.dumps({
        "symbol":"EURUSD","direction":"LONG","strategy":"ICT_OB",
        "entry":1.1,"sl":1.0,"tp":1.2,"confidence":0.8,
        "reasoning":"test"
    })
    monkeypatch.setattr("openai.ChatCompletion.create",
                        lambda **_: mock_resp(good))
    res = le.decide_trade(sample_payload)
    assert res and res["symbol"]=="EURUSD"
    assert tmp_csv.read_text().count("EURUSD") == 1

def test_bad_json(monkeypatch, sample_payload, tmp_csv):
    monkeypatch.setattr("openai.ChatCompletion.create",
                        lambda **_: mock_resp('{"bad":"data"}'))
    assert le.decide_trade(sample_payload) is None
    assert not tmp_csv.exists()

def test_rate_limit_retry(monkeypatch, sample_payload):
    calls = {"n":0}
    def fake_call(**_):
        calls["n"] += 1
        if calls["n"] < 3:
            raise le.openai.error.RateLimitError("boom")
        return mock_resp('{"symbol":"EURUSD","direction":"SHORT","strategy":"ICT_OB","entry":1,"sl":0.9,"tp":1.1,"confidence":0.7,"reasoning":"ok"}')
    monkeypatch.setattr("openai.ChatCompletion.create", fake_call)
    start = time.time()
    res = le.decide_trade(sample_payload)
    elapsed = time.time() - start
    assert res and calls["n"] == 3 and elapsed >= 5  # Ajusté pour être un peu plus flexible

def test_timeout(monkeypatch, sample_payload):
    class MockSeq:
        def __init__(self):
            self.count = 0
        def __call__(self, **kwargs):
            self.count += 1
            if self.count == 1:
                raise le.openai.error.Timeout("timeout")
            return mock_resp('{}')
    
    monkeypatch.setattr("openai.ChatCompletion.create", MockSeq())
    assert le.decide_trade(sample_payload) is None  # JSON vide → invalide
