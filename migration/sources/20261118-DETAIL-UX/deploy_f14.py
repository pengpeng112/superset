# -*- coding: utf-8 -*-
"""20261118-DETAIL-UX 部署脚本：上传 report-ui.js + 原地覆写 nginx.conf（保 inode 47580611）。
凭据经环境变量 JB_HOST/JB_PORT/JB_USER/JB_PW/TGT_HOST/TGT_USER/TGT_PW 注入，不落盘。
红线遵守：
  - nginx.conf 只经 /tmp 中转 + cp 原地覆写（绝无 mv/rm/sed -i，inode 47580611 保持）
  - 仅 nginx -t + -s reload，不重启任何业务容器
传输走 exec + base64 heredoc（目标机 sftp 子系统不可用，同 remote_exec --put 思路）。
"""
import base64
import gzip
import hashlib
import os
import sys

sys.path.insert(0, r"F:\python\superset\migration\tools")
import remote_exec  # noqa: E402
from remote_exec import run  # noqa: E402

LOCAL_RUI = r"F:\python\superset\offline-bundle\custom\report-ui.js"
LOCAL_NGINX = r"F:\python\superset\offline-bundle\nginx.conf"


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def q(s):
    return "'" + s.replace("'", "'\\''") + "'"


def put_b64(tgt, local, remote):
    """gzip+base64 heredoc 写远程（远程命令行有长度上限，纯 base64 86KB 会超限），
    远程 gunzip 解压到目标（对已有文件=原地截断覆写）。"""
    with open(local, "rb") as f:
        data = base64.b64encode(gzip.compress(f.read(), 9)).decode("ascii")
    r = q(remote)
    cmd = ("umask 022; base64 -d <<'__HHB64__' | gunzip > %s\n%s\n__HHB64__\n"
           "sha256sum %s") % (r, data, r)
    return run(tgt, cmd, timeout=600)


def main():
    jb, tgt = remote_exec.connect()
    try:
        local_rui_sha = sha256_file(LOCAL_RUI)
        local_nginx_sha = sha256_file(LOCAL_NGINX)
        print("local report-ui.js sha256 =", local_rui_sha)
        print("local nginx.conf    sha256 =", local_nginx_sha)

        print("== step1: put report-ui.js -> /home/superset/custom/report-ui.js")
        rc, out, err = put_b64(tgt, LOCAL_RUI, "/home/superset/custom/report-ui.js")
        print((out + err).strip()[-200:])
        assert rc == 0 and local_rui_sha in out, "put report-ui.js failed"
        print("OK")

        print("== step2: put nginx.conf -> /tmp/nginx.conf.f14, then cp in-place")
        rc, out, err = put_b64(tgt, LOCAL_NGINX, "/tmp/nginx.conf.f14")
        print((out + err).strip()[-200:])
        assert rc == 0 and local_nginx_sha in out, "put nginx.conf tmp failed"
        rc, out, err = run(tgt, "cp /tmp/nginx.conf.f14 /home/superset/nginx.conf && echo CP-OK")
        print((out + err).strip())
        assert "CP-OK" in out, "cp in-place failed"
        print("OK")

        print("== step3: pre-reload checks (inode + host sha)")
        rc, out, err = run(tgt, "stat -c %i /home/superset/nginx.conf; sha256sum /home/superset/nginx.conf /home/superset/custom/report-ui.js")
        print(out.strip(), err.strip())
        lines = [l.strip() for l in out.strip().splitlines() if l.strip()]
        inodes = [l for l in lines if l.isdigit()]
        shas = [l.split()[0] for l in lines if len(l.split()[0]) == 64]
        assert inodes and inodes[0] == "47580611", "inode changed before reload: %r" % lines
        assert len(shas) >= 2 and shas[0] == local_nginx_sha and shas[1] == local_rui_sha, \
            "sha mismatch: %r" % shas
        print("PRE-CHECKS OK: inode=47580611, shas match local")

        print("== step4: nginx -t && nginx -s reload")
        rc, out, err = run(tgt, "docker exec superset-nginx nginx -t && docker exec superset-nginx nginx -s reload")
        print(rc, out.strip(), err.strip())
        assert rc == 0, "nginx reload failed"

        print("== step5: post-reload double check (inode + host==container sha)")
        rc, out, err = run(tgt, "sleep 1; stat -c %i /home/superset/nginx.conf; sha256sum /home/superset/nginx.conf; docker exec superset-nginx sha256sum /etc/nginx/conf.d/default.conf")
        print(out.strip(), err.strip())
        lines2 = [l.strip() for l in out.strip().splitlines() if l.strip()]
        inodes2 = [l for l in lines2 if l.isdigit()]
        shas2 = [l.split()[0] for l in lines2 if len(l.split()[0]) == 64]
        assert inodes2 and inodes2[0] == "47580611", "inode changed after reload: %r" % lines2
        assert len(shas2) >= 2 and shas2[0] == shas2[1] == local_nginx_sha, "host/container sha mismatch: %r" % shas2
        print("POST-CHECKS OK: inode=47580611, host==container==local")
        print("DEPLOY SUCCESS")
    finally:
        tgt.close()
        jb.close()


if __name__ == "__main__":
    main()
