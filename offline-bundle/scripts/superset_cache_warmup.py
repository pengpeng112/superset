# -*- coding: utf-8 -*-
"""每日 BI 驾驶舱与核心报表缓存自动预热引擎（20261112-WARMUP-PERF 批）。

原理（Cache Key 100% 命中的关键）：
  浏览器打开看板时，前端把每个图表的 QueryContext POST 到
  /api/v1/chart/data?form_data=…&dashboard_id=N（URL 查询串参与服务端
  get_form_data 合并）。本脚本把 2026-11-14 用 CDP 从真实浏览器首屏抄录的
  39 条请求（10 个看板：72/73/74/32/35/41/45/46/60/63）逐条原样重放：
  - URL（含查询串）与请求体逐字节一致 → QueryContext 一致 → 缓存键一致；
  - 仅把 body.force 改为 true：跳过旧缓存读、重写新值并重置 TTL（force
    不参与缓存键，浏览器次日 force=false 打开必然命中）。
  缓存键与用户无关（生产 RLS=0，全部数据集 SQL 无 current_user_id），
  管理员会话预热全院共享。

凭据一律经环境变量注入（run_warmup.sh 从 /home/superset/.env 读取后
docker compose exec -e 注入），脚本内不硬编码任何口令：
  SUP_BASE          例：http://superset-web:8088（容器内地址）
  SUP_WARMUP_USER   预热专用账号（admin）
  SUP_WARMUP_PWD    口令
可选参数：--dry-run 只列模板不发请求；--no-force 按原样重放（验证命中用）；
  --roll-month OLD NEW   跨自然月维护（20261121 批新增）：重放时把模板内时间窗字符串
    OLD 整串替换为 NEW（例：
    --roll-month "2026-10-01 : 2026-11-01" "2026-11-01 : 2026-12-01"）。
    仅作用于本次重放（不改模板文件），浏览器随后按新月窗打开必然命中新月缓存键。
    注意：跨月还需同步推进各 BI 看板原生筛选默认值与 KPI 副标题等元数据
    （见 migration/sources/20261121-RBAC-FRONTEND-POLISH/，当月以最新完整已结账月为准）。

保护：串行执行，请求间隔 2s，单请求超时 90s；连续 3 个失败自动熔断中止
（绝不拖累 HIS/ODS 源库）。退出码：0 全部成功；1 部分失败；2 熔断中止；
3 登录或模板文件错误。
"""
import json
import os
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FILE = os.path.join(HERE, "warmup_templates.json")
REQ_TIMEOUT = (10, 90)      # 连接 10s / 读取 90s
GAP_SECONDS = 2.0           # 相邻请求间隔，串行低负载
MAX_CONSEC_FAIL = 3         # 连续失败熔断阈值
ROLL = {"from": None, "to": None}  # --roll-month 跨月替换（重放期生效，不改模板文件）


def log(msg):
    print("[warmup] %s" % msg, flush=True)


def load_templates():
    with open(TEMPLATE_FILE, encoding="utf-8") as f:
        doc = json.load(f)
    tpl = doc.get("templates") or []
    if not tpl:
        raise RuntimeError("templates empty: %s" % TEMPLATE_FILE)
    return doc.get("_meta", {}), tpl


def login(base, user, pwd):
    s = requests.Session()
    r = s.post(base + "/api/v1/security/login", timeout=30,
               json={"username": user, "password": pwd, "provider": "db", "refresh": True})
    if r.status_code != 200:
        raise RuntimeError("login failed: %d %s" % (r.status_code, r.text[:120]))
    token = r.json()["access_token"]
    r2 = s.get(base + "/api/v1/security/csrf_token/", timeout=30,
               headers={"Authorization": "Bearer " + token})
    if r2.status_code != 200:
        raise RuntimeError("csrf failed: %d" % r2.status_code)
    csrf = r2.json()["result"]
    s.headers.update({"Authorization": "Bearer " + token, "X-CSRFToken": csrf})
    return s


