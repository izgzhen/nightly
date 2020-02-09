import yaml
import glob
import os
import pymysql
import json
import time

from msbase.logging import logger

resources_config = yaml.safe_load(open("config/resources.yaml", "r"))

def prepare_insert_query(row_dict, table):
    row_items = list(row_dict.items())
    fields = ", ".join([ k for k, v in row_items ])
    placeholders = ", ".join([ "%s" for k, v in row_items ])
    values = tuple(v for k, v in row_items)
    return "INSERT INTO %s (%s) VALUES (%s)" % (table, fields, placeholders), values

def decode_entry(entry):
    for col in ["job_steps", "job_persisted", "storage", "compute"]:
        entry[col] = json.loads(entry[col])
    return entry

class DB(object):
    def __init__(self):
        self.db_connection_retry_in_seconds = 60
        print("Connecting DB")
        self.db_ = pymysql.connect(**resources_config["logdb"])

    def db(self):
        try:
            self.db_.ping(reconnect=False)
        except Exception as e:
            print(e)
            time.sleep(self.db_connection_retry_in_seconds)
            self.db_connection_retry_in_seconds += 60
            print("Connecting DB")
            self.db_ = pymysql.connect(**resources_config["logdb"])
        return self.db_

    def exec(self, query, args=()):
        with self.db() as cur:
            logger.info(query % args)
            cur.execute(query, args)
        self.db().commit()

    def exec_fetch(self, query, args=(), mode=str, return_dict=False):
        assert mode in ["one", "all"]
        if return_dict:
            cur = self.db().cursor(pymysql.cursors.DictCursor)
        else:
            cur = self.db().cursor()
        cur.execute(query, args)
        if mode == "one":
            ret = cur.fetchone()
        else:
            ret = cur.fetchall()
        cur.close()
        self.db().commit()
        return ret

    def exec_fetch_one(self, query, args=(), return_dict=False):
        return self.exec_fetch(query, args, mode="one", return_dict=return_dict)

    def exec_fetch_all(self, query, args=(), return_dict=False):
        return self.exec_fetch(query, args, mode="all", return_dict=return_dict)

    def fetch_log_by_id(self, log_id: int):
        return decode_entry(self.exec_fetch_one("SELECT * FROM log WHERE log_id = %s", (log_id,), return_dict=True))

    def total_log_count(self):
        return self.exec_fetch_one("SELECT COUNT(*) FROM log")[0]

    def fetch_all_jobs(self):
        return [ decode_entry(e) for e in self.exec_fetch_all("SELECT * FROM log", return_dict=True) ]

    def upgrade(self):
        max_version = "1000"
        cur = self.db().cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS metadata (`version` TEXT NOT NULL)")
        cur.execute("SELECT `version` FROM metadata")
        ret_all = cur.fetchall()
        cur.close()
        assert len(ret_all) <= 1
        if len(ret_all) == 0:
            cur = self.db().cursor()
            cur.execute("INSERT INTO metadata (`version`) VALUES (%s)" % max_version)
            cur.close()
        else:
            max_version = ret_all[0][0]
        for f in sorted(glob.glob("schema/*.sql")):
            current_version = os.path.basename(f).split("-")[0]
            if current_version > max_version:
                cur = self.db().cursor()
                query = open(f, "r").read()
                print(query)
                cur.execute(query)
                max_version = max(current_version, max_version)
                cur.close()
        cur = self.db().cursor()
        cur.execute("UPDATE metadata SET `version` = %s" % max_version)
        cur.close()
        self.db().commit()

    def update_pid(self, job_id, pid):
        self.exec("UPDATE log SET pid = %s WHERE log_id = %s", (pid, job_id))

    def get_last_run_started(self, job):
        return self.exec_fetch_one("SELECT MAX(job_started) FROM log WHERE job_name = %s", job["name"])[0]

    def fetch_running_jobs_of(self, job):
        return self.exec_fetch_all("SELECT * FROM log WHERE job_name = %s AND job_status = 'running'", job["name"])

    def insert_row(self, row_dict, table):
        query, values = prepare_insert_query(row_dict, table)
        self.exec(query, values)

    def insert_row_get_id(self, row_dict, table):
        cur = self.db().cursor()
        query, values = prepare_insert_query(row_dict, table)
        logger.info(query)
        cur.execute(query, values)
        cur.execute("SELECT LAST_INSERT_ID()")
        ret = cur.fetchone()[0]
        cur.close()
        self.db().commit()
        return ret

    def fetch_all_running_jobs(self):
        return [ decode_entry(e) for e in self.exec_fetch_all("SELECT * FROM log WHERE job_status = 'running'", return_dict=True) ]

    def update_job_status(self, job_id, status, finished):
        self.exec("UPDATE log SET job_status = %s, job_finished = %s WHERE log_id = %s", (status, finished, job_id))

    def commit(self):
        self.db().commit()