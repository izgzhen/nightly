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

jobs_config = yaml.safe_load(open("config/jobs.yaml", "r"))
resources_config = yaml.safe_load(open("config/resources.yaml", "r"))

db = pymysql.connect(**resources_config["logdb"])

# FIXME: use argparse
if len(sys.argv) > 1:
    first_arg = sys.argv[1]
    if first_arg == "--init":
        for f in sorted(glob.glob("schema/*.sql")):
            cur = db.cursor()
            query = open(f, "r").read()
            print(query)
            cur.execute(query)
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

def total_log_count():
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM log")
    return cur.fetchone()[0]

def create_new_job_row(job, compute):
    job_started = datetime.datetime.now()
    return insert_row_get_id({
        "job_name": job["name"],
        "job_steps": json.dumps(job["steps"]),
        "job_started": job_started,
        "job_status": "running",
        "compute": json.dumps(compute)
    }, "log")

def run_cmd(cmd):
    print("+ " + cmd)
    return subprocess.getoutput(cmd)

def scp(compute, filepath):
    """
    SSH copy file to compute's working dir
    """
    assert compute["type"] == "ubuntu-1804-x86_64"
    return run_cmd("scp " + filepath + " " + compute["host"] + ":" + compute["working_dir"])

def ssh(compute, command):
    assert compute["type"] == "ubuntu-1804-x86_64"
    cmd = "cd " + compute["working_dir"] + "; " + command
    return run_cmd("ssh " + compute["host"] + " '" + cmd + "'")

def update_pid(job_id, pid):
    cur = db.cursor()
    cur.execute("UPDATE log SET pid = %s WHERE log_id = %s", (pid, job_id))
    cur.close()

def launch_job(job, compute):
    # prepare and send task.json
    job_id = create_new_job_row(job, compute)
    task_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
    task_file.write(json.dumps({
        "task_id": job_id,
        "steps": job["steps"]
    }))
    task_file.close()
    scp(compute, task_file.name)
    scp(compute, "src/runner.py")
    ssh(compute, "nohup python3 src/runner.py & echo $! > run.pid")
    pid = int(ssh(compute, "cat run.pid").strip())
    update_pid(job_id, pid)

    # launch job and store the running PID
    logger.info("Launched job (job_id: %s, PID: %s): %s" % (job_id, pid, job["name"]))

def get_last_run(job):
    cur = db.cursor()
    cur.execute("SELECT MAX(job_started) FROM log WHERE job_name = %s", job["name"])
    return cur.fetchone()[0]

def schedule_to_interval(sched):
    if sched == "nightly":
        return datetime.timedelta(days=1)
    raise Exception("Unknown schedule: " + sched)

def prepare_insert_query(row_dict, table):
    row_items = list(row_dict.items())
    fields = ", ".join([ k for k, v in row_items ])
    placeholders = ", ".join([ "%s" for k, v in row_items ])
    values = tuple(v for k, v in row_items)
    return "INSERT INTO %s (%s) VALUES (%s)" % (table, fields, placeholders), values

def insert_row(row_dict, table):
    cur = db.cursor()
    query, values = prepare_insert_query(row_dict, table)
    logger.info(query)
    cur.execute(query, values)
    cur.close()

def insert_row_get_id(row_dict, table):
    cur = db.cursor()
    query, values = prepare_insert_query(row_dict, table)
    logger.info(query)
    cur.execute(query, values)
    cur.execute("SELECT LAST_INSERT_ID()")
    ret = cur.fetchone()[0]
    cur.close()
    return ret

def process_job(job):
    last_run = get_last_run(job)
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

    launch_job(job, compute)

while True:
    logger.info("Total log: %s" % total_log_count())
    for job in jobs_config:
        process_job(job)
        db.commit()
    time.sleep(1)