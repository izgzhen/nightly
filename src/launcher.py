"""
Process launcher for run an ad-hoc job
"""
import yaml
import json
import datetime
import tempfile
import time
import sys
import os

from msbase.utils import getenv, datetime_str
from msbase.logging import logger

from common import get_jobs_config
from model import DB
from resource import Resource
from notif import send_text

def schedule_to_interval(sched):
    if sched == "nightly":
        return datetime.timedelta(days=1)
    raise Exception("Unknown schedule: " + sched)

class Launcher(object):
    def __init__(self):
        super().__init__()
        self.resources_config = yaml.safe_load(open(getenv("CONFIG_RESOURCES"), "r"))
        self.db = DB()

    def get_storage(self, type_: str):
        for s in self.resources_config["storage"]:
            if s["type"] == type_:
                return s

    def get_master_as_compute(self):
        return self.get_compute_by_host(self.resources_config["master"]["host"])

    def get_master_as_storage(self):
        return self.get_storage_by_host(self.resources_config["master"]["host"])

    def get_compute(self, type_: str):
        # FIXME: better scheduling strategy
        for s in self.resources_config["compute"]:
            if s["type"] == type_:
                return s

    def get_compute_by_host(self, host: str):
        # FIXME: better scheduling strategy
        for s in self.resources_config["compute"]:
            if s["host"] == host:
                return s

    def get_storage_by_host(self, host: str):
        # FIXME: better scheduling strategy
        for s in self.resources_config["storage"]:
            if s["host"] == host:
                return s

    def create_new_job_row(self, job, compute, storage):
        job_started = datetime.datetime.now()
        return self.db.insert_row_get_id({
            "job_name": job["name"],
            "cwd": job["cwd"],
            "env": json.dumps(job["env"]),
            "job_steps": json.dumps(job["steps"]),
            "job_persisted": json.dumps(job["persisted"]),
            "job_started": job_started,
            "job_status": "running",
            "compute": json.dumps(compute),
            "storage": json.dumps(storage)
        }, "log")

    # FIXME: launch job in a new temporary folder
    def launch_job(self, job, compute, storage):
        # prepare and send task.json
        job_id = self.create_new_job_row(job, compute, storage)
        task_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
        task_file.write(json.dumps({
            "cwd": job["cwd"],
            "env": job["env"],
            "steps": job["steps"]
        }))
        task_file.close()
        resource = Resource(compute, storage)
        runner_dir = resource.compute["nightly_tmp"]
        resource.scp_to(task_file.name, runner_dir + "/%s-input.json" % job_id, resource.compute)
        resource.scp_to("src/runner.py", runner_dir + "/runner.py", resource.compute)
        resource.ssh_exec_on_node("cd " + runner_dir + "; nohup python3 runner.py %s > /dev/null 2>&1 &" % job_id, resource.compute)
        try:
            pid = int(resource.ssh_exec_on_node("sleep 3; cat " + runner_dir + "/" + str(job_id) + "-pid.txt", resource.compute).strip())
        except Exception:
            import pdb, traceback
            extype, value, tb = sys.exc_info()
            traceback.print_exc()
            send_text("Exception -- in PDB now")
            pdb.post_mortem(tb)
        self.db.update_pid(job_id, pid)

        # launch job and store the running PID
        logger.info("Launched job (job_id: %s, PID: %s): %s" % (job_id, pid, job["name"]))
        time.sleep(1)

    def process_job_to_launch(self, job):
        """
        Process job for further scheduling needs
        """
        job_name = job["name"]
        assert "enabled" in job, job
        if not job["enabled"]:
            logger.info(f"Job {job_name} is not enabled, thus skipped")
            return
        if "cwd" not in job:
            job["cwd"] = None
        if "env" not in job:
            job["env"] = {}
        if job["schedule"] in ["nightly"]:
            # Check if we need to wait until an internal after the last run of the same job finished
            last_run = self.db.get_last_run_started(job)
            if last_run is not None:
                now = datetime.datetime.now()
                interval = schedule_to_interval(job["schedule"])
                if last_run + interval > now:
                    return None
        elif job["schedule"] == "daemon":
            jobs = self.db.fetch_running_jobs_of(job)
            if len(jobs) > 0:
                assert len(jobs) == 1
                return None
        elif job["schedule"] == "once":
            pass
        else:
            raise Exception("Unknown schedule: " + job["schedule"])

        storage = self.get_storage(job["storage_type"])
        if storage is None:
            return None

        if "host" in job:
            compute = self.get_compute_by_host(job["host"])
        else:
            compute = self.get_compute(job["compute_type"])

        if compute is None:
            logger.warn("Can't find compute resource for " + str(job))
            return None

        self.launch_job(job, compute, storage)
        self.db.commit()

if __name__ == "__main__":
    launcher = Launcher()
    if sys.argv[1] == "--job":
        job_name = sys.argv[2]
        job = get_jobs_config()[job_name]
        print(f"Launch job {job_name}: {job}")
        launcher.process_job_to_launch(job)
        exit(0)
    cwd = getenv("NIGHTLY_LAUNCH_CWD")
    step = sys.argv[1:]
    name = "adhoc-" + datetime_str()
    print(f"Launch job {name}:")
    print(f"- cwd: {cwd}")
    print(f"- step: {step}")
    compute = launcher.get_master_as_compute() # FIXME: support other launch as well
    storage = launcher.get_master_as_storage()
    job = {
        "name": name,
        "steps": [ step ],
        "schedule": "once",
        "storage_type": storage["type"],
        "persisted": [],
        "enabled": True,
        "cwd": cwd,
        "env": dict(os.environ)
    }
    launcher.launch_job(job, compute, storage)