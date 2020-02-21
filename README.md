Nightly
=======

## Introduction

Nightly is a system for scheduling, monitoring and collecting outputs from configuration-defined
command-line tasks. It is developed to support my daily research work since I can't find an existing
solution that is lightweight (depends on nothing more than python, mysql and ssh) and
customizable (written in less than a few hundreds lines of Python in total). 
I hope it might be useful to you as well.

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

## Runbook

Initialize or update database:

```
python src/main.py --upgrade-db
```

Truncate and backup log table:

```
python src/main.py --truncate-all-log
```

Run the master daemon for scheduling jobs (on a server within tmux):

```
python src/main.py
```

Run web panel daemon:

```
make panel # debug mode
export BASIC_AUTH_USERNAME=...; export BASIC_AUTH_PASSWORD=...; make panel-prod
```

Currently, panel server and master daemon must be on the same node.

## Demo

Homepage:

![](home.png)

Output page:

![](output.png)