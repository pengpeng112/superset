# -*- coding: utf-8 -*-
"""20261120-RBAC-BACKEND 阶段1回退：把矩阵 apply 的全部写入一键还原到基线。

回退语义（确定性，不依赖 /tmp/rbac_changes_applied.json，该文件仅作交叉核对）：
  1) 34 张业务看板（GAMMA_UNBIND）→ 仅绑 Gamma；看板 34 保持仅 Gamma；
     既有 4 角色绑定（2/61-70/47/49/50-52）原样保留；通道 REST PUT dashboard；
  2) 数据集授权 → 恢复基线 6 条（341:ds4；344:ds279/321；345:ds276/332/333），
     本批新增 datasource_access 的 ab_permission_view_role 行由 SQL 直删单事务完成
     （6.1.0 REST dataset 端点无 roles 字段已证伪）。apply 自建的 ab_view_menu /
     ab_permission_view 行删 pvr 后无角色引用、语义惰性，刻意不删——防误删基线
     前已存在的同例行；字节级极端还原走阶段0 pg_dump 备份；
  3) 删除 7 个新建角色（按精确名匹配，成员必须为 0 才删，绝不触碰
     341/343/344/345 与内置角色）；REST DELETE 不可用则降级 SQL 直删
     （引用已清：pvr 步先删、看板步先还原）；
  4) 用户与科室角色零触碰。

安全校验：回退前现状必须落在「基线态…矩阵终态」之间，任何基线/终态之外的角色绑定
或数据集授权（人工改动痕迹）→ 拒绝回退并列明细，防止覆盖他人手工调整。

用法（superset-worker 容器内）：
  dry-run: /app/.venv/bin/python /app/superset_home/scripts/migration_20261120/rollback_rbac_matrix.py
  apply  : 同上加 --apply
环境变量同 apply_rbac_matrix.py。
输出：/tmp/rbac_rollback_report.json
"""
import argparse
import datetime
import fcntl
import json
import os
import re
import sys
import time

import psycopg2
import psycopg2.extras
import requests

from importlib import util as _ilu
_here = os.path.dirname(os.path.abspath(__file__))
_spec = _ilu.spec_from_file_location(
    "apply_rbac_matrix", os.path.join(_here, "apply_rbac_matrix.py"))
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
# 复用 apply 脚本的全部常量与读状态/REST 通道，保证两脚本口径完全一致
GAMMA_ID = _mod.GAMMA_ID
NEW_ROLE_MATRIX = _mod.NEW_ROLE_MATRIX
GAMMA_UNBIND = _mod.GAMMA_UNBIND
GAMMA_KEEP = _mod.GAMMA_KEEP
BASELINE_DS_ACCESS = _mod.BASELINE_DS_ACCESS
EXISTING_ROLE_DASH = _mod.EXISTING_ROLE_DASH
connect_ro = _mod.connect_ro
connect_rw = _mod.connect_rw
read_state = _mod.read_state
q = _mod.q
Api = _mod.Api
ROLE_341, ROLE_343, ROLE_344, ROLE_345 = _mod.ROLE_341, _mod.ROLE_343, _mod.ROLE_344, _mod.ROLE_345

REPORT_PATH = "/tmp/rbac_rollback_report.json"
LOCK_PATH = "/tmp/user_sync.lock"
REVOKE_SQL_PATH = "/tmp/rbac_revoke_sql.sql"

# SQL 直删：本批新增 (role_id, ds_id) 的 datasource_access pvr 行（单事务）
REVOKE_PVR_SQL = """
WITH need(role_id, vm) AS (
    SELECT DISTINCT unnest(%(role_ids)s::int[]), unnest(%(vm_names)s::text[])
)
DELETE FROM ab_permission_view_role pvr
USING need n
JOIN ab_view_menu vm ON vm.name = n.vm
JOIN ab_permission p ON p.name = 'datasource_access'
JOIN ab_permission_view pv ON pv.permission_id = p.id AND pv.view_menu_id = vm.id
WHERE pvr.permission_view_id = pv.id AND pvr.role_id = n.role_id
"""


