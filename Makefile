mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
NIGHTLY_PROJ_ROOT := $(shell dirname $(mkfile_path))

export CONFIG_JOBS = $(NIGHTLY_PROJ_ROOT)/config/jobs.yaml
export CONFIG_RESOURCES = $(NIGHTLY_PROJ_ROOT)/config/resources.yaml
export SCHEMA_DIR = $(NIGHTLY_PROJ_ROOT)/schema
export TEMPLATES_DIR = $(NIGHTLY_PROJ_ROOT)/src/templates

all:
	@echo "run, panel"

PYFILES := $(shell find src -name "*.py")

check:
	ck $(PYFILES)

run: check
	PYLOG=INFO runpy src/scheduler.py | tee main.log

panel: check
	DEBUG_MODE=1 FLASK_APP=src/panel.py flask run

panel-prod: check
	FLASK_APP=src/panel.py flask run --host=0.0.0.0

upgrade-db: check
	python src/main.py --upgrade-db

upgrade-db: check
	python src/main.py --upgrade-db

truncate-all-log: check
	python src/main.py --truncate-all-log