#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_rbac_backend.py — 20261120-RBAC-BACKEND 阶段4 正负向渗透验收（只读为主，
仅正向用例对 003158 做 grant→revoke 闭环，结束态与开始态完全一致）。

环境变量
--------
  SUP_BASE / SUP_ADMIN / SUP_ADMIN_PWD   管理员 REST 通道（同 superset_rbac_manage.py）
  PGPASSWORD                             PG 只读查询
  VERIFY_USER / VERIFY_USER_PWD          渗透测试账号（默认 003158 / 员工初始密码，
                                         由调用方 docker exec -e 注入，不落文件）
  SYNC_ORA_DSN / SYNC_ORA_USER / SYNC_ORA_PWD   可选，齐全才跑 user_sync --dry-run

验收项（与批次任务书一一对应）
--------------------------------
  N1  负向：003158 仅 Gamma+科室 → dashboard 列表仅见外壳 34
  N2  负向：受控看板 41/72 GET → 404
  N3  负向：chart/data 重放 ds350 → 403（数据集闸门）
  N4  负向：SQL Lab 通道拒绝（sqlexecution / saved_query 403/401）
  P1  正向：grant-user 003158→报表授权_护理部管理 → dashboard 41 GET 200
  P2  正向：chart/data ds350 出数 200
  P3  正向：xlsx 导出重放 200 + attachment（report-ui.js exportChart 形状）
  P4  正向：非跨界看板 72/46/32/38/50 仍 404
  P5  正向：revoke-user → 恢复拒绝（41 → 404、ds350 → 403）
  PR1 保护：revoke-user 001283↔病案离院明细 → refused（工具 exit 3）
  PR2 保护：revoke-user 001643↔抗菌办 → refused（工具 exit 3）
  PR3 保护：001283/001643 绑定在位
  S1  同步安全：user_sync --dry-run rc=0 failed=0 且零提「报表授权_」（需 SYNC_ORA_*）
  C1  恒常：Gamma 权限数 36、Gamma 看板绑定仅外壳 34
  C2  恒常：11 个报表授权_ 角色、dashboard_roles=63、ds_access=66、ab_role=351
  C3  恒常：5 序列健康（last_value==max(id)）
  C4  恒常：003158 结束态仅 Gamma+科室_微生物实验室（还原）
  R1  回退保护：rollback --dry-run 在有成员赋权时保护性拒绝（rc=2 拒绝删除），证明回退工具不盲删

