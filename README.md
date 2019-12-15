Nightly
=======

- Job definition
- Resource definition
- Log DB
- Scheduler
- Runner
- Storage

## Dependencies

```
virtualenv -p python3 .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Config

Inside `config` folder, ignored by git

- `jobs.yaml`
- `resources.yaml`

## Run

```
python src/main.py
```
