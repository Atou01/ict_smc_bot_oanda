#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour corriger le problème inversé de fuseau horaire.
Les heures de ForexFactory sont déjà en heure locale, pas en UTC.
"""

import os
import re
import sys
from pathlib import Path


def backup_file(file_path):
    """Crée une sauvegarde du fichier"""
    backup_path = f"{file_path}.bak2"
    with open(file_path, "r", encoding="utf-8") as src:
        with open(backup_path, "w", encoding="utf-8") as dst:
            dst.write(src.read())
    print(f"Sauvegarde créée: {backup_path}")
    return backup_path


def fix_timezone_issue(file_path):
    """Corrige le problème de conversion de fuseau horaire inversé"""
    # Vérifier si le fichier existe
    if not os.path.exists(file_path):
        print(f"Erreur: Fichier {file_path} non trouvé.")
        return False

    # Créer une sauvegarde
    backup_file(file_path)

    # Lire le contenu du fichier
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Modifier la fonction _parse_event_datetime pour ne pas convertir
    parse_datetime_pattern = r"def _parse_event_datetime\(self, date_str, time_str\):.*?return None\n\s+except Exception as e:.*?return None"
    replacement = """def _parse_event_datetime(self, date_str, time_str):
        \"\"\"
        Convertit la date et l'heure du format ForexFactory en timestamp ISO
        
        Note: Les dates dans le flux ForexFactory sont déjà en heure locale (Europe/Paris).
        \"\"\"
        try:
            # Format typique: date="05-11-2025" time="6:00pm"
            if not date_str or not time_str:
                return None
                
            # Nettoyer les données (pour enlever CDATA si présent)
            date_str = date_str.strip()
            time_str = time_str.strip()
            if date_str.startswith('<![CDATA['):
                date_str = date_str[9:-3].strip()
            if time_str.startswith('<![CDATA['):
                time_str = time_str[9:-3].strip()
                
            # Convertir au format datetime
            try:
                # Essayer le format "MM-DD-YYYY"
                date_parts = date_str.split('-')
                if len(date_parts) == 3:
                    month, day, year = date_parts
                    
                    # Convertir l'heure (format 12h avec AM/PM)
                    is_pm = 'pm' in time_str.lower()
                    time_str = time_str.lower().replace('am', '').replace('pm', '').strip()
                    if ':' in time_str:
                        hour, minute = time_str.split(':')[:2]
                    else:
                        hour, minute = time_str, '00'
                        
                    hour = int(hour)
                    if is_pm and hour < 12:
                        hour += 12
                    elif not is_pm and hour == 12:
                        hour = 0
                        
                    # Créer l'objet datetime déjà en heure locale
                    local_time = datetime(int(year), int(month), int(day), hour, int(minute), tzinfo=LOCAL_TZ)
                    
                    # Débogage pour vérifier l'heure (uniquement en mode debug)
                    if self.debug_mode:
                        logger.debug(f"Heure ForexFactory (locale): {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                    
                    return local_time.isoformat()
            except Exception as e:
                logger.warning(f"Erreur lors du parsing de la date: {date_str} {time_str} - {e}")
                
            return None
        except Exception as e:
            logger.warning(f"Impossible de parser la date/heure: {e}")
            return None"""

    content = re.sub(parse_datetime_pattern, replacement, content, flags=re.DOTALL)

    # Modifier check_imminent_events pour utiliser l'heure locale directement
    check_events_pattern = r"def check_imminent_events\(self, minutes_threshold=30\):.*?return imminent_events"
    check_events_replacement = """def check_imminent_events(self, minutes_threshold=30):
        \"\"\"
        Vérifie les événements importants qui vont se produire dans les prochaines minutes.
        
        Args:
            minutes_threshold (int): Nombre de minutes à l'avance pour considérer un événement comme imminent
            
        Returns:
            list: Liste des événements imminents avec impact High ou Medium
        \"\"\"
        # Utiliser maintenant avec le fuseau horaire local
        now = datetime.now(LOCAL_TZ)
        threshold = now + timedelta(minutes=minutes_threshold)
        imminent_events = []
        
        for event in self.latest_events:
            if event.get('impact') in ['High', 'Medium']:
                try:
                    # Si le timestamp est déjà au format ISO
                    if event.get('timestamp') and isinstance(event['timestamp'], str):
                        event_time = datetime.fromisoformat(event['timestamp'])
                    else:
                        # Sinon, essayer de parser la date et l'heure
                        event_time_str = self._parse_event_datetime(event.get('date', ''), event.get('time', ''))
                        if not event_time_str:
                            continue
                        event_time = datetime.fromisoformat(event_time_str)
                    
                    # Vérifier si l'événement est imminent
                    if now < event_time <= threshold:
                        imminent_events.append(event)
                        # Logguer avec les heures locales pour le débogage
                        logger.info(
                            f"[Événement imminent] {event.get('impact', 'Unknown')} impact: "
                            f"{event.get('country', '')} {event.get('title', '')} "
                            f"à {event_time.strftime('%Y-%m-%d %H:%M:%S')} (heure locale)"
                        )
                except (ValueError, TypeError) as e:
                    logger.warning(f"Erreur lors de l'analyse de la date/heure: {e}")
                    continue
        
        return imminent_events"""

    content = re.sub(
        check_events_pattern, check_events_replacement, content, flags=re.DOTALL
    )

    # Écrire le contenu modifié dans le fichier
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Corrections de fuseau horaire appliquées avec succès à {file_path}")
    return True


def main():
    """Fonction principale"""
    # Détecter le chemin du fichier macro_collector.py
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent.parent

    macro_collector_path = project_root / "src" / "bot" / "macro_collector.py"

    if not macro_collector_path.exists():
        print(f"Erreur: Fichier {macro_collector_path} non trouvé.")
        return 1

    print(
        f"Application des corrections inversées de fuseau horaire à {macro_collector_path}"
    )

    if fix_timezone_issue(str(macro_collector_path)):
        print("\nCorrections appliquées avec succès!")
        print("Maintenant, les événements macroéconomiques seront correctement")
        print("interprétés comme étant déjà en heure locale dans le flux ForexFactory.")
        print("\nLes heures d'annonces économiques devraient maintenant correspondre")
        print("exactement à ce que vous voyez sur le site ForexFactory.")
        return 0
    else:
        print("\nÉchec de l'application des corrections.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
