from common import run_cmd

def scp(compute, filepath, renamed: str = None, to_remote: bool = True):
    """
    SSH copy file to compute's working dir
    """
    assert compute["type"] == "ubuntu-1804-x86_64"
    dest = compute["working_dir"]
    host = compute["host"]
    if host in ["localhost", "127.0.0.1"]:
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

def ssh(compute, command):
    assert compute["type"] == "ubuntu-1804-x86_64"
    host = compute["host"]
    cmd = "cd " + compute["working_dir"] + "; " + command
    if host in ["localhost", "127.0.0.1"]:
        return run_cmd("bash -c '" + cmd + "'")
    else:
        return run_cmd("ssh " + host + " '" + cmd + "'")

def persist(compute, storage, log_id: str, persisted_item: str, renamed: str = None):
    assert storage["type"] == "linux-fs"
    assert storage["host"] == compute["host"]
    dest_dir = storage["where"] + "/" + log_id
    ssh(compute, "mkdir -p " + dest_dir)
    dest = dest_dir
    if renamed is not None:
        dest = dest + "/" + renamed
    ssh(compute, "cp -r " + persisted_item + " " + dest)

def fetch(storage, log_id: int, persisted_item: str, save_to: str):
    assert storage["type"] == "linux-fs"
    src = storage["host"] + ":" + storage["where"] + "/" + str(log_id) + "/" + persisted_item
    print("Fetching output of " + str(log_id) + " to " + save_to)
    run_cmd("scp " + src + " " + save_to)