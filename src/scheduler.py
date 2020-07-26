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

from typing import Dict, Any

from msbase.logging import logger
from msbase.utils import getenv, load_yaml

from model import DB
from common import run_cmd, get_jobs_config
from launcher import Launcher
from resource import Resource
from notif import send_text

try:
    launcher = Launcher()
    db = DB()

    def process_running_jobs():
        running_jobs = db.fetch_all_running_jobs()
        for job in running_jobs:
            resource = Resource(job["compute"], job["storage"])
            persisted = job["job_persisted"]
            log_id = str(job["log_id"])
            if job["pid"] is not None:
                if resource.is_pid_running(resource.compute, job["pid"]):
                    logger.info("Still running #%s" % log_id)
                else:
                    logger.info("Non-existent job PID: %s" % job["pid"])
                    # collect output
                    output_json = log_id + "-output.json"
                    runner_dir = resource.compute["nightly_tmp"]
                    resource.scp_from(runner_dir + "/" + output_json, ".", node=resource.compute)
                    if not os.path.exists(output_json):
                        logger.warn(f"Job #{log_id} failed: not existing {output_json}")
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
                init_seconds = (datetime.datetime.now() - job["job_started"]).total_seconds()
                if init_seconds > 60:
                    logger.warn(f"Job #{log_id} failed: init too long, {init_seconds} seconds")
                    db.update_job_status(log_id, "failed", datetime.datetime.now())
                else:
                    logger.info("Still initializing #%s (%s seconds passed)" % (log_id, init_seconds))

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
        for job_name, job in get_jobs_config().items():
            if job["schedule"] != "once":
                launcher.process_job_to_launch(job)
        process_running_jobs()
        time.sleep(30)
except Exception as e:
    error_msg_html = """
    <h2>Schedule is crashed by exception</h2>
    <pre>%s</pre>
    """ % e
    send_text(error_msg_html)
    raise e