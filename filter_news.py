import requests
from bs4 import BeautifulSoup

def filter_high_impact():
    """
    Fetch and filter high-impact economic news events from ForexFactory.
    Returns a list of events: {time, currency, event, impact}.
    """
    url = 'https://www.forexfactory.com/calendar?week=this_week'
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'lxml')
    events = []
    # rows with data-eventid attribute
    for row in soup.find_all('tr', attrs={'data-eventid': True}):
        imp = row.find('td', class_='impact')
        if not imp or not imp.img:
            continue
        alt = imp.img.get('alt', '').strip().lower()
        if 'high impact' not in alt:
            continue
        time = row.find('td', class_='time').get_text(strip=True)
        currency = row.find('td', class_='currency').get_text(strip=True)
        event = row.find('td', class_='event').get_text(strip=True)
        events.append({
            'time': time,
            'currency': currency,
            'event': event,
            'impact': 'high'
        })
    return events
