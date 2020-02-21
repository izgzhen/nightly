Nightly
=======

Data objects:

- Job
- Resource

Components:

- Log DB: database containing job log (status) entries
- Scheduler: master node
- Runner: launch job on runner node through SSH
- Storage: persisting job output and selected files
- Panel: web panel daemon

## Dependencies

```
virtualenv -p python3 .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Config

There should be two files inside `config` folder, which is ignored by git.
See `example_config` for examples and comments.

Users can use different `config` folders in different environment (production or development).

## Initialize or update database

```
python src/main.py --upgrade-db
```

## Runbook

Run the master daemon for scheduling jobs (on a server within tmux):

```
python src/main.py
```

Web panel:

```
make panel # debug mode
export BASIC_AUTH_USERNAME=...; export BASIC_AUTH_PASSWORD=...; make panel-prod
```

Currently, panel server and master daemon must be the same node.

## Demo

Homepage:

![](home.png)

Output page:

![](output.png)