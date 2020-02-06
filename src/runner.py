import sys
import json
import os
import subprocess
import datetime

nightly_cwd = os.getcwd()

task_id = sys.argv[1]
task = json.load(open(task_id + "-input.json", "r"))

open("run.pid", "w").write(str(os.getpid()))
status = "ok"

if task["cwd"]:
    os.chdir(task["cwd"])

for si, s in enumerate(task["steps"]):
    with open("%s-%s-stdout.txt" % (task_id, si), "w") as f_stdout:
        with open("%s-%s-stderr.txt" % (task_id, si), "w") as f_stderr:
            p = subprocess.run(s, stderr=f_stderr, stdout=f_stdout)
            if p.returncode != 0:
                status = "failed"
                print(status)
                break

os.chdir(nightly_cwd)

open(task_id + "-output.json", "w").write(json.dumps({
    "finished_timestamp": datetime.datetime.timestamp(datetime.datetime.now()),
    "status": status
}))
