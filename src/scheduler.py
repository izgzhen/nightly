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
from msbase.utils import getenv

from model import DB
from common import run_cmd
from launcher import Launcher
from resource import Resource

def get_jobs_config():
    return yaml.safe_load(open(getenv("CONFIG_JOBS"), "r"))

launcher = Launcher()
db = DB()

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
            db.update_job_status(log_id, output["status"], datetime.datetime.fromtimestamp(output["finished_timestamp"]))
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

# FIXME: use argparse
if len(sys.argv) > 1:
    first_arg = sys.argv[1]
    if first_arg == "--upgrade-db":
        db.upgrade()
        sys.exit(0)
    elif first_arg == "--truncate-all-log":
        db.truncate_all_log()
        sys.exit(0)

while True:
    logger.info("Scanning all jobs: %s" % db.total_log_count())
    for job in get_jobs_config():
        if "cwd" not in job:
            job["cwd"] = None
        if "env" not in job:
            job["env"] = {}
        if job["enabled"]:
            launcher.process_job_to_launch(job)
        db.commit()
    process_running_jobs()
    time.sleep(1)
