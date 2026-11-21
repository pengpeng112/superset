# -*- coding: utf-8 -*-
"""推送 phase3_bi_meta.py 到服务器并在 worker 容器内执行，回捞结果 JSON。
凭据环境变量 JB_*/TGT_* 注入；admin 口令从 /home/superset/secrets/ADMIN_INIT_PASSWORD 现取。"""
import base64
import json
import os
import sys

sys.path.insert(0, r"F:\python\superset\migration\tools")
import remote_exec  # noqa: E402
from remote_exec import run  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL = os.path.join(HERE, "phase3_bi_meta.py")
EVID = os.path.join(HERE, "evidence")


def main():
    jb, tgt = remote_exec.connect()
    try:
        with open(LOCAL, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        rc, out, err = run(tgt, (
            "umask 022; mkdir -p /home/superset/superset_home/scripts/migration_20261121; "
            "base64 -d > /home/superset/superset_home/scripts/migration_20261121/phase3_bi_meta.py <<'__HHB64__'\n%s\n__HHB64__\n"
            "md5sum /home/superset/superset_home/scripts/migration_20261121/phase3_bi_meta.py"
        ) % data, timeout=120)
        assert rc == 0 and ".py" in out, out + err
        print("uploaded superset_home/scripts/migration_20261121/phase3_bi_meta.py")
        rc, out, err = run(tgt, (
            'ADMPW=$(cat /home/superset/secrets/ADMIN_INIT_PASSWORD); '
            'docker exec -e SUP_BASE=http://superset-web:8088 -e SUP_ADMIN=admin '
            '-e SUP_ADMIN_PWD="$ADMPW" -e PYTHONIOENCODING=utf-8 '
            'superset-worker /app/.venv/bin/python /app/superset_home/scripts/migration_20261121/phase3_bi_meta.py; '
            'echo "EXIT=$?"; '
            'cp /tmp/phase3_bi_meta_result.json /home/superset/migration-private/20261121-RBAC-FRONTEND-POLISH/ 2>/dev/null; true'
        ), timeout=600)
        print(out)
        print(err[:800])
        rc2, out2, err2 = run(tgt, "base64 -w0 /home/superset/migration-private/20261121-RBAC-FRONTEND-POLISH/phase3_bi_meta_result.json 2>/dev/null || base64 -w0 /tmp/phase3_bi_meta_result.json", timeout=60)
        if rc2 == 0:
            with open(os.path.join(EVID, "phase3_bi_meta_result.json"), "wb") as f:
                f.write(base64.b64decode(out2.strip()))
            print("saved evidence/phase3_bi_meta_result.json")
        assert "PHASE3 META DONE ok=True" in out, "phase3 failed"
    finally:
        tgt.close()
        jb.close()


if __name__ == "__main__":
    main()
