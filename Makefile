PYTHON := python3
VENV := venv
PIP := $(VENV)/bin/pip
PYTHON_BIN := $(VENV)/bin/python

.PHONY: venv deps update-deps run ci-check

venv:
	$(PYTHON) -m venv $(VENV)

deps:
	$(PIP) install -r requirements.txt

update-deps:
	./update_requirements.sh

run:
	./run_briefing.sh

ci-check:
	$(PYTHON_BIN) -m compileall .
	$(PYTHON_BIN) -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path('.').resolve())); import config, models, fetchers, analyzers, generators, sender; print('Core modules imported successfully')"
