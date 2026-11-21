# -*- coding: utf-8 -*-
"""20261121-RBAC-FRONTEND-POLISH 部署：三 JS + nginx.conf（gzip+base64 heredoc，inode 47580611 保持）
+ 预热引擎（--roll-month）与 47 条模板三端对齐 + run_warmup 实跑 + 18 项体检。
凭据经环境变量注入。红线：nginx.conf 只经 /tmp 中转 + cp 原地覆写；仅 nginx -t + -s reload；
不动任何业务容器。"""
import base64
import gzip
import hashlib
import os
import sys

sys.path.insert(0, r"F:\python\superset\migration\tools")
import remote_exec  # noqa: E402
from remote_exec import run  # noqa: E402

LOCALS = [
    (r"F:\python\superset\offline-bundle\custom\home-ui.js", "/home/superset/custom/home-ui.js"),
    (r"F:\python\superset\offline-bundle\custom\report-ui.js", "/home/superset/custom/report-ui.js"),
    (r"F:\python\superset\offline-bundle\custom\roles-zh.js", "/home/superset/custom/roles-zh.js"),
    (r"F:\python\superset\offline-bundle\scripts\superset_cache_warmup.py", "/home/superset/superset_home/scripts/superset_cache_warmup.py"),
    (r"F:\python\superset\offline-bundle\scripts\warmup_templates.json", "/home/superset/superset_home/scripts/warmup_templates.json"),
    (r"F:\python\superset\offline-bundle\nginx.conf", "/home/superset/nginx.conf"),
]
NGINX_IDX = 5


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def q(s):
    return "'" + s.replace("'", "'\\''") + "'"


def put_gz(tgt, local, remote):
    with open(local, "rb") as f:
        data = base64.b64encode(gzip.compress(f.read(), 9)).decode("ascii")
    r = q(remote)
    cmd = "umask 022; base64 -d <<'__HHB64__' | gunzip > %s\n%s\n__HHB64__\nsha256sum %s" % (r, data, r)
    return run(tgt, cmd, timeout=600)


def main():
    jb, tgt = remote_exec.connect()
    try:
        shas = {lp: sha256_file(lp) for lp, _ in LOCALS}
        for lp, _ in LOCALS:
            print("local %s sha256=%s" % (os.path.basename(lp), shas[lp][:16]))

        print("== step1: upload 5 files (3 JS + warmup engine + templates)")
        for i, (lp, rp) in enumerate(LOCALS[:NGINX_IDX]):
            rc, out, err = put_gz(tgt, lp, rp)
            assert rc == 0 and shas[lp] in out, "upload %s failed: %s %s" % (rp, out[-200:], err[-200:])
            print("  OK %s" % rp)

        print("== step2: nginx.conf -> /tmp + cp in-place (inode 47580611)")
        lp, rp = LOCALS[NGINX_IDX]
        rc, out, err = put_gz(tgt, lp, "/tmp/nginx.conf.rfp")
        assert rc == 0 and shas[lp] in out, "tmp upload failed"
        rc, out, err = run(tgt, "cp /tmp/nginx.conf.rfp /home/superset/nginx.conf && echo CP-OK")
        assert "CP-OK" in out, "cp failed"
        print("  cp OK")

        print("== step3: pre-reload checks (inode + host SHA)")
        rc, out, err = run(tgt, "stat -c %i /home/superset/nginx.conf; sha256sum /home/superset/nginx.conf /home/superset/custom/home-ui.js /home/superset/custom/report-ui.js /home/superset/custom/roles-zh.js /home/superset/superset_home/scripts/superset_cache_warmup.py /home/superset/superset_home/scripts/warmup_templates.json")
        print(out.strip())
        lines = [l.strip() for l in out.strip().splitlines() if l.strip()]
        inodes = [l for l in lines if l.isdigit()]
        assert inodes and inodes[0] == "47580611", "inode changed before reload: %s" % inodes
        shas_out = [l.split()[0] for l in lines if len(l.split()[0]) == 64]
        expect = [shas[LOCALS[NGINX_IDX][0]], shas[LOCALS[0][0]], shas[LOCALS[1][0]], shas[LOCALS[2][0]], shas[LOCALS[3][0]], shas[LOCALS[4][0]]]
        assert shas_out == expect, "sha mismatch: %s vs %s" % (shas_out, expect)
        print("PRE-CHECKS OK")

        print("== step4: nginx -t && reload")
        rc, out, err = run(tgt, "docker exec superset-nginx nginx -t && docker exec superset-nginx nginx -s reload")
        print((out + err).strip())
        assert rc == 0, "reload failed"

        print("== step5: post-reload double check (inode + host==container)")
        rc, out, err = run(tgt, "sleep 1; stat -c %i /home/superset/nginx.conf; sha256sum /home/superset/nginx.conf; docker exec superset-nginx sha256sum /etc/nginx/conf.d/default.conf; curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8180/login/")
        print(out.strip())
        lines2 = [l.strip() for l in out.strip().splitlines() if l.strip()]
        inodes2 = [l for l in lines2 if l.isdigit()]
        shas2 = [l.split()[0] for l in lines2 if len(l.split()[0]) == 64]
        assert inodes2 and inodes2[0] == "47580611", "inode changed after reload"
        assert len(shas2) >= 2 and shas2[0] == shas2[1] == shas[LOCALS[NGINX_IDX][0]], "host/container sha mismatch"
        assert lines2[-1] == "200", "login page not 200: %s" % lines2[-1]
        print("POST-CHECKS OK: inode=47580611, host==container==local, login 200")
        print("DEPLOY SUCCESS")
    finally:
        tgt.close()
        jb.close()


if __name__ == "__main__":
    main()
