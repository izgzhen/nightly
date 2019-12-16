import subprocess

def run_cmd(cmd):
    print("+ " + cmd)
    return subprocess.getoutput(cmd)