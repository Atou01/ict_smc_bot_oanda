#!/usr/bin/env python3
"""
Script de vérification de l'environnement d'exécution du bot.
Valide la présence des variables d'environnement requises et des dépendances Python.
Adapté pour fonctionner en CI (GitHub Actions) et en local.
"""

import os
import sys
import subprocess
import pkg_resources

# Détecte si nous sommes en environnement CI
is_ci = os.getenv("CI", "false").lower() == "true"
print(f"Environnement détecté: {'CI' if is_ci else 'local'}")

# Liste des variables requises selon l'environnement
required_vars = {
    "CI": [],  # En CI, aucune variable d'environnement spécifique n'est requise
    "local": [
        "OPENAI_API_KEY",
        "VANTAGE_LOGIN",
        "VANTAGE_PWD",
        "VANTAGE_SERVER",
        "DISCORD_TOKEN",
        "DISCORD_CHANNEL_ID"
    ]
}

# Vérifie les variables d'environnement
to_check = required_vars["CI"] if is_ci else required_vars["local"]
missing = [v for v in to_check if not os.getenv(v)]

if missing:
    print(f"❌ Variables d'environnement manquantes: {missing}")
    if not is_ci:  # En local, on échoue si des variables sont manquantes
        sys.exit(1)
    else:
        print("⚠️ En environnement CI, on continue malgré les variables manquantes")
else:
    print("✅ Toutes les variables d'environnement requises sont définies")

# Vérifie la présence du fichier requirements.txt
if not os.path.isfile("requirements.txt"):
    print("❌ Fichier requirements.txt introuvable")
    sys.exit(1)
else:
    print("✅ Fichier requirements.txt trouvé")

# Vérifie les dépendances Python
try:
    with open("requirements.txt", "r") as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
    # Traite les conditions de plateforme
    filtered_requirements = []
    for req in requirements:
        if ";" in req:
            # Format: package; condition
            package, condition = [part.strip() for part in req.split(";", 1)]
            # Si la condition contient sys_platform == "win32", on ne la vérifie que sur Windows
            if "sys_platform == \"win32\"" in condition and sys.platform != "win32":
                continue
            filtered_requirements.append(package)
        else:
            filtered_requirements.append(req)
    
    # Vérifie les dépendances installées
    installed = {pkg.key for pkg in pkg_resources.working_set}
    missing_pkgs = []
    
    for req in filtered_requirements:
        # Enlève les versions et autres spécificateurs
        pkg_name = req.split("==")[0].split(">=")[0].split(">")[0].split("<")[0].split("<=")[0].strip()
        if pkg_name.lower() not in installed:
            missing_pkgs.append(pkg_name)
    
    if missing_pkgs:
        print(f"❌ Dépendances Python manquantes: {missing_pkgs}")
        sys.exit(1)
    else:
        print("✅ Toutes les dépendances Python sont installées")

except Exception as e:
    print(f"❌ Erreur lors de la vérification des dépendances: {e}")
    sys.exit(1)

print("✅ Environnement validé avec succès")