产物：/tmp/rbac_verify_report.json。退出码 0=全绿；2=存在红项。
"""

import json
import os
import re
import subprocess
import sys
import traceback
from datetime import datetime, timedelta, timezone

import requests

HERE = os.path.dirname(os.path.abspath(__file__))           # .../scripts/migration_20261120（rollback/apply 同目录）
SCRIPTS_MAIN = os.path.dirname(HERE)                        # .../scripts（superset_rbac_manage / superset_user_sync 所在）
sys.path.insert(0, SCRIPTS_MAIN)
from superset_rbac_manage import Db, Api, ROLE_PREFIX, PROTECTED_BINDINGS, find_user, find_role_id  # noqa: E402

TZ = timezone(timedelta(hours=8))
VERIFY_USER = os.environ.get("VERIFY_USER", "003158")
VERIFY_ROLE = ROLE_PREFIX + "护理部管理"
PROTECTED_TRY = [(p["username"], p["role"]) for p in PROTECTED_BINDINGS]
GAMMA_DASH_KEEP = 34
EXPECT = {"rbac_roles": 11, "dashboard_roles_rows": 63, "ds_access_rows": 66,
          "ab_role_total": 351, "gamma_perm_count": 36}
FIVE_SEQS = ["ab_user_role_id_seq", "ab_role_id_seq", "ab_permission_view_role_id_seq",
             "ab_view_menu_id_seq", "ab_permission_view_id_seq"]
CROSS_DASHBOARDS = [72, 46, 32, 38, 50]  # 院领导/绩效/质控/字典/手术——护理部角色不应跨界

# 浏览器 2026-11-18 实测的看板 41 filter_time 查询 body（ds350，200/403 判据已实证）
REPLAY_BODY = '{"datasource":{"id":350,"type":"table"},"force":false,"queries":[{"filters":[],"extras":{"having":"","where":""},"applied_time_extras":{},"columns":["STAT_BEGIN"],"metrics":["count"],"annotation_layers":[],"row_limit":1000,"series_limit":0,"group_others_when_limit_reached":false,"order_desc":true,"url_params":{"native_filters_key":"T3e4IHcDheo"},"custom_params":{},"custom_form_data":{}}],"form_data":{"enableEmptyFilter":false,"datasource":"350__table","groupby":["STAT_BEGIN"],"adhoc_filters":[],"extra_filters":[],"extra_form_data":{},"metrics":["count"],"row_limit":1000,"showSearch":true,"url_params":{"native_filters_key":"T3e4IHcDheo"},"inView":true,"viz_type":"filter_time","type":"NATIVE_FILTER","dashboardId":41,"native_filter_id":"NATIVE_FILTER-UI-41-COMPAT-H02-DATE","force":false,"result_format":"json","result_type":"full"},"result_format":"json","result_type":"full"}'

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append({"check": name, "ok": bool(ok), "detail": str(detail)[:400]})
    print(("[OK] " if ok else "[FAIL] ") + name + (("  | " + str(detail)) if detail else ""))


def user_session(base, username, password):
    """普通用户 REST 会话：Bearer 即可（实测 Gamma 无 SecurityApi csrf 权限 → csrf_token 403；
    且本工具仅用 GET + chart/data POST，后者实测不需要 X-CSRFToken）。"""
    s = requests.Session()
    r = s.post(base + "/api/v1/security/login",
               json={"username": username, "password": password,
                     "provider": "db", "refresh": True}, timeout=60)
    if r.status_code != 200:
        raise RuntimeError("登录 %s 失败 %s: %s" % (username, r.status_code, r.text[:200]))
    s.headers["Authorization"] = "Bearer " + r.json()["access_token"]
    return s


def replay(s, base, fmt):
    """按 report-ui.js exportChart 的形状重放（丢 URL 查询参数、改 result_format）。"""
    p = json.loads(REPLAY_BODY)
    p["result_format"] = fmt
    p["result_type"] = "full"
    if isinstance(p.get("form_data"), dict):
        p["form_data"]["result_format"] = fmt
        p["form_data"]["result_type"] = "full"
    r = s.post(base + "/api/v1/chart/data", json=p, timeout=120)
    return r


def dash_get(s, base, dash_id):
    return s.get("%s/api/v1/dashboard/%d" % (base, dash_id), timeout=60)


def manage(*args):
    """调用 superset_rbac_manage.py，返回 (returncode, stdout, stderr)。"""
    cmd = [sys.executable, os.path.join(SCRIPTS_MAIN, "superset_rbac_manage.py")] + list(args)
    env = dict(os.environ)
    env.setdefault("SUP_BASE", os.environ.get("SUP_BASE", "http://superset-web:8088"))
    env.setdefault("PYTHONIOENCODING", "utf-8")
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=600)
    return p.returncode, p.stdout, p.stderr


def main():
    base = os.environ.get("SUP_BASE", "http://superset-web:8088").rstrip("/")
    pwd = os.environ.get("VERIFY_USER_PWD", "<REDACTED-DEFAULT-EMPLOYEE-PW>")
    db = Db()

    # ---------- 前置：确认 003158 干净起点（负向用例有效性前提） ----------
    snap_roles = {r["id"]: r["name"] for r in db.q("SELECT id,name FROM ab_role")}
    my_roles = [snap_roles[x["role_id"]] for x in
                db.q("SELECT ur.role_id FROM ab_user_role ur JOIN ab_user u ON u.id=ur.user_id "
                     "WHERE u.username=%s", (VERIFY_USER,))]
    rbac_mine = [r for r in my_roles if r.startswith(ROLE_PREFIX)]
    if rbac_mine:
        print("前置清理：发现 %s 残留 %s，先撤销以还原负向起点" % (VERIFY_USER, rbac_mine))
        for rname in rbac_mine:
            manage("revoke-user", "--username", VERIFY_USER, "--role", rname)

    s = user_session(base, VERIFY_USER, pwd)

    # ---------- N1：dashboard 列表仅见外壳 34 ----------
    r = s.get(base + "/api/v1/dashboard/", params={"q": json.dumps(
        {"order_by": "-changed_on", "page": 0, "page_size": 100})}, timeout=60)
    ids = [d["id"] for d in r.json().get("result", [])] if r.status_code == 200 else []
    check("N1 dashboard列表仅外壳34", r.status_code == 200 and ids == [GAMMA_DASH_KEEP],
          "status=%s ids=%s" % (r.status_code, ids))

    # ---------- N2：受控看板 404 ----------
    codes = {i: dash_get(s, base, i).status_code for i in (41, 72)}
    check("N2 受控看板41/72均404", all(c == 404 for c in codes.values()), codes)

    # ---------- N3：chart/data 重放 403 ----------
    r = replay(s, base, "json")
    check("N3 chart/data重放ds350→403", r.status_code == 403,
          "status=%s" % r.status_code)

    # ---------- N4：SQL Lab 拒绝 ----------
    codes = {}
    codes["sqlexec"] = s.post(base + "/api/v1/sqlexecution/", json={
        "sql": "select 1", "database_id": 1, "schema": None, "tmp_table_name": "",
        "select_as_cta": False, "select_as_cta_method": "TABLE", "queryLimit": 10,
        "runAsync": False}, timeout=60).status_code
    codes["saved_query"] = s.get(base + "/api/v1/saved_query/", timeout=60).status_code
    denied = all(c in (401, 403, 404) for c in codes.values())
    check("N4 SQLLab通道全拒绝(403/401/404)", denied, codes)

    # ---------- P1-P4：正向（grant 003158 → 护理部管理） ----------
    rc, out, err = manage("grant-user", "--username", VERIFY_USER, "--role", VERIFY_ROLE)
    grant_ok = rc == 0 and ("applied" in out or "no_change" in out)
    check("P1 grant-user %s→%s" % (VERIFY_USER, VERIFY_ROLE), grant_ok,
          "rc=%s out=%s err=%s" % (rc, out.strip()[:120], err.strip()[:120]))

    codes = {i: dash_get(s, base, i).status_code for i in (41, 42, 43, 75)}
    check("P1b 授权看板41/42/43/75可达200", all(c == 200 for c in codes.values()), codes)

    r = replay(s, base, "json")
    got_rows = False
    if r.status_code == 200:
        try:
            j = r.json()
            res = j.get("result") if isinstance(j, dict) else j   # 6.1 实测：顶层 {"result":[{...,"data":[...]}]}
            got_rows = bool(res) and isinstance(res[0].get("data"), list) and len(res[0]["data"]) > 0
        except Exception:
            got_rows = False
    check("P2 chart/data出数200", r.status_code == 200 and got_rows,
          "status=%s rows_nonempty=%s" % (r.status_code, got_rows))

    r = replay(s, base, "xlsx")
    cd = r.headers.get("content-disposition", "")
    is_xlsx = r.status_code == 200 and "spreadsheetml" in r.headers.get("content-type", "") \
        and "attachment" in cd
    check("P3 xlsx导出重放200+attachment", is_xlsx, "status=%s cd=%s" % (r.status_code, cd[:80]))

    codes = {i: dash_get(s, base, i).status_code for i in CROSS_DASHBOARDS}
    check("P4 非跨界看板72/46/32/38/50仍404", all(c == 404 for c in codes.values()), codes)

    # ---------- P5：revoke → 恢复拒绝 ----------
    rc, out, err = manage("revoke-user", "--username", VERIFY_USER, "--role", VERIFY_ROLE)
    check("P5a revoke-user", rc == 0 and ("applied" in out or "no_change" in out),
          "rc=%s out=%s" % (rc, out.strip()[:120]))
    code41 = dash_get(s, base, 41).status_code
    code350 = replay(s, base, "json").status_code
    check("P5b 恢复拒绝：41→404、ds350→403",
          code41 == 404 and code350 == 403, "dash41=%s ds350=%s" % (code41, code350))

    # ---------- PR1/PR2：受保护绑定摘除拒绝 ----------
    for i, (u, rname) in enumerate(PROTECTED_TRY, 1):
        rc, out, err = manage("revoke-user", "--username", u, "--role", rname)
        check("PR%d 摘除%s↔%s被拒绝(exit3)" % (i, u, rname), rc == 3, "rc=%s out=%s" % (rc, out.strip()[:150]))

    # ---------- PR3：受保护绑定在位 ----------
    rows = db.q("SELECT u.username, r.name FROM ab_user_role ur "
                "JOIN ab_user u ON u.id=ur.user_id JOIN ab_role r ON r.id=ur.role_id "
                "WHERE r.name LIKE %s", (ROLE_PREFIX + "%",))
    have = {(x["username"], x["name"]) for x in rows}
    missing = [(u, r) for (u, r) in PROTECTED_TRY if (u, r) not in have]
    check("PR3 受保护绑定在位", not missing, "missing=%s" % (missing or "无"))

    # ---------- S1：user_sync --dry-run（需 SYNC_ORA_* 环境变量） ----------
    if all(k in os.environ for k in ("SYNC_ORA_DSN", "SYNC_ORA_USER", "SYNC_ORA_PWD")):
        env = dict(os.environ)
        env.update({"SUP_BASE": base, "RLS_TABLE_ID": "0", "PYTHONIOENCODING": "utf-8"})
        cmd = [sys.executable, os.path.join(SCRIPTS_MAIN, "superset_user_sync.py"), "--dry-run"]
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=900)
        text = p.stdout + p.stderr
        rc0 = p.returncode == 0
        nofail = bool(re.search(r'"failed"\s*:\s*0\b', text)) or ("failed=0" in text)
        norole = (ROLE_PREFIX not in text)
        check("S1 user_sync --dry-run rc=0 failed=0 零提报表授权_",
              rc0 and nofail and norole,
              "rc=%s failed0=%s zeroRole=%s" % (p.returncode, nofail, norole))
    else:
        check("S1 user_sync --dry-run", False, "缺 SYNC_ORA_* 环境变量，未执行")

    # ---------- C1：Gamma 权限 36、看板绑定仅外壳 34 ----------
    gamma = db.q("SELECT id FROM ab_role WHERE name='Gamma'")
    gamma_id = gamma[0]["id"]
    pv = db.q("SELECT count(*) AS c FROM ab_permission_view_role WHERE role_id=%s", (gamma_id,))[0]["c"]
    gd = db.q("SELECT d.id FROM dashboard_roles dr JOIN dashboards d ON d.id=dr.dashboard_id "
              "WHERE dr.role_id=%s", (gamma_id,))
    check("C1 Gamma权限36/看板仅34", pv == EXPECT["gamma_perm_count"] and [x["id"] for x in gd] == [GAMMA_DASH_KEEP],
          "perm=%s dash=%s" % (pv, [x["id"] for x in gd]))

    # ---------- C2：体系计数恒常 ----------
    c_role = db.q("SELECT count(*) AS c FROM ab_role WHERE name LIKE %s", (ROLE_PREFIX + "%",))[0]["c"]
    c_all = db.q("SELECT count(*) AS c FROM ab_role")[0]["c"]
    c_dr = db.q("SELECT count(*) AS c FROM dashboard_roles")[0]["c"]
    ds_rows = db.q("SELECT count(*) AS c FROM ab_permission_view_role pvr "
                   "JOIN ab_permission_view pv2 ON pv2.id=pvr.permission_view_id "
                   "JOIN ab_permission p ON p.id=pv2.permission_id "
                   "JOIN ab_view_menu vm ON vm.id=pv2.view_menu_id "
                   "WHERE p.name='datasource_access' AND vm.name ~ '\\(id:[0-9]+\\)$'")[0]["c"]
    check("C2 体系计数恒常(11角色/63绑定/66授权/351总数)",
          c_role == EXPECT["rbac_roles"] and c_dr == EXPECT["dashboard_roles_rows"]
          and ds_rows == EXPECT["ds_access_rows"] and c_all == EXPECT["ab_role_total"],
          "role=%s dr=%s ds=%s all=%s" % (c_role, c_dr, ds_rows, c_all))

    # ---------- C3：5 序列健康（滞后=危险/超前=无害） ----------
    # FAB 对 PUT users 走增量 diff，每次 grant 消耗 1 个 nextval 而 revoke 只删行 → last 恒 >= max。
    # 危险方向只有滞后（last < max，INSERT 会撞既有 id）；超前仅浪费 id 空间。
    seq_bad = []
    seq_ahead = []
    for seq in FIVE_SEQS:
        row = db.q("SELECT last_value, is_called FROM %s" % seq)[0]
        tbl = seq.replace("_id_seq", "")
        mx = db.q("SELECT coalesce(max(id),0) AS m FROM %s" % tbl)[0]["m"]
        if row["last_value"] < mx:
            seq_bad.append({"seq": seq, "last": row["last_value"], "max": mx})
        elif row["last_value"] > mx:
            seq_ahead.append("%s: +%d" % (seq, row["last_value"] - mx))
    check("C3 五序列无滞后(超前无害)", not seq_bad,
          seq_bad or ("超前量(无害): %s" % "; ".join(seq_ahead) if seq_ahead else "全部对齐"))

    # ---------- C4：003158 结束态还原 ----------
    end_roles = sorted(x["role_id"] and snap_roles[x["role_id"]] for x in
                       db.q("SELECT ur.role_id FROM ab_user_role ur JOIN ab_user u "
                            "ON u.id=ur.user_id WHERE u.username=%s", (VERIFY_USER,)))
    check("C4 %s结束态仅Gamma+科室" % VERIFY_USER,
          not any(r.startswith(ROLE_PREFIX) for r in end_roles), end_roles)

    # ---------- R1：rollback 保护性拒绝（阶段2 已有 311 人成员绑定，全量回退必须拒绝） ----------
    # 正确回退路径（写入手册/最终报告）：先清人员赋权（revoke-dept / sync-policy 清空）→ 再跑 rollback。
    # 此处验证 rollback 的 F-PROTECT 逻辑：成员非 0 的新角色一律拒绝删除 → rc=2 且输出含「拒绝删除」。
    # rollback 退出码语义：1=计划阶段保护性拒绝（F-PROTECT），0=dry-run 通过，2=apply 后校验问题
    rc, out, err = manage_call_rollback()
    r1_ok = rc == 1 and "拒绝删除" in ((out or "") + (err or ""))
    check("R1 rollback 保护性拒绝(有成员时拒绝全量回退, rc=1)", r1_ok,
          "rc=%s out=%s err=%s" % (rc, (out or "").strip()[-200:], (err or "").strip()[-200:]))

    db.close()

    report = {"command": "verify-rbac-backend", "ts": datetime.now(TZ).isoformat(),
              "verify_user": VERIFY_USER, "checks": CHECKS,
              "ok": sum(1 for c in CHECKS if c["ok"]),
              "fail": sum(1 for c in CHECKS if not c["ok"])}
    with open("/tmp/rbac_verify_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\n========== 验收汇总：绿 %d / 红 %d ==========" % (report["ok"], report["fail"]))
    sys.exit(0 if report["fail"] == 0 else 2)


def manage_call_rollback():
    cmd = [sys.executable, os.path.join(HERE, "rollback_rbac_matrix.py"), "--dry-run"]
    env = dict(os.environ)
    env.setdefault("SUP_BASE", os.environ.get("SUP_BASE", "http://superset-web:8088"))
    env.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=900)
        return p.returncode, p.stdout, p.stderr
    except Exception as e:
        return 2, "", str(e)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        traceback.print_exc()
        print("FATAL: %s" % e, file=sys.stderr)
        sys.exit(2)
