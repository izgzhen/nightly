from common import run_cmd
import yaml

resources_config = yaml.safe_load(open("config/resources.yaml", "r"))

class Resource(object):
    def __init__(self, compute, storage):
        self.master  = resources_config["master"]
        self.compute = compute
        self.storage = storage

    def scp_compute(self, filepath, renamed: str = None, to_remote: bool = True):
        """
        SSH copy file to compute's working dir
        """
        assert self.compute["type"] == "ubuntu-1804-x86_64"
        dest = self.compute["working_dir"]
        host = self.compute["host"]
        if self.master["host"] == self.compute["host"]:
            cp = "cp"
        else:
            cp = "scp"
            dest = host + ":" + dest
        if renamed is not None:
            dest = dest + "/" + renamed
        if to_remote:
            return run_cmd(cp + " " + filepath + " " + dest)
        else:
            return run_cmd(cp + " " + dest + " " + filepath)

    def ssh_compute(self, command):
        assert self.compute["type"] == "ubuntu-1804-x86_64"
        host = self.compute["host"]
        cmd = "cd " + self.compute["working_dir"] + "; " + command
        if self.master["host"] == self.compute["host"]:
            return run_cmd("bash -c '" + cmd + "'")
        else:
            return run_cmd("ssh " + host + " '" + cmd + "'")

    def persist(self, log_id: str, persisted_item: str, renamed: str = None):
        assert self.storage["type"] == "linux-fs"
        assert self.storage["host"] == self.compute["host"]
        dest_dir = self.storage["where"] + "/" + log_id
        self.ssh_compute("mkdir -p " + dest_dir)
        dest = dest_dir
        if renamed is not None:
            dest = dest + "/" + renamed
        self.ssh_compute("cp -r " + persisted_item + " " + dest)

    def fetch(self, log_id: int, persisted_item: str, save_to: str):
        assert self.storage["type"] == "linux-fs"
        print("Fetching output of " + str(log_id) + " to " + save_to)
        if self.storage["host"] == self.master["host"]:
            src = self.storage["where"] + "/" + str(log_id) + "/" + persisted_item
            run_cmd("cp " + src + " " + save_to)
        else:
            src = self.storage["host"] + ":" + self.storage["where"] + "/" + str(log_id) + "/" + persisted_item
            run_cmd("scp " + src + " " + save_to)