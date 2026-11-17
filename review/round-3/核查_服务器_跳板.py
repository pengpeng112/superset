# -*- coding: utf-8 -*-
"""round-3 H3 决策后核查：经跳板机(BI) 10.10.8.53:40022 登录目标服务器 10.10.8.73。

凭据经环境变量传入（JB_* 跳板机 / TGT_* 目标机），不硬编码；全部只读命令。
用户 2026-10-04 提供跳板机信息并要求"登录下再确定下"。
"""
import sys

import paramiko

JB_HOST = "10.10.8.53"
JB_PORT = 40022
TGT_HOST = "10.10.8.73"
TGT_PORT = 22

JUMP_PROBES = [
    ("jump_info", "hostname; ip -4 addr 2>/dev/null | grep inet | head -6"),
    ("jump_to_73_22", "timeout 4 bash -c '</dev/tcp/10.10.8.73/22' 2>/dev/null && echo TGT_22_OPEN || echo TGT_22_FAIL"),
    ("jump_to_216_1521", "timeout 4 bash -c '</dev/tcp/10.10.8.216/1521' 2>/dev/null && echo REACH_216_1521_OK || echo REACH_216_1521_FAIL"),
]

TARGET_CMDS = [
    ("os", "cat /etc/os-release 2>/dev/null | head -5; uname -m; uname -r"),
    ("cpu_mem", "nproc; free -h"),
    ("disk", "df -h | grep -Ev 'tmpfs|overlay|shm' | head -15"),
    ("docker", "docker --version 2>&1; docker compose version 2>&1; docker ps -a --format '{{.Names}}\\t{{.Image}}\\t{{.Status}}' 2>&1 | head -20"),
    ("python", "python3 --version 2>&1; ls /usr/bin/python* 2>/dev/null"),
    ("ports_listen", "(ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null) | head -30"),
    ("services", "systemctl list-units --type=service --state=running --no-pager 2>/dev/null | head -35"),
    ("db_oracle_reach", "timeout 4 bash -c '</dev/tcp/10.10.8.216/1521' 2>/dev/null && echo REACH_10.10.8.216_1521_OK || echo REACH_10.10.8.216_1521_FAIL"),
    ("egress", "timeout 4 bash -c '</dev/tcp/mirrors.aliyun.com/443' 2>/dev/null && echo EGRESS_OK || echo EGRESS_FAIL_INTRANET"),
    ("dirs", "ls -d /data /opt /app 2>/dev/null; ls /opt 2>/dev/null | head -10"),
    ("selinux_firewall", "getenforce 2>&1; systemctl is-active firewalld 2>&1"),
    ("locale_tz", "timedatectl 2>/dev/null | head -4"),
    ("mem_total_mb", "awk '/MemTotal/{print int($2/1024)}' /proc/meminfo"),
    ("existing_superset", "ls -d /opt/superset* /data/superset* 2>/dev/null; docker images 2>/dev/null | grep -i superset | head -5"),
]


def run(cli, tag, cmd, timeout=25):
    _, out, err = cli.exec_command(cmd, timeout=timeout)
    o = out.read().decode("utf-8", "replace").strip()
    e = err.read().decode("utf-8", "replace").strip()
    rc = out.channel.recv_exit_status()
    print(f"===== [{tag}] rc={rc} $ {cmd}")
    if o:
        print(o)
    if e:
        print(f"[stderr] {e[:300]}")


def main() -> int:
    import os
    jb_user, jb_pwd = os.environ.get("JB_USER", ""), os.environ.get("JB_PWD", "")
    tgt_user, tgt_pwd = os.environ.get("TGT_USER", ""), os.environ.get("TGT_PWD", "")
    if not (jb_user and jb_pwd and tgt_user and tgt_pwd):
        print("[abort] 缺少 JB_USER/JB_PWD/TGT_USER/TGT_PWD 环境变量（凭据见部署计划第 2 节）")
        return 2

    gw = paramiko.SSHClient()
    gw.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    gw.connect(JB_HOST, port=JB_PORT, username=jb_user, password=jb_pwd, timeout=12, banner_timeout=12, auth_timeout=12)
    key = gw.get_transport().get_remote_server_key()
    print(f"[jump] {JB_HOST}:{JB_PORT} connected; host-key {key.get_name()} {key.get_fingerprint().hex()}")
    for tag, cmd in JUMP_PROBES:
        run(gw, tag, cmd)

    print(f"===== [tunnel] direct-tcpip {TGT_HOST}:{TGT_PORT} via jump")
    try:
        channel = gw.get_transport().open_channel("direct-tcpip", (TGT_HOST, TGT_PORT), ("127.0.0.1", 0))
    except Exception as exc:  # noqa: BLE001
        print(f"[tunnel] FAILED: {type(exc).__name__}: {exc}")
        gw.close()
        return 1

    tgt = paramiko.SSHClient()
    tgt.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        tgt.connect(TGT_HOST, port=TGT_PORT, username=tgt_user, password=tgt_pwd, sock=channel, timeout=12, banner_timeout=12, auth_timeout=12)
    except Exception as exc:  # noqa: BLE001
        print(f"[target] SSH FAILED: {type(exc).__name__}: {exc}")
        gw.close()
        return 1
    tkey = tgt.get_transport().get_remote_server_key()
    print(f"[target] {TGT_HOST}:{TGT_PORT} connected; host-key {tkey.get_name()} {tkey.get_fingerprint().hex()}")
    for tag, cmd in TARGET_CMDS:
        run(tgt, tag, cmd)
    tgt.close()
    gw.close()
    print("===== DONE jump+target read-only inspection")
    return 0


if __name__ == "__main__":
    sys.exit(main())
