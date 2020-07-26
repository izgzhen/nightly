from common import run_cmd, run_cmd_stdout
import yaml
import tempfile
from fabric import Connection
from typing import Dict
import invoke
import requests

from notif import send_text

resources_config = yaml.safe_load(open("config/resources.yaml", "r"))

connection_pool = {} # type: Dict[str, Connection]
def get_connnection(host: str) -> Connection:
    if host in connection_pool:
        return connection_pool[host]
    return Connection(host)

def parse_ps_output(text: str):
    output = text.splitlines()
    headers = [h for h in ' '.join(output[0].strip().split()).split() if h]
    raw_data = map(lambda s: s.strip().split(None, len(headers) - 1), output[1:])
    return [dict(zip(headers, r)) for r in raw_data]

class Resource(object):
    def __init__(self, compute, storage):
        self.master  = resources_config["master"]
        self.compute = compute
        self.storage = storage

    def node_is_master(self, node): return self.master["host"] == node["host"]

    def scp_from(self, src_filepath: str, master_filepath: str, node):
        """
        SSH copy file from node's src_filepath to master_filepath
        """
        assert node in [self.storage, self.compute]
        if self.node_is_master(node):
            cp = "cp"
        else:
            cp = "scp"
            src_filepath = node["host"] + ":" + src_filepath
        run_cmd(cp + " " + src_filepath + " " + master_filepath)

    def scp_to(self, master_filepath: str, tgt_filepath: str, node):
        """
        SSH copy file from master_filepath to node's tgt_filepath
        """
        assert node in [self.storage, self.compute]
        if self.node_is_master(node):
            cp = "cp"
        else:
            cp = "scp"
            tgt_filepath = node["host"] + ":" + tgt_filepath
        run_cmd_stdout([cp, master_filepath, tgt_filepath])

    def ssh_exec_on_node(self, cmd: str, node, noexception=False):
        assert node in [self.storage, self.compute]
        if self.node_is_master(node):
            return run_cmd("bash -c '" + cmd + "'")
        else:
            try:
                result = get_connnection(node["host"]).run(cmd, timeout=10)
                if noexception:
                    return result.stdout, result.stderr, result.return_code
                else:
                    assert result.ok, result.stderr
                    return result.stdout
            except Exception as e:
                if noexception:
                    return None, None, -1
                else:
                    raise e

    def is_pid_running(self, node, pid: int) -> bool:
        pid_str = str(pid)
        if "shell2http" in node:
            shell2http = node["shell2http"]
            resp = requests.get(shell2http["endpoint"] + "/ps", auth=(shell2http["user"], shell2http['password']))
            assert resp.ok, resp.text
            ps_output = parse_ps_output(resp.text)
            return any(proc["PID"] == pid_str for proc in ps_output)
        else:
            stdout, stderr, return_code = self.ssh_exec_on_node("ps -p %s" % pid, node, noexception=True)
            if return_code != 0:
                send_text("is_pid_running failed<br>node: %s<br>pid: %s" % (node, pid))
                return True # something wrong with the ssh, think it is still running
            else:
                return pid_str in stdout

    def persist(self, log_id: str, runner_filepath: str, new_filename: str = None):
        """
        copy file at runner:runner_filepath to storage:storage["where"]/log_id/(new_filename)
        """
        tmpfile = tempfile.NamedTemporaryFile(delete=False).name
        self.scp_from(runner_filepath, tmpfile, self.compute)

        dest_dir = self.storage["where"] + "/" + log_id
        self.ssh_exec_on_node("mkdir -p " + dest_dir, self.storage)
        dest = dest_dir
        if new_filename is not None:
            dest = dest + "/" + new_filename

        self.scp_to(tmpfile, dest, self.storage)

    def fetch_from_storage(self, log_id: int, persisted_item: str, save_to: str):
        """Fetch file from storage node to master node
        """
        print("Fetching output of " + str(log_id) + " to " + save_to)
        if self.storage["host"] == self.master["host"]:
            src = self.storage["where"] + "/" + str(log_id) + "/" + persisted_item
            run_cmd("cp " + src + " " + save_to)
        else:
            src = self.storage["host"] + ":" + self.storage["where"] + "/" + str(log_id) + "/" + persisted_item
            run_cmd("scp " + src + " " + save_to)
