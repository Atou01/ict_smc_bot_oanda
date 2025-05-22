"""
config_validator.py
Module de validation de la configuration.
Vérifie que toutes les clés nécessaires sont présentes dans le fichier de configuration.
"""


def print_config_status(cfg):
    """
    Valide la présence des clés essentielles dans la configuration.

    Args:
        cfg (dict): Dictionnaire de configuration chargé depuis config.yaml

    Returns:
        bool: True si toutes les clés essentielles sont présentes, False sinon
    """
    # Clés obligatoires pour le fonctionnement du bot
    required_keys = {
        "OPENAI": ["api_key"],
        "XML_FEED_URL": None,
        "RISK": ["capital", "risk_pct"],
    }

    missing = []
    for key, subkeys in required_keys.items():
        if key not in cfg:
            missing.append(key)
        elif subkeys:  # Si on a des sous-clés à vérifier
            for subkey in subkeys:
                if key in cfg and (
                    not isinstance(cfg[key], dict) or subkey not in cfg[key]
                ):
                    missing.append(f"{key}.{subkey}")

    if missing:
        print(
            f"[CONFIG] ⚠️ Clés manquantes dans la configuration : {', '.join(missing)}"
        )
        return False

    # Vérifications spécifiques
    warnings = []

    # Vérifier que l'URL XML est valide
    if not cfg.get("XML_FEED_URL", "").startswith(("http://", "https://", "file://")):
        warnings.append("XML_FEED_URL n'est pas une URL valide")

    # Afficher les warnings éventuels
    if warnings:
        print(f"[CONFIG] ⚠️ Avertissements : {', '.join(warnings)}")

    print("[CONFIG] ✅ Tous les paramètres obligatoires sont présents.")
    return True
