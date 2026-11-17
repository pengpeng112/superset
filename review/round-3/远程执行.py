# -*- coding: utf-8 -*-
"""经跳板机在 10.10.8.73 执行命令（部署执行器）。

用法：
  JB_USER=root JB_PWD=... TGT_USER=root TGT_PWD=... python 远程执行.py "命令1" ["命令2" ...]
  或：cat 命令.txt | JB_USER=... python 远程执行.py -    # 从 stdin 读命令逐条执行
凭据一律环境变量（JB_* 跳板机 / TGT_* 目标机），不硬编码。
"""
import os
import sys

import paramiko

JB_HOST, JB_PORT = "10.10.8.53", 40022
TGT_HOST, TGT_PORT = "10.10.8.73", 22


def connect():
    gw = paramiko.SSHClient()
    gw.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    gw.connect(JB_HOST, port=JB_PORT, username=os.environ["JB_USER"], password=os.environ["JB_PWD"], timeout=15)
    channel = gw.get_transport().open_channel("direct-tcpip", (TGT_HOST, TGT_PORT), ("127.0.0.1", 0))
    tgt = paramiko.SSHClient()
    tgt.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    tgt.connect(TGT_HOST, port=TGT_PORT, username=os.environ["TGT_USER"], password=os.environ["TGT_PWD"], sock=channel, timeout=15)
    return gw, tgt


def main():
    args = sys.argv[1:]
    cmds = [ln.strip() for ln in sys.stdin if ln.strip()] if args == ["-"] else args
    if not cmds:
        print("no commands")
        return 2
    gw, tgt = connect()
    rc_all = 0
    for cmd in cmds:
        print(f"===== $ {cmd}", flush=True)
        _, out, err = tgt.exec_command(cmd, timeout=600)
        o = out.read().decode("utf-8", "replace").rstrip()
        e = err.read().decode("utf-8", "replace").rstrip()
        rc = out.channel.recv_exit_status()
        if o:
            print(o)
        if e:
            print(f"[stderr] {e[:2000]}")
        print(f"===== rc={rc}")
        if rc != 0:
            rc_all = 1
    tgt.close()
    gw.close()
    return rc_all


if __name__ == "__main__":
    sys.exit(main())
