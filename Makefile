all:
	@echo "run, panel"

run:
	PYLOG=INFO runpy src/main.py | tee main.log

panel:
	FLASK_APP=src/panel.py flask run

panel-prod:
	FLASK_APP=src/panel.py flask run --host=0.0.0.0
