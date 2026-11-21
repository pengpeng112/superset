# -*- coding: utf-8 -*-
"""推送 phase3b_chart_windows.py 到服务器 worker 执行并回捞结果。"""
import base64
import json
import os
import sys

sys.path.insert(0, r"F:\python\superset\migration\tools")
import remote_exec  # noqa: E402
from remote_exec import run  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL = os.path.join(HERE, "phase3b_chart_windows.py")
EVID = os.path.join(HERE, "evidence")
RMT_DIR = "/home/superset/superset_home/scripts/migration_20261121"


def main():
    jb, tgt = remote_exec.connect()
    try:
        with open(LOCAL, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        rc, out, err = run(tgt, (
            "umask 022; mkdir -p %s; base64 -d > %s/phase3b_chart_windows.py <<'__HHB64__'\n%s\n__HHB64__\n"
            "md5sum %s/phase3b_chart_windows.py"
        ) % (RMT_DIR, RMT_DIR, data, RMT_DIR), timeout=120)
        assert rc == 0 and ".py" in out, out + err
        print("uploaded")
        rc, out, err = run(tgt, (
            'ADMPW=$(cat /home/superset/secrets/ADMIN_INIT_PASSWORD); '
            'docker exec -e SUP_BASE=http://superset-web:8088 -e SUP_ADMIN=admin '
            '-e SUP_ADMIN_PWD="$ADMPW" -e PYTHONIOENCODING=utf-8 '
            'superset-worker /app/.venv/bin/python %s/phase3b_chart_windows.py; echo "EXIT=$?"; '
            'cp /tmp/phase3b_result.json /home/superset/migration-private/20261121-RBAC-FRONTEND-POLISH/ 2>/dev/null; true'
        ) % RMT_DIR, timeout=600)
        print(out)
        print(err[-400:])
        rc2, out2, err2 = run(tgt, "base64 -w0 /home/superset/migration-private/20261121-RBAC-FRONTEND-POLISH/phase3b_result.json 2>/dev/null || base64 -w0 /tmp/phase3b_result.json", timeout=60)
        if rc2 == 0:
            with open(os.path.join(EVID, "phase3b_result.json"), "wb") as f:
                f.write(base64.b64decode(out2.strip()))
            print("saved evidence/phase3b_result.json")
        assert "PHASE3B DONE ok=True" in out, "phase3b failed"
    finally:
        tgt.close()
        jb.close()


if __name__ == "__main__":
    main()
