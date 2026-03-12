PYTHON := python3
VENV := venv
PIP := $(VENV)/bin/pip
PYTHON_BIN := $(VENV)/bin/python3

.PHONY: venv deps update-deps run alert ci-check

venv:
	$(PYTHON) -m venv $(VENV)

deps:
	$(PIP) install -r requirements.txt

update-deps:
	./update_requirements.sh

run:
	./run_briefing.sh

alert:
	./run_options_alert.sh

ci-check:
	$(PYTHON_BIN) -m compileall yoloinvest check_requirements.py
	$(PYTHON_BIN) -c "import yoloinvest.config, yoloinvest.common.models, yoloinvest.common.fetchers, yoloinvest.common.sender, yoloinvest.market_briefing.app, yoloinvest.market_briefing.analyzers, yoloinvest.market_briefing.generators, yoloinvest.options_alert.alert; print('Core modules imported successfully')"
