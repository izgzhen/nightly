import yaml
import time
import pymysql
import glob
import sys
import os
import json
import tempfile
import subprocess
import datetime

from msbase.logging import logger

from model import DB
from common import run_cmd
from resource import ssh, scp, persist

jobs_config = yaml.safe_load(open("config/jobs.yaml", "r"))
resources_config = yaml.safe_load(open("config/resources.yaml", "r"))

db = DB()

# FIXME: use argparse
if len(sys.argv) > 1:
    first_arg = sys.argv[1]
    if first_arg == "--upgrade-db":
        db.upgrade()
        sys.exit(0)

def get_storage(type_: str):
    for s in resources_config["storage"]:
        if s["type"] == type_:
            return s

def get_compute(type_: str):
    # FIXME: better scheduling strategy
    for s in resources_config["compute"]:
        if s["type"] == type_:
            return s

def create_new_job_row(job, compute, storage):
    job_started = datetime.datetime.now()
    return db.insert_row_get_id({
        "job_name": job["name"],
        "job_steps": json.dumps(job["steps"]),
        "job_persisted": json.dumps(job["persisted"]),
        "job_started": job_started,
        "job_status": "running",
        "compute": json.dumps(compute),
        "storage": json.dumps(storage)
    }, "log")

# FIXME: launch job in a new temporary folder
def launch_job(job, compute, storage):
    # prepare and send task.json
    job_id = create_new_job_row(job, compute, storage)
    task_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
    task_file.write(json.dumps({
        "task_id": job_id,
        "steps": job["steps"]
    }))
    task_file.close()
    scp(compute, task_file.name, "task.json")
    scp(compute, "src/runner.py")
    logger.info(ssh(compute, "nohup python3 runner.py > /dev/null 2>&1 &"))
    pid = int(ssh(compute, "sleep 1; cat run.pid").strip())
    db.update_pid(job_id, pid)

    # launch job and store the running PID
    logger.info("Launched job (job_id: %s, PID: %s): %s" % (job_id, pid, job["name"]))

def schedule_to_interval(sched):
    if sched == "nightly":
        return datetime.timedelta(days=1)
    raise Exception("Unknown schedule: " + sched)

def process_job_to_launch(job):
    last_run = db.get_last_run(job)
    if last_run is not None:
        now = datetime.datetime.now()
        interval = schedule_to_interval(job["schedule"])
        if last_run + interval > now:
            return None

    storage = get_storage(job["storage_type"])
    if storage is None:
        return None

    compute = get_compute(job["compute_type"])
    if compute is None:
        return None

    launch_job(job, compute, storage)

def process_running_jobs():
    running_jobs = db.fetch_running_jobs()
    for job in running_jobs:
        compute = json.loads(job["compute"])
        storage = json.loads(job["storage"])
        persisted = json.loads(job["job_persisted"])
        log_id = str(job["log_id"])
        ret = ssh(compute, "ps -p %s" % job["pid"])
        logger.info(ret)
        if str(job["pid"]) not in ret:
            # collect output
            output_json = log_id + ".json"
            scp(compute, ".", renamed=output_json, to_remote=False)
            output = json.loads(open(output_json, "r").read())
            db.update_job_status(log_id, output["status"], datetime.date.fromtimestamp(output["finished_timestamp"]))
            os.system("rm " + output_json)
            # collect persisted
            for persisted_item in persisted:
                persist(compute, storage, log_id, persisted_item)
            persist(compute, storage, log_id, output_json, renamed="output.json")
            logger.info("Finished %s" % log_id)
        else:
            logger.info("Still running %s" % log_id)

while True:
    logger.info("Total log: %s" % db.total_log_count())
    for job in jobs_config:
        process_job_to_launch(job)
        db.commit()
    process_running_jobs()
    time.sleep(1)
