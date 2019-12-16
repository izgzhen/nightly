from flask import Flask
import datetime

app = Flask(__name__)

@app.route('/')
def hello_world():
    return "%s" % datetime.datetime.now()