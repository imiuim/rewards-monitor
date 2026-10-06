#!/usr/bin/env python3
"""SSH 到 170.106.115.45 执行命令 / 传文件的小工具"""
import sys, time
import paramiko

HOST = "170.106.115.45"
USER = "ubuntu"
PW = "235428lsy!"

def get_client():
    for attempt in range(1, 26):
        try:
            c = paramiko.SSHClient()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            c.connect(HOST, username=USER, password=PW, timeout=10, banner_timeout=15)
            return c
        except Exception as e:
            print(f"[attempt {attempt}] {type(e).__name__}: {e}", flush=True)
            time.sleep(10)
    raise SystemExit("SSH 连不上，fail2ban 可能限流")

def run(cmd):
    c = get_client()
    stdin, stdout, stderr = c.exec_command(cmd, timeout=60)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    rc = stdout.channel.recv_exit_status()
    c.close()
    return rc, out, err

def put(local_path, remote_path):
    remote_path = remote_path.replace("~", "/home/ubuntu")
    c = get_client()
    sftp = c.open_sftp()
    sftp.put(local_path, remote_path)
    sftp.close()
    c.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: ssh_run.py <cmd> | put <local> <remote>")
        sys.exit(1)
    if sys.argv[1] == "put":
        put(sys.argv[2], sys.argv[3])
        print("PUT OK", sys.argv[2], "->", sys.argv[3])
    else:
        rc, out, err = run(" ".join(sys.argv[1:]))
        print("RC:", rc)
        print("OUT:", out)
        if err:
            print("ERR:", err)
