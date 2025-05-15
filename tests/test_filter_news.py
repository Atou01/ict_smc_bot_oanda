import pytest
import requests
from filter_news import filter_high_impact

class FakeResponse:
    def __init__(self, text):
        self.text = text
    def raise_for_status(self):
        pass

@ pytest.fixture(autouse=True)
def fake_response(monkeypatch):
    html = """
    <html><body><table>
    <tr data-eventid="1">
      <td class="time">12:30</td>
      <td class="currency">USD</td>
      <td class="impact"><img alt="High Impact"/></td>
      <td class="event">Job Growth</td>
    </tr>
    <tr data-eventid="2">
      <td class="time">13:30</td>
      <td class="currency">EUR</td>
      <td class="impact"><img alt="Medium Impact"/></td>
      <td class="event">GDP Data</td>
    </tr>
    </table></body></html>
    """
    monkeypatch.setattr(requests, 'get', lambda url: FakeResponse(html))
    yield

def test_filter_high_impact_only_high():
    events = filter_high_impact()
    assert isinstance(events, list)
    assert len(events) == 1
    ev = events[0]
    assert ev['time'] == '12:30'
    assert ev['currency'] == 'USD'
    assert ev['event'] == 'Job Growth'
    assert ev['impact'] == 'high'
