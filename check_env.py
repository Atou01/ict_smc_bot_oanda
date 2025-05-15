#!/usr/bin/env python3
import sys
import os
import importlib

REQUIRED_PYTHON = (3, 9)
REQUIRED_FILES = ["config.yaml"]
REQUIREMENTS_FILE = "requirements.txt"

def check_python_version():
    if sys.version_info < REQUIRED_PYTHON:
        print(f"❌ Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+ requis, version détectée : {sys.version_info.major}.{sys.version_info.minor}")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} OK")
    return True

def check_required_files():
    ok = True
    for f in REQUIRED_FILES:
        if not os.path.isfile(f):
            print(f"❌ Fichier requis absent : {f}")
            ok = False
        else:
            print(f"✅ {f} présent")
    return ok

def check_dependencies():
    ok = True
    try:
        with open(REQUIREMENTS_FILE) as f:
            for line in f:
                pkg = line.strip().split("#")[0]
                if not pkg or pkg.startswith("-"): continue
                pkg_name = pkg.split("==")[0].split(">=")[0].split("<=")[0].strip()
                try:
                    importlib.import_module(pkg_name.replace("-", "_"))
                except ImportError:
                    print(f"❌ Dépendance manquante : {pkg_name}")
                    ok = False
                else:
                    print(f"✅ {pkg_name} installé")
    except Exception as e:
        print(f"⚠️ Erreur lors de la lecture de {REQUIREMENTS_FILE} : {e}")
        return False
    return ok

if __name__ == "__main__":
    ok = check_python_version()
    ok &= check_required_files()
    ok &= check_dependencies()
    sys.exit(0 if ok else 1)
