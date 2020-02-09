"""
Job Panel Web Server
"""
from flask import Flask, flash, request, redirect, url_for, render_template
from flask_basicauth import BasicAuth

import datetime
import json
import tempfile
import os

from model import DB
from resource import Resource

db = DB()

app = Flask(__name__)

if os.getenv("DEBUG_MODE") != "1":
    for e in ['BASIC_AUTH_USERNAME', 'BASIC_AUTH_PASSWORD']:
        v = os.getenv(e)
        assert v is not None
        app.config[e] = v
    app.config['BASIC_AUTH_FORCE'] = True # force auth all requests
    basic_auth = BasicAuth(app)

def color_of_status(status: str):
    if status == 'running':
        return "green"
    elif status == 'ok':
        return "white"
    elif status == 'failed':
        return "red"
    else:
        raise Exception(status)

@app.route('/')
def index():
    entries = db.fetch_all_jobs()
    for entry in entries:
        entry["job_status_color"] = color_of_status(entry["job_status"])
    return render_template('index.html',
                            now=datetime.datetime.now(),
                            logs=reversed(entries))

@app.route('/output/<log_id>')
def serve_output(log_id: int):
    log = db.fetch_log_by_id(log_id)
    tmpfile = tempfile.NamedTemporaryFile(delete=False).name

    resource = Resource(log["compute"], log["storage"])
    stderr = []
    stdout = []
    if log["job_status"] == "running":
        # fetch from running node
        for si in range(len(log["job_steps"])):
            resource.scp_from(resource.compute["nightly_tmp"] + "/%s-%s-stdout.txt" % (log_id, si), tmpfile, resource.compute)
            stdout.append(open(tmpfile, "r").read())
            resource.scp_from(resource.compute["nightly_tmp"] + "/%s-%s-stderr.txt" % (log_id, si), tmpfile, resource.compute)
            stderr.append(open(tmpfile, "r").read())
    else:
        for si in range(len(log["job_steps"])):
            resource.fetch_from_storage(log_id, "%s-%s-stdout.txt" % (log_id, si), tmpfile)
            stdout.append(open(tmpfile, "r").read())
            resource.fetch_from_storage(log_id, "%s-%s-stderr.txt" % (log_id, si), tmpfile)
            stderr.append(open(tmpfile, "r").read())

    return render_template('output.html', log_id=log_id, stderr=stderr, stdout=stdout)
