import sys
import json
import os
import subprocess

task = json.load(open("task.json", "r"))

open("run.pid", "w").write(str(os.getpid()))

stdout = []
stderr = []

status = "ok"

for s in task["steps"]:
    p = subprocess.run(s, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    stderr.append(str(p.stderr, "utf-8"))
    stdout.append(str(p.stdout, "utf-8"))
    if p.returncode != 0:
        status = "failed"
        break

open(str(task["task_id"]) + ".json", "w").write(json.dumps({
    "stdout": stdout,
    "stderr": stderr,
    "status": status
}))
