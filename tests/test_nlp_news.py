import pytest
from nlp_news import LLMAnalyzer

class DummySentiment:
    def __init__(self, polarity):
        self.polarity = polarity

class FakeBlob:
    def __init__(self, text):
        # positive if contains 'good', negative if 'bad', neutral otherwise
        if 'good' in text.lower():
            self.sentiment = DummySentiment(0.5)
        elif 'bad' in text.lower():
            self.sentiment = DummySentiment(-0.5)
        else:
            self.sentiment = DummySentiment(0.0)

@pytest.fixture(autouse=True)
def patch_textblob(monkeypatch):
    import nlp_news
    monkeypatch.setattr(nlp_news, 'TextBlob', FakeBlob)
    yield


def test_analyze_empty():
    analyzer = LLMAnalyzer()
    summary = analyzer.analyze([])
    assert summary['events_count'] == 0
    assert summary['details'] == []


def test_analyze_sentiment():
    events = [
        {'event': 'Good news announced'},
        {'event': 'Bad results published'},
        {'event': 'Neutral statement'}
    ]
    analyzer = LLMAnalyzer()
    summary = analyzer.analyze(events)
    assert summary['events_count'] == 3
    assert len(summary['details']) == 3
    labels = [d['label'] for d in summary['details']]
    assert labels == ['positive', 'negative', 'neutral']
