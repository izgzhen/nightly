"""
Job scheduling master daemon
"""
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
from resource import Resource

def get_jobs_config():
    return yaml.safe_load(open("config/jobs.yaml", "r"))
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

def get_compute_by_host(host: str):
    # FIXME: better scheduling strategy
    for s in resources_config["compute"]:
        if s["host"] == host:
            return s

def create_new_job_row(job, compute, storage):
    job_started = datetime.datetime.now()
    return db.insert_row_get_id({
        "job_name": job["name"],
        "cwd": job["cwd"],
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
        "cwd": job["cwd"],
        "steps": job["steps"]
    }))
    task_file.close()
    resource = Resource(compute, storage)
    runner_dir = resource.compute["nightly_tmp"]
    resource.scp_to(task_file.name, runner_dir + "/%s-input.json" % job_id, resource.compute)
    resource.scp_to("src/runner.py", runner_dir + "/runner.py", resource.compute)
    resource.ssh_exec_on_node("cd " + runner_dir + "; nohup python3 runner.py %s > /dev/null 2>&1 &" % job_id, resource.compute)
    pid = int(resource.ssh_exec_on_node("sleep 1; cat " + runner_dir + "/run.pid", resource.compute).strip())
    db.update_pid(job_id, pid)

    # launch job and store the running PID
    logger.info("Launched job (job_id: %s, PID: %s): %s" % (job_id, pid, job["name"]))

def schedule_to_interval(sched):
    if sched == "nightly":
        return datetime.timedelta(days=1)
    raise Exception("Unknown schedule: " + sched)

def process_job_to_launch(job):
    if job["schedule"] in ["nightly"]:
        # Check if we need to wait until an internal after the last run of the same job finished
        last_run = db.get_last_run_started(job)
        if last_run is not None:
            now = datetime.datetime.now()
            interval = schedule_to_interval(job["schedule"])
            if last_run + interval > now:
                return None
    elif job["schedule"] == "daemon":
        jobs = db.fetch_running_jobs_of(job)
        if len(jobs) > 0:
            assert len(jobs) == 1
            return None
    else:
        raise Exception("Unknown schedule: " + job["schedule"])

    storage = get_storage(job["storage_type"])
    if storage is None:
        return None

    if "host" in job:
        compute = get_compute_by_host(job["host"])
    else:
        compute = get_compute(job["compute_type"])

    if compute is None:
        log.warning("missing host for " + str(job))
        return None

    launch_job(job, compute, storage)

def process_running_jobs():
    running_jobs = db.fetch_all_running_jobs()
    for job in running_jobs:
        resource = Resource(job["compute"], job["storage"])
        persisted = job["job_persisted"]
        log_id = str(job["log_id"])
        ret = resource.ssh_exec_on_node("ps -p %s" % job["pid"], resource.compute)
        if str(job["pid"]) not in ret:
            # collect output
            output_json = log_id + "-output.json"
            runner_dir = resource.compute["nightly_tmp"]
            resource.scp_from(runner_dir + "/" + output_json, ".", node=resource.compute)
            if not os.path.exists(output_json):
                db.update_job_status(log_id, "failed", datetime.datetime.now())
                continue
            output = json.loads(open(output_json, "r").read())
            db.update_job_status(log_id, output["status"], datetime.date.fromtimestamp(output["finished_timestamp"]))
            os.system("rm " + output_json)
            # collect persisted
            for persisted_item in persisted:
                resource.persist(log_id, runner_dir + "/" + persisted_item, os.path.basename(persisted_item))
            for si in range(len(job["job_steps"])):
                f = "%s-%s-stderr.txt" % (log_id, si)
                resource.persist(log_id, runner_dir + "/" + f, f)
                f = "%s-%s-stdout.txt" % (log_id, si)
                resource.persist(log_id, runner_dir + "/" + f, f)

            resource.persist(log_id, runner_dir + "/" + output_json, "output.json")
            logger.info("Finished #%s" % log_id)
        else:
            logger.info("Still running #%s" % log_id)

while True:
    logger.info("Scanning all jobs: %s" % db.total_log_count())
    for job in get_jobs_config():
        if "cwd" not in job:
            job["cwd"] = None
        if job["enabled"]:
            process_job_to_launch(job)
        db.commit()
    process_running_jobs()
    time.sleep(1)
