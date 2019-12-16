from flask import Flask, flash, request, redirect, url_for, render_template
import datetime
import json
import tempfile

from model import DB
from resource import Resource

db = DB()

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html',
                            now=datetime.datetime.now(),
                            logs=db.fetch_all_jobs_json_decoded())


@app.route('/output/<log_id>')
def serve_output(log_id: int):
    log = db.fetch_log_by_id(log_id)
    tf = tempfile.NamedTemporaryFile(delete=False)
    tf.close()
    resource = Resource(json.loads(log["compute"]), json.loads(log["storage"]))
    resource.fetch(log_id, "output.json", tf.name)
    output = json.load(open(tf.name, "r"))
    return render_template('output.html', log_id=log_id, output=output)