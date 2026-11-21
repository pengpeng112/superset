# -*- coding: utf-8 -*-
"""上传 warmup_templates.json 到生产（wb 位置 + 服务器历史位置）并实跑 run_warmup.sh + 体检。"""
import hashlib
import os
import sys

sys.path.insert(0, r"F:\python\superset\migration\tools")
import remote_exec  # noqa: E402
from remote_exec import run  # noqa: E402

LOCAL_TPL = r"F:\python\superset\offline-bundle\scripts\warmup_templates.json"


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    sha = sha256_file(LOCAL_TPL)
    import gzip
    import base64
    with open(LOCAL_TPL, "rb") as f:
        data = base64.b64encode(gzip.compress(f.read(), 9)).decode("ascii")
    jb, tgt = remote_exec.connect()
    try:
        cmd = ("umask 022; base64 -d <<'__HHB64__' | gunzip > /tmp/warmup_templates.json\n%s\n__HHB64__\n"
               "sha256sum /tmp/warmup_templates.json") % data
        rc, out, err = run(tgt, cmd, timeout=300)
        assert rc == 0 and sha in out, "b64 upload failed: %s" % (out[-200:] + err[-200:])
        print("uploaded tmp OK", sha[:16])
        # 覆盖生产两处（superset_home/scripts 为 run_warmup.sh 读取位置；/home/superset/scripts 历史同步位置如存在则同步）
        rc, out, err = run(tgt, (
            "cp /tmp/warmup_templates.json /home/superset/superset_home/scripts/warmup_templates.json && "
            "[ -d /home/superset/scripts ] && cp /tmp/warmup_templates.json /home/superset/scripts/warmup_templates.json 2>/dev/null; "
            "sha256sum /home/superset/superset_home/scripts/warmup_templates.json; echo SYNC-OK"))
        print(out.strip()[-400:], err.strip()[:200])
        assert sha in out, "server sha mismatch"
        print("== 实跑 run_warmup.sh ==")
        rc, out, err = run(tgt, "bash /home/superset/superset_home/scripts/run_warmup.sh 2>&1 | tail -22", timeout=900)
        print(out[-1600:], err[-200:])
        rc2, out2, err2 = run(tgt, "tail -5 /home/superset/logs/warmup.log 2>/dev/null; echo; grep -c 'ok' /home/superset/logs/warmup.log 2>/dev/null | tail -1")
        print(out2[-600:])
    finally:
        tgt.close()
        jb.close()


if __name__ == "__main__":
    main()
