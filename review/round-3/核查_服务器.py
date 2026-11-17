# -*- coding: utf-8 -*-
"""round-3 服务器只读核查脚本（修订版，2026-10-04 对辩后落地）。

修订内容（分歧表 A13/B12/B7）：
- 凭据不再硬编码：从环境变量 SUP_SSH_HOST/SUP_SSH_USER/SUP_SSH_PWD 读取
  （凭据本身经用户 2026-10-04 授权记录于《superset-部署与安装长任务计划-v1》第 2 节）。
- 修正外网探测 `/dev/tcp/ ` 多余空格 bug（原版该检查恒失败）。
- 记录每条远端命令退出码；全部只读命令，不安装、不修改、不重启。
- AutoAddPolicy 保留（一次性核查场景），但首次连接打印主机指纹供人工核对留痕。

用法（PowerShell）：
  $env:SUP_SSH_HOST="10.10.8.73"; $env:SUP_SSH_USER="root"; $env:SUP_SSH_PWD="..."
  python 核查_服务器.py > 核查_服务器.out
用法（Git Bash）：
  SUP_SSH_HOST=10.10.8.73 SUP_SSH_USER=root SUP_SSH_PWD=... python 核查_服务器.py
"""
import os
import socket
import sys

import paramiko

CMDS = [
    ("os", "cat /etc/os-release 2>/dev/null | head -5; uname -a"),
    ("cpu_mem", "nproc; free -h"),
    ("disk", "df -h | grep -Ev 'tmpfs|overlay|shm' | head -15"),
    ("docker", "docker --version 2>&1; docker compose version 2>&1; docker ps -a --format '{{.Names}}\\t{{.Image}}\\t{{.Status}}' 2>&1 | head -20"),
    ("podman", "podman --version 2>&1 | head -1"),
    ("python", "python3 --version 2>&1; pip3 --version 2>&1 | head -1; ls /usr/bin/python* 2>/dev/null"),
    ("node", "node --version 2>&1 | head -1; npm --version 2>&1 | head -1"),
    ("ports_listen", "(ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null) | head -30"),
    ("services", "systemctl list-units --type=service --state=running --no-pager 2>/dev/null | head -35"),
    ("db_oracle_reach", "timeout 4 bash -c '</dev/tcp/10.10.8.216/1521' 2>/dev/null && echo REACH_10.10.8.216_1521_OK || echo REACH_10.10.8.216_1521_FAIL"),
    ("egress", "timeout 4 bash -c '</dev/tcp/mirrors.aliyun.com/443' 2>/dev/null && echo EGRESS_OK || echo EGRESS_FAIL_INTRANET"),
    ("dirs", "ls -d /data /opt /app /home/* 2>/dev/null | head -10; ls /opt 2>/dev/null | head -10"),
    ("nginx", "nginx -v 2>&1 | head -1; which nginx 2>&1"),
    ("selinux_firewall", "getenforce 2>&1; systemctl is-active firewalld 2>&1"),
    ("locale_tz", "timedatectl 2>/dev/null | head -4; locale 2>&1 | head -2"),
    ("cron", "crontab -l 2>&1 | head -10"),
    ("mem_total_mb", "awk '/MemTotal/{print int($2/1024)}' /proc/meminfo"),
    ("existing_superset", "ls -d /opt/superset* /data/superset* 2>/dev/null; docker images 2>/dev/null | grep -i superset | head -5"),
]


def main() -> int:
    host = os.environ.get("SUP_SSH_HOST", "10.10.8.73")
    user = os.environ.get("SUP_SSH_USER", "")
    pwd = os.environ.get("SUP_SSH_PWD", "")
    if not (user and pwd):
        print("[abort] 缺少 SUP_SSH_USER / SUP_SSH_PWD 环境变量（凭据见计划文档第 2 节，勿硬编码）")
        return 2

    print(f"===== target {host} (tcp/22 预探测)")
    s = socket.socket()
    s.settimeout(6)
    try:
        s.connect((host, 22))
        print("tcp/22 OPEN")
    except Exception as exc:  # noqa: BLE001 - 核查脚本需如实记录各类失败
        print(f"tcp/22 UNREACHABLE: {type(exc).__name__}（成因待查：关机/IP 未配/防火墙/需跳板，见 P3-S0 诊断问询）")
        return 1
    finally:
        s.close()

    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(host, username=user, password=pwd, timeout=12, banner_timeout=12, auth_timeout=12)
    key = cli.get_transport().get_remote_server_key()
    print(f"[host-key] {key.get_name()} {key.get_fingerprint().hex()}（首次连接，供人工核对留痕）")
    rc_all = 0
    for tag, cmd in CMDS:
        _, out, err = cli.exec_command(cmd, timeout=25)
        o = out.read().decode("utf-8", "replace").strip()
        e = err.read().decode("utf-8", "replace").strip()
        rc = out.channel.recv_exit_status()
        if rc != 0:
            rc_all = 1
        print(f"===== [{tag}] rc={rc} $ {cmd}")
        if o:
            print(o)
        if e:
            print(f"[stderr] {e[:300]}")
    cli.close()
    print(f"===== DONE read-only inspection rc_all={rc_all}")
    return rc_all


if __name__ == "__main__":
    sys.exit(main())
