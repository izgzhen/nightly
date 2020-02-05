import sys
import json
import os
import subprocess
import datetime

nightly_cwd = os.getcwd()

task = json.load(open("task.json", "r"))

open("run.pid", "w").write(str(os.getpid()))

stdout = []
stderr = []

status = "ok"

if task["cwd"]:
    os.chdir(task["cwd"])

for s in task["steps"]:
    p = subprocess.run(s, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    stderr.append(str(p.stderr, "utf-8"))
    stdout.append(str(p.stdout, "utf-8"))
    if p.returncode != 0:
        status = "failed"
        break

os.chdir(nightly_cwd)

open(str(task["task_id"]) + ".json", "w").write(json.dumps({
    "stdout": stdout,
    "stderr": stderr,
    "finished_timestamp": datetime.datetime.timestamp(datetime.datetime.now()),
    "status": status
}))
