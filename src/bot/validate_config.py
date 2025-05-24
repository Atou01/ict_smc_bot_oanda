"""
config_validator.py
Utilitaire de validation des configurations requises au démarrage du bot.
Vérifie que toutes les clés essentielles sont présentes.
"""

import sys
import yaml

"""
config_validator.py
Utilitaire CLI pour valider la configuration du bot (config.yaml)
Usage : python validate_config.py
"""


def validate_config(config):
    """
    Valide que toutes les clés requises sont présentes dans la configuration.
    Retourne (valide, messages) où valide est un booléen et messages la liste des problèmes.
    """
    messages = []
    valid = True

    # Définir les clés requises par section
    required_keys = {
        "RISK": ["capital", "risk_pct", "max_drawdown_pct"],
        "BROKER": ["mode"],
        "OPENAI": ["api_key"],
    }

    # Vérifier chaque section et ses clés
    for section, keys in required_keys.items():
        if section not in config:
            messages.append(f"Section {section} manquante dans config.yaml")
            valid = False
            continue

        for key in keys:
            if key not in config[section]:
                messages.append(
                    f"Clé {key} manquante dans la section {section} de config.yaml"
                )
                valid = False

    # Vérifier les valeurs spécifiques
    if "RISK" in config and "capital" in config["RISK"]:
        try:
            capital = float(config["RISK"]["capital"])
            if capital <= 0:
                messages.append("Le capital doit être supérieur à 0")
                valid = False
        except (ValueError, TypeError):
            messages.append("La valeur du capital doit être un nombre")
            valid = False

    if "RISK" in config and "max_drawdown_pct" in config["RISK"]:
        try:
            drawdown = float(config["RISK"]["max_drawdown_pct"])
            if drawdown <= 0 or drawdown > 100:
                messages.append("Le drawdown maximum doit être entre 0 et 100%")
                valid = False
        except (ValueError, TypeError):
            messages.append("La valeur du drawdown maximum doit être un nombre")
            valid = False

    return valid, messages


if __name__ == "__main__":
    try:
        with open("config.yaml") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Erreur lors du chargement de config.yaml : {e}")
        sys.exit(1)

    valid, messages = validate_config(config)
    if valid:
        print("✅ Configuration valide : toutes les clés critiques sont présentes.")
        # Afficher un résumé des paramètres essentiels
        print("\nRésumé des paramètres essentiels :")
        if "RISK" in config:
            print(f"  - Capital : {config['RISK'].get('capital', 'N/A')}")
            print(f"  - Risk % : {config['RISK'].get('risk_pct', 'N/A')}")
            print(f"  - Drawdown max : {config['RISK'].get('max_drawdown_pct', 'N/A')}")
        if "BROKER" in config:
            print(f"  - Mode broker : {config['BROKER'].get('mode', 'N/A')}")
        sys.exit(0)
    else:
        print("❌ Erreurs de configuration détectées :")
        for msg in messages:
            print(f"  - {msg}")
        print("\nCorrigez le fichier config.yaml avant de lancer le bot.")
        sys.exit(1)


def print_config_status(config):
    """
    Affiche le statut de validation de la configuration avec un formatage clair.
    """
    valid, messages = validate_config(config)

    if valid:
        print("✅ Configuration valide: Toutes les clés requises sont présentes.")

        # Afficher un résumé des paramètres essentiels
        if "RISK" in config:
            risk = config["RISK"]
            print(f"💰 Capital: {risk.get('capital', 'N/A')}€")
            print(f"📊 Risk par trade: {risk.get('risk_pct', 'N/A')}%")
            print(f"⚠️ Drawdown max: {risk.get('max_drawdown_pct', 'N/A')}%")
    else:
        print("❌ Configuration invalide:")
        for msg in messages:
            print(f"  - {msg}")
        print(
            "\nVeuillez corriger ces problèmes dans le fichier config.yaml avant de continuer."
        )

    return valid
