all:
	@echo "run, panel"

run:
	PYLOG=INFO python src/main.py | tee main.log

panel:
	DEBUG_MODE=1 FLASK_APP=src/panel.py flask run

panel-prod:
	FLASK_APP=src/panel.py flask run --host=0.0.0.0
