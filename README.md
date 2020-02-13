Nightly
=======

Data objects:

- Job
- Resource

Components:

- Job DB: Database containing job log (status) entries
- Scheduler: master node
- Runner: launch job on runner node through SSH
- Storage: persisting job output and selected files

## Dependencies

```
virtualenv -p python3 .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Config

Inside `config` folder, ignored by git

- `resources.yaml` ... TBD
    - `storage` and `compute`:
        - `type`: type composed of OS name etc.
        - `host`: host name
    - `storage` only:
        - `where`: where the job data is persisted
    - `compute` only:
        - `nightly_tmp`: temporary directory for holding nightly related file, e.g. `task.json` (FIXME: use task-specific names)
    - ... TBD
- `jobs.yaml` -- each job has a set of attributes:
    - `name`: unique id to identify the same type of job
    - `schedule` -- one of:
        + `nightly`: launch new job now if `now > last_run(name).started + 1 day`
        + `daemon`: launch new job now if all previous same type run has finished or failed
    - `steps`: a list of commands
    - `cwd` (optional, default to compute node's `nightly_tmp`): where commands in `steps` are run
    - `compute_type`: compute node type
    - `host`: compute node host (optional, default to any `host` in `resources` that has the required `compute_type`)
    - ... TBD

We use different set of `config` folders for different environment (production or development)

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