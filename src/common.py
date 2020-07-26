import subprocess
from typing import Dict, Any, List

from msbase.utils import getenv, load_yaml
from msbase.subprocess_ import try_call_std

def run_cmd(cmd):
    print("+ " + cmd)
    return subprocess.getoutput(cmd)

def run_cmd_stdout(cmd_args: List[str]):
    stdout, stderr, code = try_call_std(cmd_args, print_cmd=True, output=True, noexception=True)
    return stdout

def render_job_html(job):
    TEMPLATES_DIR = getenv("TEMPLATES_DIR")
    from jinja2 import Template
    with open(TEMPLATES_DIR + '/job.jinja2', "r") as f:
        template = Template(f.read())
    return template.render(log=job)

def get_jobs_config() -> Dict[str, Any]:
    jobs = load_yaml(getenv("CONFIG_JOBS"))
    jobs_dict = { job["name"] : job for job in jobs }
    assert len(jobs) == len(jobs_dict)
    return jobs_dict
