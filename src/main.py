import yaml
import time
import pymysql

jobs_config = yaml.safe_load(open("config/jobs.yaml", "r"))
resources_config = yaml.safe_load(open("config/resources.yaml", "r"))

db = pymysql.connect(**resources_config["logdb"])

while True:
    print("Check")
    db.ping()
    time.sleep(1)