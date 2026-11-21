# -*- coding: utf-8 -*-
"""20261121-RBAC-FRONTEND-POLISH 阶段3-1：BI 看板元数据修正（REST，幂等，回读断言）。

1. 看板 72 原生筛选 NATIVE-FILTER-BI1-DATE 默认窗 2026-09-01 : 2026-10-01
   → 2026-10-01 : 2026-11-01（对齐 74/75 最新完整已结账自然月）；
2. 看板 75 KPI 图表 393/394/395 副标题硬编码 "2026-10 全院合计" → "选定期间全院合计"
   （396 "占用床日/开放床日" 无月份误导，保持不动）；
3. 看板 72 底部汇总表（图表 378）栅格高度 meta.height 14（112px 过扁）→ 44（352px 舒适）。

环境变量：SUP_BASE / SUP_ADMIN / SUP_ADMIN_PWD（run 时注入，不落盘）。
产出：/tmp/phase3_bi_meta_result.json（宿主侧回捞存档 evidence/）。
"""
import json
import os
import sys

import requests

BASE = os.environ.get("SUP_BASE", "http://superset-web:8088").rstrip("/")
USER = os.environ["SUP_ADMIN"]
PWD = os.environ["SUP_ADMIN_PWD"]
OLD_WIN = "2026-09-01 : 2026-10-01"
NEW_WIN = "2026-10-01 : 2026-11-01"
RESULT = {"steps": []}


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
        json.dump(RESULT, open("/tmp/phase3_bi_meta_result.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        sys.exit("ABORT at " + name)


def get_json(s, path):
    r = s.get(BASE + path, timeout=60)
    r.raise_for_status()
    return r.json()["result"]


def main():
    RESULT["ok"] = True
    s = login()
    step("login", True, USER)

    # ---- 1. 看板 72 默认时间窗推进 ----
    d = get_json(s, "/api/v1/dashboard/72")
    jm = json.loads(d["json_metadata"] or "{}")
    nfc = jm.get("native_filter_configuration") or []
    hit = 0
    for f in nfc:
        mask = ((f.get("defaultDataMask") or {}).get("extraFormData") or {}).get("time_range")
        if mask == OLD_WIN:
            f["defaultDataMask"]["extraFormData"]["time_range"] = NEW_WIN
            f["defaultDataMask"]["filterState"]["value"] = NEW_WIN
            hit += 1
        elif mask == NEW_WIN:
            hit += 1  # 幂等：已是目标值
    step("72_default_window_check", hit >= 1, "native filters matched=%d" % hit)
    if hit:
        r = s.put(BASE + "/api/v1/dashboard/72", json={"json_metadata": json.dumps(jm, ensure_ascii=False)}, timeout=60)
        step("72_json_metadata_put", r.status_code == 200, "HTTP %d %s" % (r.status_code, r.text[:120]))
        d2 = get_json(s, "/api/v1/dashboard/72")
        jm2 = json.loads(d2["json_metadata"] or "{}")
        vals = [((f.get("defaultDataMask") or {}).get("extraFormData") or {}).get("time_range")
                for f in (jm2.get("native_filter_configuration") or [])]
        step("72_default_window_verify", NEW_WIN in vals, "readback time_ranges=%s" % vals)

    # ---- 2. 看板 75 KPI 副标题去硬编码 ----
    for cid in (393, 394, 395):
        c = get_json(s, "/api/v1/chart/%d" % cid)
        p = json.loads(c["params"] or "{}")
        old = p.get("subheader")
        if old and old != "选定期间全院合计":
            p["subheader"] = "选定期间全院合计"
            r = s.put(BASE + "/api/v1/chart/%d" % cid,
                      json={"params": json.dumps(p, ensure_ascii=False)}, timeout=60)
            step("chart_%d_put" % cid, r.status_code == 200, "HTTP %d old=%r" % (r.status_code, old))
        c2 = get_json(s, "/api/v1/chart/%d" % cid)
        p2 = json.loads(c2["params"] or "{}")
        step("chart_%d_verify" % cid, p2.get("subheader") == "选定期间全院合计",
             "subheader=%r" % p2.get("subheader"))

    # ---- 3. 看板 72 图表 378 高度 14 → 44 ----
    d = get_json(s, "/api/v1/dashboard/72")
    pos = json.loads(d["position_json"] or "{}")
    changed = 0
    before = after = None
    for k, v in pos.items():
        if not isinstance(v, dict):
            continue
        meta = v.get("meta") or {}
        if meta.get("chartId") == 378:
            before = meta.get("height")
            if meta.get("height") != 44:
                meta["height"] = 44
                changed += 1
            after = meta.get("height")
    step("378_height_found", before is not None, "meta.height before=%s" % before)
    if changed:
        r = s.put(BASE + "/api/v1/dashboard/72", json={"position_json": json.dumps(pos, ensure_ascii=False)}, timeout=60)
        step("72_position_put", r.status_code == 200, "HTTP %d %s" % (r.status_code, r.text[:120]))
    d3 = get_json(s, "/api/v1/dashboard/72")
    pos3 = json.loads(d3["position_json"] or "{}")
    h3 = [ (v.get("meta") or {}).get("height") for v in pos3.values()
           if isinstance(v, dict) and (v.get("meta") or {}).get("chartId") == 378 ]
    step("378_height_verify", h3 == [44], "readback heights=%s" % h3)

    RESULT["ok"] = all(x["ok"] for x in RESULT["steps"])
    json.dump(RESULT, open("/tmp/phase3_bi_meta_result.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("PHASE3 META DONE ok=%s" % RESULT["ok"])
    sys.exit(0 if RESULT["ok"] else 1)


if __name__ == "__main__":
    main()
