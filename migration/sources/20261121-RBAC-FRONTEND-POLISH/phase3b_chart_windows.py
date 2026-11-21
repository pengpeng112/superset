# -*- coding: utf-8 -*-
"""20261121 阶段3 补丁：BI 图表 params.time_range 显式化（对齐 20261119 批 75 号
「显式窗固定防模板默认漂移」模式）。

- 72 号 8 张图表（371-378）：No filter → 2026-10-01 : 2026-11-01（与原生筛选默认窗一致）
- 75 号饼图 398：No filter → 2026-10-01 : 2026-11-01（20261119 验收基线即十月结构；
  其余 393-397/399 建板时已显式）
- 73/74 保持 No filter（sameday 当日口径，业务如此）
用户在页面上切换月份时，原生筛选 apply 正常覆盖图表窗（75 号历史验收实证），交互不变。
幂等 + 回读断言。
"""
import json
import os
import sys

import requests

BASE = os.environ.get("SUP_BASE", "http://superset-web:8088").rstrip("/")
USER = os.environ["SUP_ADMIN"]
PWD = os.environ["SUP_ADMIN_PWD"]
WIN = "2026-10-01 : 2026-11-01"
CHARTS = list(range(371, 379)) + [398]
RESULT = {"steps": [], "ok": True}


def login():
    s = requests.Session()
    r = s.post(BASE + "/api/v1/security/login", timeout=30,
               json={"username": USER, "password": PWD, "provider": "db", "refresh": True})
    r.raise_for_status()
    token = r.json()["access_token"]
    r2 = s.get(BASE + "/api/v1/security/csrf_token/", timeout=30,
               headers={"Authorization": "Bearer " + token})
    r2.raise_for_status()
    s.headers.update({"Authorization": "Bearer " + token, "X-CSRFToken": r2.json()["result"]})
    return s


def step(name, ok, detail):
    RESULT["steps"].append({"step": name, "ok": bool(ok), "detail": detail})
    print("[%s] %s -> %s" % ("OK" if ok else "FAIL", name, detail), flush=True)
    if not ok:
        RESULT["ok"] = False
        json.dump(RESULT, open("/tmp/phase3b_result.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        sys.exit("ABORT at " + name)


def main():
    s = login()
    step("login", True, USER)
    for cid in CHARTS:
        c = s.get(BASE + "/api/v1/chart/%d" % cid, timeout=60).json()["result"]
        p = json.loads(c["params"] or "{}")
        old = p.get("time_range", "<absent>")
        if old != WIN:
            p["time_range"] = WIN
            r = s.put(BASE + "/api/v1/chart/%d" % cid,
                      json={"params": json.dumps(p, ensure_ascii=False)}, timeout=60)
            step("chart_%d_put" % cid, r.status_code == 200, "HTTP %d old=%r" % (r.status_code, old))
        p2 = json.loads(s.get(BASE + "/api/v1/chart/%d" % cid, timeout=60).json()["result"]["params"] or "{}")
        step("chart_%d_verify" % cid, p2.get("time_range") == WIN, "readback=%r" % p2.get("time_range"))
    RESULT["ok"] = all(x["ok"] for x in RESULT["steps"])
    json.dump(RESULT, open("/tmp/phase3b_result.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("PHASE3B DONE ok=%s" % RESULT["ok"])
    sys.exit(0 if RESULT["ok"] else 1)


if __name__ == "__main__":
    main()
