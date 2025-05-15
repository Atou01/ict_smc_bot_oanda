install:
	python3 -m venv venv-py311
	source venv-py311/bin/activate && python3 -m pip install --upgrade pip setuptools wheel
	source venv-py311/bin/activate && python3 -m pip install -r requirements.txt

lint:
	source venv-py311/bin/activate && flake8 .

check:
	python3 -m compileall .

run:
	source venv-py311/bin/activate && python3 main.py
