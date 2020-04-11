import sys
import json
import os
import subprocess
import datetime

nightly_cwd = os.getcwd()
task_id = sys.argv[1]
task = json.load(open(task_id + "-input.json", "r"))

open(task_id + "-pid.txt", "w").write(str(os.getpid()))
status = "ok"

if task["cwd"]:
    os.chdir(task["cwd"])

if task["env"]:
    env = task["env"]
else:
    env = {}

msg = ""

for si, s in enumerate(task["steps"]):
    stdout_output_path = "%s/%s-%s-stdout.txt" % (nightly_cwd, task_id, si)
    stderr_output_path = "%s/%s-%s-stderr.txt" % (nightly_cwd, task_id, si)
    with open(stdout_output_path, "w") as f_stdout:
        with open(stderr_output_path, "w") as f_stderr:
            p = subprocess.run(s, stderr=f_stderr, stdout=f_stdout, env={**os.environ, **env})
            if p.returncode != 0:
                status = "failed"
                msg = "step %s: returncode is %s" % (s, p.returncode)
                break

os.chdir(nightly_cwd)

open(task_id + "-output.json", "w").write(json.dumps({
    "finished_timestamp": datetime.datetime.timestamp(datetime.datetime.now()),
    "status": status,
    "msg": msg
}))