def warm(s, base, tpl, force=True):
    """重放一条模板，返回 (ok, 耗时ms, 说明)。HTTP 200 且 result[0].status=success 才算成功。"""
    body = json.loads(json.dumps(tpl["body"]))  # 深拷贝，避免污染模板
    if ROLL["from"] and ROLL["to"]:
        # 20261121：--roll-month 跨月——序列化整串替换时间窗（与新月真实首屏请求逐字节一致）
        raw = json.dumps(body, ensure_ascii=False).replace(ROLL["from"], ROLL["to"])
        body = json.loads(raw)
    body["force"] = bool(force)
    label = "d%s/s%s%s" % (tpl["dashboard"], tpl["slice_id"] or "ft",
                           "/" + tpl["viz"] if tpl.get("viz") else "")
    t0 = time.time()
    try:
        r = s.post(base + tpl["url_path"], json=body, timeout=REQ_TIMEOUT)
    except requests.RequestException as e:
        return False, int((time.time() - t0) * 1000), "%s EXC %s" % (label, repr(e)[:90])
    ms = int((time.time() - t0) * 1000)
    if r.status_code != 200:
        return False, ms, "%s HTTP%d %s" % (label, r.status_code, r.text[:90].replace("\n", " "))
    try:
        res = (r.json().get("result") or [{}])[0]
        errs = r.json().get("errors") or []
    except Exception as e:
        return False, ms, "%s BADJSON %s" % (label, repr(e)[:60])
    if errs:
        return False, ms, "%s APIERR %s" % (label, str(errs[0])[:110])
    status = res.get("status")
    if status != "success":
        return False, ms, "%s STATUS=%s err=%s" % (label, status, str(res.get("error"))[:80])
    return True, ms, "%s ok %dms rows=%s key=%s" % (label, ms, res.get("rowcount"),
                                                    (res.get("cache_key") or "")[:12])


def main():
    argv = sys.argv[1:]
    args = set(a for a in argv if not a.startswith("--roll-month"))
    dry = "--dry-run" in args
    force = "--no-force" not in args
    if "--roll-month" in argv:
        i = argv.index("--roll-month")
        try:
            ROLL["from"], ROLL["to"] = argv[i + 1], argv[i + 2]
        except IndexError:
            log("--roll-month 需要两个参数：OLD NEW（时间窗整串，含空格冒号空格）")
            return 3
        if ROLL["from"] == ROLL["to"] or not ROLL["from"]:
            log("--roll-month 参数非法")
            return 3
    base = os.environ.get("SUP_BASE", "http://superset-web:8088").rstrip("/")
    user = os.environ.get("SUP_WARMUP_USER", "")
    pwd = os.environ.get("SUP_WARMUP_PWD", "")
    meta, tpl = load_templates()
    if dry:
        for t in tpl:
            log("DRY d%s s%s %s -> %s" % (t["dashboard"], t["slice_id"], t.get("viz"), t["url_path"][:70]))
        log("DRY total=%d force=%s" % (len(tpl), force))
        return 0
    if not user or not pwd:
        log("missing SUP_WARMUP_USER/SUP_WARMUP_PWD")
        return 3
    t_start = time.time()
    try:
        s = login(base, user, pwd)
    except Exception as e:
        log("login error: %s" % e)
        return 3
    log("start base=%s user=%s templates=%d force=%s" % (base, user, len(tpl), force))
    ok = fail = consec = 0
    breaker = False
    for t in tpl:
        good, ms, note = warm(s, base, t, force=force)
        if good:
            ok += 1
            consec = 0
        else:
            fail += 1
            consec += 1
        log(note)
        if consec >= MAX_CONSEC_FAIL:
            log("CIRCUIT-BREAK: %d consecutive failures, abort remaining %d" %
                (consec, len(tpl) - ok - fail))
            breaker = True
            break
        time.sleep(GAP_SECONDS)
    secs = round(time.time() - t_start, 1)
    log("SUMMARY json=%s" % json.dumps({
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "total": len(tpl), "ok": ok, "fail": fail,
        "duration_secs": secs, "force": force, "circuit_break": breaker,
        "roll_month": (ROLL["from"] + " -> " + ROLL["to"]) if ROLL["from"] else None}, ensure_ascii=False))
    return 2 if breaker else (0 if fail == 0 else 1)


if __name__ == "__main__":
    sys.exit(main())
