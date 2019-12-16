all:
	@echo "run, panel"

run:
	python3 src/main.py | tee main.log

panel:
	FLASK_APP=src/panel.py flask run
