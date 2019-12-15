import yaml
import time
import pymysql
import glob
import sys

jobs_config = yaml.safe_load(open("config/jobs.yaml", "r"))
resources_config = yaml.safe_load(open("config/resources.yaml", "r"))

db = pymysql.connect(**resources_config["logdb"])

# FIXME: use argparse
if len(sys.argv) > 1:
    first_arg = sys.argv[1]
    if first_arg == "--init":
        for f in sorted(glob.glob("schema/*.sql")):
            cur = db.cursor()
            query = open(f, "r").read()
            print(query)
            cur.execute(query)
        sys.exit(0)

while True:
    print("Check")
    db.ping()
    time.sleep(1)