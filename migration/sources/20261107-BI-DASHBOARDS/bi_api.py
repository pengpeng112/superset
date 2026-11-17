# -*- coding: utf-8 -*-
"""20261107-BI-DASHBOARDS 剩余任务共用 API 辅助（凭据一律环境变量 ACC_ADMIN / ACC_GUEST）。"""
import json
import os
import re
import time

import requests

BASE = "http://127.0.0.1:18180"


def session(user, pw):
    s = requests.Session()
    r = s.get(BASE + "/login/", timeout=30)
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text).group(1)
    s.post(BASE + "/login/", data={"username": user, "password": pw, "csrf_token": tok}, timeout=30)
    try:  # Gamma 无该端点权限（403），只读取数不需要 CSRF
        rt = s.get(BASE + "/api/v1/security/csrf_token/", timeout=30)
        s.headers["X-CSRFToken"] = rt.json()["result"]
    except Exception:
        pass
    s.headers["Referer"] = BASE + "/"
    return s


def admin():
    return session("admin", os.environ["ACC_ADMIN"])


def guest():
    return session("003158", os.environ["ACC_GUEST"])


def get_chart(s, cid):
    r = s.get(BASE + "/api/v1/chart/%d" % cid, timeout=60)
    r.raise_for_status()
    return r.json()["result"]


def put_chart(s, cid, body):
    r = s.put(BASE + "/api/v1/chart/%d" % cid, json=body, timeout=60)
    return r.status_code, (r.text[:300] if not r.ok else "")


def chart_params(s, cid):
    c = get_chart(s, cid)
    return json.loads(c["params"]), c


def put_params(s, cid, params, extra=None):
    """整包覆盖 params（GET 回读→改→PUT），extra 为同请求其他顶层字段（如 slice_name/viz_type）。"""
    body = {"params": json.dumps(params, ensure_ascii=False)}
    if extra:
        body.update(extra)
    return put_chart(s, cid, body)


def get_dashboard(s, did):
    r = s.get(BASE + "/api/v1/dashboard/%d" % did, timeout=60)
    r.raise_for_status()
    return r.json()["result"]


def q(s, ds, query, form_data=None, force=False, viz="table", timeout=300):
    """chart/data 只读取数。filters 键为 col/op/val。"""
    fd = {"datasource": "%d__table" % ds, "viz_type": viz}
    if form_data:
        fd.update(form_data)
    payload = {"datasource": {"id": ds, "type": "table"}, "force": force,
               "queries": [dict({"filters": [], "row_limit": 1000, "extras": {"having": "", "where": ""}}, **query)],
               "form_data": fd, "result_format": "json", "result_type": "full"}
    t0 = time.time()
    rr = s.post(BASE + "/api/v1/chart/data", json=payload, timeout=timeout)
    dt = round(time.time() - t0, 1)
    if not rr.ok:
        return {"http": rr.status_code, "sec": dt, "err": rr.text[:300]}
    r0 = rr.json()["result"][0]
    return {"http": 200, "sec": dt, "rows": r0.get("rowcount"), "data": r0.get("data"),
            "sql": r0.get("query"), "is_cached": r0.get("is_cached")}


def S(col, label="v", agg="SUM"):
    return {"expressionType": "SIMPLE", "column": {"column_name": col}, "aggregate": agg, "label": label}


def SQLM(expr, label="v"):
    return {"expressionType": "SQL", "sqlExpression": expr, "label": label}


def TR(col, rng):
    return {"col": col, "op": "TEMPORAL_RANGE", "val": rng}


def val(x):
    try:
        return x["data"][0]["v"]
    except Exception:
        return x.get("err") or x.get("http")
