import subprocess

from msbase.utils import getenv

def run_cmd(cmd):
    print("+ " + cmd)
    return subprocess.getoutput(cmd)

def render_job_html(job):
    TEMPLATES_DIR = getenv("TEMPLATES_DIR")
    from jinja2 import Template
    with open(TEMPLATES_DIR + '/job.jinja2', "r") as f:
        template = Template(f.read())
    return template.render(log=job)