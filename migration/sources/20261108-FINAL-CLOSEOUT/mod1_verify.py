# -*- coding: utf-8 -*-
"""模块1验收探针：h11/g6 版本断言 + bi-overview 别名路径 pageId 行为回归。

断言：
  V1 /superset/dashboard/bi-overview/：hospitalHomeUI.version=20261115h11
  V2 同页：hospitalVisitGuard.version=20261115g6
  V3 同页：documentElement 含 hh-query-ui（isQuery 经 pageId→72 命中区间）
  V4 数字路径 /superset/dashboard/72/：hh-query-ui=true（回归）
  V5 别名 /superset/dashboard/month-work-report-new/：hh-query-ui=true
  V6 别名 /superset/dashboard/mr-discharge-death-detail/：hh-query-ui=true
  V7 首页 /：hh-home=true（回归）
  V8 目录 /superset/dashboard/34/：hh-catalog-compact=true（pageId 34 路径回归）
  S1 生产 HTML sub_filter 已引用 v=20261115h11 与 v=20261115g6
  S2 生产源码 pageId 已是正则捕获版（含 [^/]+ 且无旧 replace 写法）
输出 mod1-verify.json。
"""
import json
import os
import sys
import time

import urllib.request
import websocket

sys.path.insert(0, r"F:\python\superset\migration\sources\20261112-WARMUP-PERF")
from wb_run import Tab, launch, new_tab  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "http://127.0.0.1:18180"

port = 19330
proc, ver = launch(r"C:\Program Files\Google\Chrome\Application\chrome.exe", "mod1", port)
info = new_tab(port)
ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=30)
tab = Tab(ws)
tab.send("Page.enable")
login_ok = tab.login("admin", "<REDACTED-SUPERSET-ADMIN-PW>")

CLASS_CHECK = """(function(){
  var de=document.documentElement;
  return JSON.stringify({query:de.classList.contains('hh-query-ui'),home:de.classList.contains('hh-home'),
    catalog:de.classList.contains('hh-catalog-compact'),path:location.pathname});
})()"""


def visit(path, settle=6):
    tab.send("Page.navigate", {"url": BASE + path})
    time.sleep(2.0)
    for _ in range(30):
        if tab.eval("document.readyState") == "complete":
            break
        time.sleep(0.5)
    time.sleep(settle)
    tab.eval("1+1")


checks = {}

# S1/S2：静态核对生产响应
html = urllib.request.urlopen(BASE + "/superset/dashboard/72/", timeout=15).read().decode("utf-8", "replace")
checks["S1_html_versions"] = ("v=20261115h11" in html and "v=20261115g6" in html, html.count("v=20261115h11"))
src = urllib.request.urlopen(BASE + "/custom/home-ui.js?v=20261115h11", timeout=15).read().decode("utf-8", "replace")
checks["S2_pageid_fixed"] = ("/^\\/superset\\/dashboard\\/([^/]+)\\/?$/" in src and "DASH_ALIASES[m[1]]" in src
                             and "replace(/\\/?$/,'/')" not in src, src[:40])
gsrc = urllib.request.urlopen(BASE + "/custom/report-guards.js?v=20261115g6", timeout=15).read().decode("utf-8", "replace")
checks["S2b_guard_version"] = ("version:'20261115g6'" in gsrc and "lastRenderTs" in gsrc, gsrc[:40])

# V1-V3：别名页
visit("/superset/dashboard/bi-overview/")
st = json.loads(tab.eval(CLASS_CHECK))
checks["V1_h11_version"] = (tab.eval("(window.hospitalHomeUI||{}).version") == "20261115h11",
                            tab.eval("(window.hospitalHomeUI||{}).version"))
checks["V2_g6_version"] = (tab.eval("(window.hospitalVisitGuard||{}).version") == "20261115g6",
                           tab.eval("(window.hospitalVisitGuard||{}).version"))
checks["V3_alias_bi_overview_query_ui"] = (st["query"] is True, st)
# 别名页等价性：bi-overview 应与数字 72 同为查询页（hh-query-ui）且非目录/首页
checks["V3b_alias_not_catalog_home"] = (st["catalog"] is False and st["home"] is False, st)

visit("/superset/dashboard/72/")
st = json.loads(tab.eval(CLASS_CHECK))
checks["V4_numeric_72_query_ui"] = (st["query"] is True and st["path"].rstrip("/").endswith("72"), st)

visit("/superset/dashboard/month-work-report-new/")
st = json.loads(tab.eval(CLASS_CHECK))
checks["V5_alias_mwrn_query_ui"] = (st["query"] is True, st)

visit("/superset/dashboard/mr-discharge-death-detail/")
st = json.loads(tab.eval(CLASS_CHECK))
checks["V6_alias_mrd_query_ui"] = (st["query"] is True, st)

visit("/")
st = json.loads(tab.eval(CLASS_CHECK))
checks["V7_home_regression"] = (st["home"] is True, st)

visit("/superset/dashboard/34/")
st = json.loads(tab.eval(CLASS_CHECK))
checks["V8_catalog34_regression"] = (st["catalog"] is True, st)
dir_rows = tab.eval("(document.querySelectorAll('[data-hh-catalog-name]').length)||"
                    "document.querySelectorAll('.dashboard-markdown a[href*=\"/superset/dashboard/\"]').length")
checks["V8b_catalog34_links"] = ((dir_rows or 0) > 0, dir_rows)

ws.close()
proc.terminate()
time.sleep(1)
proc.kill()

rows = [{"check": k, "pass": bool(v[0]), "detail": str(v[1])[:120]} for k, v in checks.items()]
out = os.path.join(HERE, "mod1-verify.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump({"browser": ver, "login": login_ok, "checks": rows}, f, ensure_ascii=False, indent=1)
for r in rows:
    print(("PASS " if r["pass"] else "FAIL ") + r["check"] + "  " + r["detail"], flush=True)
npass = sum(1 for r in rows if r["pass"])
print("mod1 verify: %d/%d pass  -> %s" % (npass, len(rows), out), flush=True)
