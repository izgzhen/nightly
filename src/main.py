import yaml
import time
import pymysql
import glob
import sys
import json

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

def run_job(job):
    logger.info("Run job: " + job["name"])
    return {
        "job_steps": json.dumps(job["steps"]),
        "job_status": "ok"
    }

def get_last_run(job):
    cur = db.cursor()
    cur.execute("SELECT MAX(job_finished) FROM log WHERE job_name = %s", job["name"])
    return cur.fetchone()[0]

def schedule_to_interval(sched):
    if sched == "nightly":
        return datetime.timedelta(days=1)
    raise Exception("Unknown schedule: " + sched)

def insert_row(row_dict, table):
    cur = db.cursor()
    row_items = list(row_dict.items())
    fields = ", ".join([ k for k, v in row_items ])
    placeholders = ", ".join([ "%s" for k, v in row_items ])
    values = tuple(v for k, v in row_items)
    query = "INSERT INTO %s (%s) VALUES (%s)" % (table, fields, placeholders)
    logger.info(query)
    cur.execute(query, values)
    cur.close()

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

    job_started = datetime.datetime.now()
    result = run_job(job)
    job_finished = datetime.datetime.now()
    result["job_name"] = job["name"]
    result["job_persisted"] = json.dumps(job["persisted"])
    result["job_started"] = job_started
    result["job_finished"] = job_finished
    result["storage"] = json.dumps(storage)
    result["compute"] = json.dumps(compute)

    insert_row(result, "log")

while True:
    logger.info("Total log: %s" % total_log_count())
    for job in jobs_config:
        process_job(job)
        db.commit()
    time.sleep(1)