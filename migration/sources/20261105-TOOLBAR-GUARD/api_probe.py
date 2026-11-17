# -*- coding: utf-8 -*-
"""独立探针：验证 /api/v1/chart/data 导出请求（CSRF/cookie/xlsx/csv）与登录页 cookie 名。"""
import json
import os
import sys

import requests

BASE = os.environ.get("ACC_BASE", "http://127.0.0.1:18180")

s = requests.Session()
s.headers["User-Agent"] = "hh-probe/1.0"

# 1) 登录页：拿 CSRF cookie
r = s.get(BASE + "/login/", timeout=30)
print("login page:", r.status_code, "cookies:", dict(s.cookies))

csrf = None
for name in ("csrf_token", "csrftoken"):
    if name in s.cookies:
        csrf = s.cookies[name]
        break
# Flask-WTF 登录表单也需要 csrf_token 字段
r2 = s.post(
    BASE + "/login/",
    data={"username": "admin", "password": os.environ["ACC_ADMIN"], "csrf_token": csrf or ""},
    timeout=30,
    allow_redirects=True,
)
print("login post:", r2.status_code, "url:", r2.url, "cookies:", {k: v[:8] + "..." for k, v in s.cookies.items()})

csrf = None
for name in ("csrf_token", "csrftoken"):
    if name in s.cookies:
        csrf = s.cookies[name]
        break
print("csrf cookie:", (csrf or "")[:12], "...")

# 2) 读看板 65 → 图表 349 的 latestQueryFormData 参考：直接用 chart API 拿 form_data
r = s.get(BASE + "/api/v1/chart/349", timeout=30)
print("chart 349:", r.status_code)
params = r.json()["result"]["params"] if r.ok else {}
fd = json.loads(params) if isinstance(params, str) else params
# 构造导出 form_data：取 params 里的查询字段
qfd = {
    "datasource": {"id": fd.get("datasource_id", 363), "type": "table"},
    "viz_type": "table",
    "row_limit": 200,
    "all_columns": fd.get("all_columns", [])[:5],
    "granularity_sqla": fd.get("granularity_sqla"),
    "time_range": "2026-09-16 : 2026-09-17",
    "url_params": fd.get("url_params"),
}
qfd = {k: v for k, v in qfd.items() if v is not None}
hdr = {"X-CSRFToken": csrf or "", "Referer": BASE + "/superset/dashboard/65/"}
for fmt in ("csv", "xlsx"):
    body = {"result_format": fmt, "result_type": "full", "form_data": qfd}
    rr = s.post(BASE + "/api/v1/chart/data", json=body, headers=hdr, timeout=120)
    ct = rr.headers.get("Content-Type", "")
    print(fmt, "->", rr.status_code, ct, "bytes:", len(rr.content))
    if fmt == "csv" and rr.ok:
        print("  csv head:", rr.content[:80])
    if rr.status_code >= 400:
        print("  body:", rr.text[:300])