def revoke_ds_access(pairs, ds_perm):
    """单事务删除 (role_id, ds_id) 对应 datasource_access 的 pvr 行。返回 SQL 全文存证。"""
    params = {"role_ids": [r for r, _ in sorted(pairs)],
              "vm_names": [ds_perm[d] for _, d in sorted(pairs)]}
    conn = connect_rw()
    try:
        with conn.cursor() as rc:
            rc.execute("SELECT id FROM ab_permission WHERE name = 'datasource_access'")
            prow = rc.fetchall()
            if len(prow) != 1:
                raise RuntimeError("ab_permission.datasource_access 行数=%d（应为 1）"
                                   % len(prow))
            text = rc.mogrify(REVOKE_PVR_SQL, params).decode("utf-8")
            rc.execute(REVOKE_PVR_SQL, params)
        conn.commit()
        with open(REVOKE_SQL_PATH, "w", encoding="utf-8") as f:
            f.write("-- %s rollback 数据集授权撤销事务（实际执行原文）\n"
                    % "20261120-RBAC-BACKEND")
            f.write("BEGIN;\n" + text.strip("\n") + ";\nCOMMIT;\n")
        return text
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def rw_delete_role(rid):
    """REST 角色删除不可用时的 SQL 降级（引用已在前序步骤清理）。"""
    conn = connect_rw()
    try:
        with conn.cursor() as rc:
            rc.execute("DELETE FROM ab_role WHERE id = %s", (rid,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# 基线看板绑定（阶段0 pg_dump 证据）
BASELINE_DASH_ROLES = {d: {GAMMA_ID} for d in GAMMA_UNBIND + GAMMA_KEEP}
for _rid, _ds in EXISTING_ROLE_DASH.items():
    for _d in _ds:
        BASELINE_DASH_ROLES[_d] = {_rid}
# 基线数据集角色
BASELINE_DS_ROLES = {}
for _rid, _ds in BASELINE_DS_ACCESS:
    BASELINE_DS_ROLES.setdefault(_ds, set()).add(_rid)


def plan_rollback(st, problems):
    """判定现状合法并给出回退动作清单。"""
    new_ids = {}
    for name, _, _ in NEW_ROLE_MATRIX:
        if name in st["role_id"]:
            new_ids[name] = st["role_id"][name]

    # 允许出现在 34 张看板上的角色白名单 = Gamma + 344/345(目录补绑) + 7 新角色
    allowed = {GAMMA_ID, ROLE_344, ROLE_345} | set(new_ids.values())
    dash_todo = {}
    for d in GAMMA_UNBIND:
        cur = st["dash_roles"].get(d, set())
        extra = cur - allowed
        if extra:
            problems.append("F-DRIFT 看板 %s 挂基线/终态外角色 %s" % (d, sorted(extra)))
            continue
        if GAMMA_ID in cur and cur != {GAMMA_ID}:
            problems.append("F-DRIFT 看板 %s Gamma 与其他角色混挂 %s" % (d, sorted(cur)))
            continue
        if cur != BASELINE_DASH_ROLES[d]:
            dash_todo[d] = cur
    if st["dash_roles"].get(GAMMA_KEEP[0], set()) != {GAMMA_ID}:
        problems.append("F-KEEP 看板 %s 应仅绑 Gamma: %s"
                        % (GAMMA_KEEP[0], sorted(st["dash_roles"].get(GAMMA_KEEP[0], set()))))
    extra_gamma = sorted(d for d, rl in st["dash_roles"].items()
                         if GAMMA_ID in rl and d not in GAMMA_UNBIND + GAMMA_KEEP)
    if extra_gamma:
        problems.append("F-DRIFT Gamma 越界绑定看板: %s" % extra_gamma)

    # 数据集：现 pair 集必须 ⊆ 基线 ∪ 终态
    fin_pairs = _mod.final_ds_pairs(new_ids)
    cur_pairs = set()
    for ds_id, roles in st["ds_roles"].items():
        for rid in roles:
            cur_pairs.add((rid, ds_id))
    beyond = cur_pairs - (fin_pairs | BASELINE_DS_ACCESS)
    if beyond:
        problems.append("F-DRIFT datasource_access 基线/终态外条目: %s" % sorted(beyond))
    missing_base = BASELINE_DS_ACCESS - cur_pairs
    if missing_base:
        problems.append("F-DRIFT 基线 datasource_access 缺失: %s" % sorted(missing_base))
    ds_todo = {}
    for ds_id, roles in st["ds_roles"].items():
        base = BASELINE_DS_ROLES.get(ds_id, set())
        if roles != base and (roles - base):
            ds_todo[ds_id] = roles

    # 既有 4 角色成员保护（回退绝不触碰）
    for rid in (ROLE_341, ROLE_343):
        n = st["members"].get(rid, 0)
        if rid == ROLE_341 and n != 1:
            problems.append("F-PROTECT 角色 341 成员数 %s != 1" % n)
        if rid == ROLE_343 and n != 1:
            problems.append("F-PROTECT 角色 343 成员数 %s != 1" % n)

    # 待删角色：必须 0 成员
    roles_todo = []
    for name, _, _ in NEW_ROLE_MATRIX:
        rid = new_ids.get(name)
        if rid is None:
            continue
        if st["members"].get(rid, 0):
            problems.append("F-PROTECT 新角色 %s(id=%s) 有成员 %s，拒绝删除"
                            % (name, rid, st["members"].get(rid)))
            continue
        roles_todo.append((name, rid))
    return dash_todo, ds_todo, roles_todo


def final_verify_rollback(st_before, st):
    problems = []
    checks = []

    def add(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": str(detail)})
        if not ok:
            problems.append("%s %s" % (name, detail))

    bad = []
    for d, expect in BASELINE_DASH_ROLES.items():
        cur = st["dash_roles"].get(d, set())
        if cur != expect:
            bad.append({"id": d, "expect": sorted(expect), "got": sorted(cur)})
    add("dashboards_baseline", not bad, json.dumps(bad, ensure_ascii=False))

    gamma_bound = sorted(d for d, rl in st["dash_roles"].items() if GAMMA_ID in rl)
    add("gamma_back_to_35", gamma_bound == sorted(GAMMA_UNBIND + GAMMA_KEEP), gamma_bound)

    cur_pairs = set()
    for ds_id, roles in st["ds_roles"].items():
        for rid in roles:
            cur_pairs.add((rid, ds_id))
    add("ds_access_baseline", cur_pairs == BASELINE_DS_ACCESS,
        "missing=%s extra=%s" % (sorted(BASELINE_DS_ACCESS - cur_pairs),
                                  sorted(cur_pairs - BASELINE_DS_ACCESS)))

    leftover = [n for n, _, _ in NEW_ROLE_MATRIX if n in st["role_id"]]
    add("new_roles_deleted", not leftover, leftover)

    add("role341_member", st["members"].get(ROLE_341, 0) == 1, st["members"].get(ROLE_341))
    add("role343_member", st["members"].get(ROLE_343, 0) == 1, st["members"].get(ROLE_343))
    add("ab_role_count", st["counts"]["ab_role"] == 344, st["counts"]["ab_role"])
    add("dashboard_roles_rows", st["counts"]["dashboard_roles"] == 51,
        st["counts"]["dashboard_roles"])
    add("ds_access_rows", st["counts"]["ds_access"] == 6, st["counts"]["ds_access"])
    add("user_roles_untouched",
        st["counts"]["ab_user_role"] == st_before["counts"]["ab_user_role"],
        "%s->%s" % (st_before["counts"]["ab_user_role"], st["counts"]["ab_user_role"]))
    add("gamma_perm_count_unchanged",
        st["role_pv_count"].get(GAMMA_ID, 0) == st_before["role_pv_count"].get(GAMMA_ID, 0),
        "%s->%s" % (st_before["role_pv_count"].get(GAMMA_ID, 0),
                    st["role_pv_count"].get(GAMMA_ID, 0)))
    nds_b = st_before["counts"]["ab_permission_view_role"] - st_before["counts"]["ds_access"]
    nds_a = st["counts"]["ab_permission_view_role"] - st["counts"]["ds_access"]
    add("non_ds_perm_rows_unchanged", nds_b == nds_a, "%s->%s" % (nds_b, nds_a))
    bad_seq = []
    for seq, info in sorted(st["fab_seq"].items()):
        next_would = info["last_value"] + (1 if info["is_called"] else 0)
        if next_would <= info["max_id"]:
            bad_seq.append({"seq": seq, "next_would": next_would,
                            "max_id": info["max_id"]})
    add("fab_sequences_healthy", not bad_seq, json.dumps(bad_seq, ensure_ascii=False))
    return {"checks": checks, "problems": problems, "counts_after": st["counts"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真正回退（默认 dry-run）")
    ap.add_argument("--dry-run", action="store_true", help="仅预览回退计划（默认行为，显式给出以便验收脚本调用）")
    args = ap.parse_args()
    if args.apply and args.dry_run:
        ap.error("--apply 与 --dry-run 互斥")
    mode = "apply" if args.apply else "dry-run"

    cur, conn = connect_ro()
    st = read_state(cur)
    problems = []
    dash_todo, ds_todo, roles_todo = plan_rollback(st, problems)

    rep = {
        "batch": "20261120-RBAC-BACKEND",
        "stage": "stage1-rollback",
        "mode": mode,
        "time_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "dashboards_to_restore": {str(d): sorted(v) for d, v in sorted(dash_todo.items())},
        "datasets_to_restore": {str(d): sorted(v) for d, v in sorted(ds_todo.items())},
        "roles_to_delete": [{"name": n, "id": r} for n, r in roles_todo],
        "problems": problems,
        "baseline_counts": st["counts"],
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)

    if problems:
        print("ABORT problems=%d report=%s" % (len(problems), REPORT_PATH))
        for p in problems:
            print("  PROBLEM:", p)
        sys.exit(1)

    print("%s_STATE dash_restore=%d ds_restore=%d roles_delete=%d"
          % (mode.upper(), len(dash_todo), len(ds_todo), len(roles_todo)))
    if not args.apply:
        print("DRYRUN_OK report=%s" % REPORT_PATH)
        sys.exit(0)

    lockfh = open(LOCK_PATH, "a+")
    for _ in range(60):
        try:
            fcntl.flock(lockfh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except OSError:
            time.sleep(2)
    else:
        print("ABORT lock busy: user_sync running?")
        sys.exit(1)

    try:
        api = Api() if (dash_todo or ds_todo or roles_todo) else None

        # 1) 看板恢复基线（先于删角色，避免悬挂引用）
        for d in sorted(dash_todo):
            expect = sorted(BASELINE_DASH_ROLES[d])
            api.call("PUT", "/api/v1/dashboard/%d" % d, {"roles": expect})
            now = set(read_state(cur)["dash_roles"].get(d, set()))
            if now != set(expect):
                raise RuntimeError("dashboard %s restore fail: expect %s got %s"
                                   % (d, expect, sorted(now)))
            print("DASH_RESTORE %d roles=%s" % (d, expect))

        # 2) 数据集恢复基线：SQL 直删本批新增 datasource_access pvr 行（单事务）
        #    （REST dataset 端点无 roles 字段已证伪；apply 自建 vm/pv 行惰性不删）
        if ds_todo:
            pairs = []
            for ds_id in sorted(ds_todo):
                base = BASELINE_DS_ROLES.get(ds_id, set())
                for rid in sorted(ds_todo[ds_id] - base):
                    if not isinstance(rid, int):
                        raise RuntimeError("数据集撤销对角色 id 未解析: %r" % (rid,))
                    pairs.append((rid, ds_id))
            if pairs:
                ds_perm = {d: st["ds_meta"][d][2] for d in {p[1] for p in pairs}}
                revoke_ds_access(pairs, ds_perm)
            now_st = read_state(cur)
            for ds_id in sorted(ds_todo):
                base = BASELINE_DS_ROLES.get(ds_id, set())
                now = set(now_st["ds_roles"].get(ds_id, set()))
                if now != base:
                    raise RuntimeError("ds %s restore fail: expect %s got %s"
                                       % (ds_id, sorted(base), sorted(now)))
            rep["revoke_sql_trace"] = REVOKE_SQL_PATH
            print("DS_REVOKE pairs=%d datasets=%d trace=%s"
                  % (len(pairs), len(ds_todo), REVOKE_SQL_PATH))

        # 3) 删除 7 个新角色（精确名匹配 + 0 成员 + 0 权限行）
        for name, rid in roles_todo:
            snap = read_state(cur)
            if snap["role_id"].get(name) != rid or snap["members"].get(rid, 0) \
                    or snap["role_pv_count"].get(rid, 0):
                raise RuntimeError("role %s(id=%s) 非干净状态，拒绝删除" % (name, rid))
            try:
                api.call("DELETE", "/api/v1/security/roles/%d" % rid)
            except RuntimeError:
                # REST 删除不可用（405/409 等）→ SQL 降级（引用已在前序步骤清理）
                rw_delete_role(rid)
            if q(cur, "SELECT id FROM ab_role WHERE id = %s", (rid,)):
                raise RuntimeError("role delete verify fail: %s(id=%s)" % (name, rid))
            print("ROLE_DELETE %s id=%s" % (name, rid))

        # 4) 终态校验
        verify = final_verify_rollback(st, read_state(cur))
        rep["verify"] = verify
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
        if verify["problems"]:
            print("ROLLBACK_DONE_WITH_PROBLEMS %s" % REPORT_PATH)
            for p in verify["problems"]:
                print("  PROBLEM:", p)
            sys.exit(2)
        print("ROLLBACK_OK report=%s" % REPORT_PATH)
    finally:
        try:
            fcntl.flock(lockfh, fcntl.LOCK_UN)
        finally:
            lockfh.close()
        conn.close()


if __name__ == "__main__":
    main()
