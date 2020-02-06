from common import run_cmd
import yaml
import tempfile

resources_config = yaml.safe_load(open("config/resources.yaml", "r"))

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
        run_cmd(cp + " " + master_filepath + " " + tgt_filepath)

    def ssh_exec_on_node(self, cmd: str, node):
        assert node in [self.storage, self.compute]
        if self.node_is_master(node):
            return run_cmd("bash -c '" + cmd + "'")
        else:
            return run_cmd("ssh " + node["host"] + " '" + cmd + "'")

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