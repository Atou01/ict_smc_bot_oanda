#!/usr/bin/env bash
set -e

python3 -m venv venv-py311
source venv-py311/bin/activate

python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install -r requirements.txt

python3 -m compileall .

echo "✅  Environnement prêt. Activez-le avec : source venv-py311/bin/activate"
