from bot.macro_collector import MacroCollector

# Exemple d'entrée brute depuis ForexFactory
date_str = "05-22-2025"
time_str = "7:15am"

collector = MacroCollector(xml_url=None)  # xml_url inutile pour ce test
result = collector._parse_event_datetime(date_str, time_str)
print(f"Entrée ForexFactory : {date_str} {time_str}")
print(f"Résultat conversion (ISO) : {result}")

# -*- coding: utf-8 -*-

"""
Script de test pour vérifier la conversion des fuseaux horaires.
À utiliser pour valider que la conversion UTC -> Heure locale fonctionne correctement.
"""

import pytz
from datetime import datetime

# Fuseau horaire local (France/Europe Centrale)
LOCAL_TZ = pytz.timezone("Europe/Paris")


def to_local_timezone(dt):
    """
    Convertit un datetime UTC en heure locale

    Args:
        dt (datetime): Objet datetime, avec ou sans timezone

    Returns:
        datetime: Datetime converti en timezone locale
    """
    # Si le datetime n'a pas de timezone, on considère qu'il est en UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.UTC)
    # Conversion en heure locale
    return dt.astimezone(LOCAL_TZ)


def main():
    """Test de conversion d'heures de calendrier économique typiques"""

    # Exemple 1: Non-Farm Payrolls (NFP) - généralement 8:30 AM ET / 12:30 UTC en hiver
    nfp_utc = datetime(2025, 6, 6, 12, 30, 0, tzinfo=pytz.UTC)
    nfp_local = to_local_timezone(nfp_utc)
    print(f"NFP (UTC): {nfp_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"NFP (Local): {nfp_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # Exemple 2: CPI - généralement 8:30 AM ET / 12:30 UTC en hiver
    cpi_utc = datetime(2025, 6, 11, 12, 30, 0, tzinfo=pytz.UTC)
    cpi_local = to_local_timezone(cpi_utc)
    print(f"CPI (UTC): {cpi_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"CPI (Local): {cpi_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # Exemple 3: ECB Rate Decision - généralement 13:45 CET / 12:45 UTC en hiver
    ecb_utc = datetime(2025, 6, 5, 12, 45, 0, tzinfo=pytz.UTC)
    ecb_local = to_local_timezone(ecb_utc)
    print(f"ECB (UTC): {ecb_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"ECB (Local): {ecb_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # Test avec l'heure actuelle
    now_utc = datetime.now(pytz.UTC)
    now_local = to_local_timezone(now_utc)
    print(f"Now (UTC): {now_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Now (Local): {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # Test avec simulation de format ForexFactory
    # Format: date="06-05-2025" time="8:30am" (mois-jour-année)
    ff_date = "06-05-2025"
    ff_time = "8:30am"

    # Parsing du format ForexFactory
    month, day, year = ff_date.split("-")
    is_pm = "pm" in ff_time.lower()
    time_str = ff_time.lower().replace("am", "").replace("pm", "").strip()
    hour, minute = time_str.split(":")
    hour = int(hour)
    if is_pm and hour < 12:
        hour += 12
    elif not is_pm and hour == 12:
        hour = 0

    # Créer l'heure en UTC (les heures ForexFactory sont généralement en UTC)
    ff_utc = datetime(
        int(year), int(month), int(day), hour, int(minute), tzinfo=pytz.UTC
    )
    ff_local = to_local_timezone(ff_utc)

    print(f"\nForexFactory original: {ff_date} {ff_time}")
    print(f"Parsed (UTC): {ff_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Converted (Local): {ff_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Différence d'heures: {(ff_local.hour - ff_utc.hour):+d} heures")


if __name__ == "__main__":
    main()
