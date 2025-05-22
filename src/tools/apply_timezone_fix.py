#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour appliquer la correction de fuseau horaire au collecteur macro.
Ce script modifie les parties spécifiques du macro_collector.py pour
assurer que toutes les dates/heures sont en fuseau horaire local.
"""

import os
import re
import sys
from pathlib import Path


def backup_file(file_path):
    """Crée une sauvegarde du fichier"""
    backup_path = f"{file_path}.bak"
    with open(file_path, "r", encoding="utf-8") as src:
        with open(backup_path, "w", encoding="utf-8") as dst:
            dst.write(src.read())
    print(f"Sauvegarde créée: {backup_path}")
    return backup_path


def apply_timezone_fix(file_path):
    """Applique les corrections de fuseau horaire"""
    # Vérifier si le fichier existe
    if not os.path.exists(file_path):
        print(f"Erreur: Fichier {file_path} non trouvé.")
        return False

    # Créer une sauvegarde
    backup_file(file_path)

    # Lire le contenu du fichier
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Ajout de l'import pytz et définition du fuseau horaire local (si nécessaire)
    if "import pytz" not in content:
        content = content.replace(
            "from typing import Optional",
            "from typing import Optional\nimport pytz\n\n# Définition du fuseau horaire local à utiliser pour toutes les conversions\nLOCAL_TZ = pytz.timezone('Europe/Paris')",
        )

    # 2. Ajout de la fonction helper de conversion de fuseau horaire
    if "_to_local_timezone" not in content:
        helper_func = """
    def _to_local_timezone(self, dt):
        \"\"\"
        Convertit un datetime UTC en heure locale (Europe/Paris)
        
        Args:
            dt (datetime): Objet datetime, avec ou sans timezone
            
        Returns:
            datetime: Datetime converti en timezone locale
        \"\"\"
        # Si le datetime n'a pas de timezone, on considère qu'il est en UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)
        # Conversion en heure locale
        return dt.astimezone(LOCAL_TZ)
    """
        # Ajouter la fonction après le _apply_filters
        content = re.sub(
            r"(def _apply_filters.*?\n\s+return True\n)",
            r"\1\n" + helper_func,
            content,
            flags=re.DOTALL,
        )

    # 3. Modification de _parse_event_datetime pour inclure la conversion de fuseau horaire
    parse_datetime_pattern = r"def _parse_event_datetime\(self, date_str, time_str\):.*?return None\n\s+except Exception as e:.*?return None"
    replacement = """def _parse_event_datetime(self, date_str, time_str):
        \"\"\"
        Convertit la date et l'heure du format ForexFactory en timestamp ISO avec timezone locale
        
        Note: Les dates dans le flux ForexFactory sont en UTC/GMT par défaut.
        Cette fonction les convertit en heure locale (Europe/Paris).
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
                        
                    # Créer l'objet datetime en UTC
                    utc_time = datetime(int(year), int(month), int(day), hour, int(minute), tzinfo=pytz.UTC)
                    
                    # Convertir en heure locale (Europe/Paris)
                    local_time = self._to_local_timezone(utc_time)
                    
                    # Débogage pour vérifier la conversion (uniquement en mode debug)
                    if self.debug_mode:
                        logger.debug(f"Conversion: UTC {utc_time.strftime('%Y-%m-%d %H:%M:%S')} -> "
                                    f"Local {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                    
                    return local_time.isoformat()
            except Exception as e:
                logger.warning(f"Erreur lors du parsing de la date: {date_str} {time_str} - {e}")
                
            return None
        except Exception as e:
            logger.warning(f"Impossible de parser la date/heure: {e}")
            return None"""

    content = re.sub(parse_datetime_pattern, replacement, content, flags=re.DOTALL)

    # 4. Modification de check_imminent_events pour utiliser l'heure locale
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
                        # Assurons-nous que l'heure de l'événement a une timezone
                        if event_time.tzinfo is None:
                            # Si pas de timezone, supposer qu'elle est en UTC et convertir en local
                            event_time = pytz.UTC.localize(event_time).astimezone(LOCAL_TZ)
                    else:
                        # Sinon, essayer de parser la date et l'heure
                        event_time_str = self._parse_event_datetime(event.get('date', ''), event.get('time', ''))
                        if not event_time_str:
                            continue
                        event_time = datetime.fromisoformat(event_time_str)
                        # Le parsing _parse_event_datetime retourne déjà en heure locale
                    
                    # Vérifier si l'événement est imminent - now et threshold sont en heure locale
                    # event_time est aussi en heure locale grâce à la conversion ci-dessus
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

    # 5. Écrire le contenu modifié dans le fichier
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

    print(f"Application des corrections de fuseau horaire à {macro_collector_path}")

    if apply_timezone_fix(str(macro_collector_path)):
        print("\nCorrections appliquées avec succès!")
        print("Maintenant, les événements macroéconomiques seront correctement")
        print("convertis et comparés en heure locale (Europe/Paris).")
        print("\nPour vérifier que tout fonctionne correctement, vous pouvez exécuter:")
        print(f"python {script_dir}/timezone_test.py")
        return 0
    else:
        print("\nÉchec de l'application des corrections.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
