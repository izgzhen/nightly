import yaml
import glob
import os
import pymysql

from msbase.logging import logger

resources_config = yaml.safe_load(open("config/resources.yaml", "r"))

def prepare_insert_query(row_dict, table):
    row_items = list(row_dict.items())
    fields = ", ".join([ k for k, v in row_items ])
    placeholders = ", ".join([ "%s" for k, v in row_items ])
    values = tuple(v for k, v in row_items)
    return "INSERT INTO %s (%s) VALUES (%s)" % (table, fields, placeholders), values

class DB(object):
    def __init__(self):
        self.db = pymysql.connect(**resources_config["logdb"])

    def total_log_count(self):
        cur = self.db.cursor()
        cur.execute("SELECT COUNT(*) FROM log")
        return cur.fetchone()[0]

    def upgrade(self):
        max_version = "1000"
        cur = db.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS metadata (`version` TEXT NOT NULL)")
        cur.execute("SELECT `version` FROM metadata")
        ret_all = cur.fetchall()
        cur.close()
        assert len(ret_all) <= 1
        if len(ret_all) == 0:
            cur = db.cursor()
            cur.execute("INSERT INTO metadata (`version`) VALUES (%s)" % max_version)
            cur.close()
        else:
            max_version = ret_all[0][0]
        for f in sorted(glob.glob("schema/*.sql")):
            current_version = os.path.basename(f).split("-")[0]
            if current_version > max_version:
                cur = db.cursor()
                query = open(f, "r").read()
                print(query)
                cur.execute(query)
                max_version = max(current_version, max_version)
                cur.close()
        cur = db.cursor()
        cur.execute("UPDATE metadata SET `version` = %s" % max_version)
        cur.close()
        db.commit()

    def update_pid(self, job_id, pid):
        cur = self.db.cursor()
        cur.execute("UPDATE log SET pid = %s WHERE log_id = %s", (pid, job_id))
        cur.close()

    def get_last_run(self, job):
        cur = self.db.cursor()
        cur.execute("SELECT MAX(job_started) FROM log WHERE job_name = %s", job["name"])
        return cur.fetchone()[0]

    def insert_row(self, row_dict, table):
        cur = self.db.cursor()
        query, values = prepare_insert_query(row_dict, table)
        logger.info(query)
        cur.execute(query, values)
        cur.close()

    def insert_row_get_id(self, row_dict, table):
        cur = self.db.cursor()
        query, values = prepare_insert_query(row_dict, table)
        logger.info(query)
        cur.execute(query, values)
        cur.execute("SELECT LAST_INSERT_ID()")
        ret = cur.fetchone()[0]
        cur.close()
        return ret

    def fetch_running_jobs(self):
        cur = self.db.cursor(pymysql.cursors.DictCursor)
        cur.execute("SELECT * FROM log WHERE job_status = 'running'")
        return cur.fetchall()

    def update_job_status(self, job_id, status, finished):
        cur = self.db.cursor()
        cur.execute("UPDATE log SET job_status = %s, job_finished = %s WHERE log_id = %s", (status, finished, job_id))
        cur.close()

    def commit(self):
        self.db.commit()