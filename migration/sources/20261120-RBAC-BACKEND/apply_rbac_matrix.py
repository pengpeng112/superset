# -*- coding: utf-8 -*-
"""20261120-RBAC-BACKEND 阶段1：应用 11 角色看板/数据集授权矩阵。

写通道（生产实证）：
  建角色  POST /api/v1/security/roles/                body {"name": ...}
          （前置 repair_sequence：ab_role_id_seq 滞后时 setval 到 max(id)，只进不退。
           本批实测 REST 建角色 500 即该序列 nextval 撞主键——20261108 显式 id
           裸 SQL 未推序列的遗留缺陷；pvr 序列同病，授权事务后一并推齐）
  绑看板  PUT  /api/v1/dashboard/<id>                 body {"roles": [角色id...]}
  授数据集 SQL 直写单事务（20261108 create_roles_20261108.sql 同款已实证模式）。
          6.1.0 REST /api/v1/dataset 端点无 roles 字段（datasets/api.py、schemas.py
          源码零命中，PUT 授权会被 marshmallow 静默丢弃）——该通道已证伪弃用。
          幂等三步（全部 NOT EXISTS 防重，id=coalesce(max(id),0)+row_number()）：
            ① ab_view_menu 缺行（view_menu 名 = tables.perm）
            ② ab_permission_view 缺行（datasource_access × view_menu）
            ③ ab_permission_view_role 缺行（pv × 角色）
          tables.perm 与基线 6 条现存 datasource_access view_menu 逐一核对后才用。
读与校验通道：psycopg2 只读连接（readonly=True）；数据集授权用独立第二条
          可写连接仅执行上述事务，apply 全程持有 flock。

用法（superset-worker 容器内）：
  dry-run: /app/.venv/bin/python /app/superset_home/scripts/migration_20261120/apply_rbac_matrix.py
  apply  : 同上加 --apply

环境变量：PGPASSWORD 或 POSTGRES_PASSWORD；SUP_BASE/SUP_ADMIN/SUP_ADMIN_PWD。

安全约束（任务书红线）：
  - apply 全程持有 /tmp/user_sync.lock（flock），避开每日 06:00 用户同步；
  - 严禁 superset init；严禁改数据集 SQL；绝不触碰 341/343 既有成员；
  - 既有绑定只做合并新增，绝不覆盖 341/344/345 现有授权；
  - 数据集授权按「看板 slices ∪ 原生筛选字典数据集」现算，并与任务书硬编码期望集
    逐角色交叉核对，不一致立即中止；
  - 面向终态设计：任意看板/数据集只允许「原始态 / 终态」两种现状，混合=断点续跑，
    其他状态=漂移中止；幂等可重跑；
  - 任何 REST 非 2xx 或即时回读不一致立即中止（用 rollback_rbac_matrix.py 回退）。

输出：/tmp/rbac_apply_plan.json（dry-run）或 /tmp/rbac_changes_applied.json（apply，
      兼作 rollback 输入；角色创建后即落盘并随每步更新，崩溃一致）。
      apply 另存 /tmp/rbac_grant_sql.sql（实际执行的授权 SQL 全文存证）。
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

BATCH = "20261120-RBAC-BACKEND"
LOCK_PATH = "/tmp/user_sync.lock"
PLAN_PATH = "/tmp/rbac_apply_plan.json"
CHANGES_PATH = "/tmp/rbac_changes_applied.json"
GRANT_SQL_PATH = "/tmp/rbac_grant_sql.sql"

GAMMA_ID = 4
ROLE_341, ROLE_343, ROLE_344, ROLE_345 = 341, 343, 344, 345

# ---------- 矩阵常量（2026-11-18 与阶段0审计证据逐项核对） ----------
# 7 个新建角色：名称 -> (管辖看板, 期望数据集集合【硬编码交叉核对】)
NEW_ROLE_MATRIX = [
    ("报表授权_院领导与运营驾驶舱", [72, 73, 74, 75],
     {322, 324, 325, 326, 338, 345, 347, 348, 350, 351, 373, 374, 375}),
    ("报表授权_质控与全院月报", [25, 29, 33, 32, 35, 36, 37, 39, 44, 45],
     {281, 338, 344, 345, 347, 348, 353, 356, 357}),
    ("报表授权_绩效考核管理", [31, 40, 46, 58, 59, 60],
     {283, 329, 336, 337, 353, 358, 359, 361}),
    ("报表授权_护理部管理", [26, 41, 42, 43, 75],
     {350, 351, 352, 355, 375}),
    ("报表授权_门诊与窗口管理", [27, 28, 30, 48, 53, 54, 55, 56, 57, 73],
     {322, 323, 324, 325, 326, 330}),
    ("报表授权_临床科室日常统计", [26, 29, 33, 36, 37, 39, 41],
     {281, 344, 345, 350, 353}),
    ("报表授权_系统字典维护", [38], {346, 349}),
]

# 既有 4 角色看板清单（写前断言 + 数据集现算依据）
EXISTING_ROLE_DASH = {
    ROLE_341: [2],
    ROLE_343: list(range(61, 71)),
    ROLE_344: [47, 49],
    ROLE_345: [50, 51, 52],
}
# 既有角色看板补绑（目录页）
EXISTING_DASH_ADD = {ROLE_344: [27, 28], ROLE_345: [29]}
# 既有角色期望数据集 = 现有授权 ∪ 本批新增
EXISTING_ROLE_DS = {
    ROLE_341: {4},                      # 不变，仅断言
    ROLE_343: set(range(363, 373)),     # 补 61-70 页 10 个数据集
    ROLE_344: {279, 321},               # 不变，仅断言
    ROLE_345: {276, 332, 333, 360, 362},  # 补 51/52 原生筛选字典 360/362
}

# Gamma 解绑 34 张业务看板（保留 34 统计报表目录外壳）
GAMMA_UNBIND = [25, 26, 27, 28, 29, 30, 31, 32, 33, 35, 36, 37, 38, 39, 40, 41,
                42, 43, 44, 45, 46, 48, 53, 54, 55, 56, 57, 58, 59, 60,
                72, 73, 74, 75]
GAMMA_KEEP = [34]

BASELINE_DS_ACCESS = {(341, 4), (344, 279), (344, 321),
                      (345, 276), (345, 332), (345, 333)}
FINAL_DASH_ROWS_DELTA = 12   # 51 -> 63
FINAL_DS_ACCESS_DELTA = 60   # 6 -> 66

# FAB 表序列巡检/修复范围（SQLAlchemy 对整型主键显式发 nextval，列默认值为空是假象；
# 20261108 裸 SQL 显式 id 写入未推序列 → ab_role_id_seq(344/345) 与
# ab_permission_view_role_id_seq(470/476) 已滞后，ORM/REST 后续写入必撞主键 500）
FAB_SEQ_TABLES = (
    ("ab_role_id_seq", "ab_role"),
    ("ab_view_menu_id_seq", "ab_view_menu"),
    ("ab_permission_view_id_seq", "ab_permission_view"),
    ("ab_permission_view_role_id_seq", "ab_permission_view_role"),
)


# ---------- DB 只读通道 ----------
def connect_ro():
    pw = os.environ.get("PGPASSWORD") or os.environ.get("POSTGRES_PASSWORD") or ""
    conn = psycopg2.connect(host="postgres", port=5432, dbname="superset",
                            user="superset", password=pw)
    conn.set_session(readonly=True, autocommit=True)
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor), conn


def q(cur, sql, args=None):
    cur.execute(sql, args or ())
    return cur.fetchall()


def read_state(cur):
    st = {}
    rows = q(cur, "SELECT id, name FROM ab_role ORDER BY id")
    st["role_id"] = {r["name"]: r["id"] for r in rows}
    st["role_name"] = {r["id"]: r["name"] for r in rows}

    dash = q(cur, "SELECT id, dashboard_title, published FROM dashboards ORDER BY id")
    st["dash_title"] = {d["id"]: d["dashboard_title"] for d in dash}
    st["dash_published"] = {d["id"]: d["published"] for d in dash}

    st["dash_roles"] = {}
    for r in q(cur, "SELECT dashboard_id, role_id FROM dashboard_roles "
                    "ORDER BY dashboard_id, role_id"):
        st["dash_roles"].setdefault(r["dashboard_id"], set()).add(r["role_id"])

    st["dash_ds"] = {}
    for r in q(cur, "SELECT ds.dashboard_id, s.datasource_id, s.datasource_type "
                    "FROM dashboard_slices ds JOIN slices s ON s.id = ds.slice_id"):
        if r["datasource_type"] == "table" and r["datasource_id"]:
            st["dash_ds"].setdefault(r["dashboard_id"], set()).add(r["datasource_id"])

    st["nf_ds"] = {}
    for d in q(cur, "SELECT id, json_metadata FROM dashboards"):
        try:
            meta = json.loads(d["json_metadata"] or "{}")
        except Exception:
            meta = {}
        ids = set()
        for nf in meta.get("native_filter_configuration") or []:
            for tgt in nf.get("targets") or []:
                did = tgt.get("datasetId")
                if did:
                    ids.add(int(did))
        if ids:
            st["nf_ds"][d["id"]] = ids

    st["ds_meta"] = {r["id"]: (r["table_name"], r["schema"], r["perm"])
                     for r in q(cur, "SELECT id, table_name, schema, perm FROM tables")}
    st["vm_names"] = {r["name"] for r in q(cur, "SELECT name FROM ab_view_menu")}

    st["ds_roles"] = {}
    for r in q(cur, "SELECT pvr.role_id AS role_id, vm.name AS vm "
                    "FROM ab_permission_view_role pvr "
                    "JOIN ab_permission_view pv ON pv.id = pvr.permission_view_id "
                    "JOIN ab_permission p ON p.id = pv.permission_id "
                    "JOIN ab_view_menu vm ON vm.id = pv.view_menu_id "
                    "WHERE p.name = 'datasource_access'"):
        m = re.search(r"\(id:(\d+)\)$", r["vm"] or "")
        if not m:
            st.setdefault("unparsed_ds_viewmenus", []).append(r["vm"])
            continue
        st["ds_roles"].setdefault(int(m.group(1)), set()).add(r["role_id"])

    st["members"] = {r["role_id"]: r["n"]
                     for r in q(cur, "SELECT role_id, count(*) AS n FROM ab_user_role "
                                    "GROUP BY role_id")}
    st["role_pv_count"] = {r["role_id"]: r["n"]
                           for r in q(cur, "SELECT pvr.role_id AS role_id, count(*) AS n "
                                          "FROM ab_permission_view_role pvr "
                                          "GROUP BY pvr.role_id")}
    st["counts"] = {
        "ab_role": q(cur, "SELECT count(*) AS n FROM ab_role")[0]["n"],
        "dashboard_roles": q(cur, "SELECT count(*) AS n FROM dashboard_roles")[0]["n"],
        "ab_user_role": q(cur, "SELECT count(*) AS n FROM ab_user_role")[0]["n"],
        "ab_permission_view_role":
            q(cur, "SELECT count(*) AS n FROM ab_permission_view_role")[0]["n"],
        "ds_access": q(cur, "SELECT count(*) AS n FROM ab_permission_view_role pvr "
                            "JOIN ab_permission_view pv ON pv.id = pvr.permission_view_id "
                            "JOIN ab_permission p ON p.id = pv.permission_id "
                            "WHERE p.name = 'datasource_access'")[0]["n"],
    }
    st["fab_seq"] = {}
    for _seq, _tbl in FAB_SEQ_TABLES:
        _row = q(cur, "SELECT last_value, is_called FROM %s" % _seq)[0]
        st["fab_seq"][_seq] = {
            "last_value": _row["last_value"], "is_called": _row["is_called"],
            "max_id": q(cur, "SELECT coalesce(max(id), 0) AS m FROM %s" % _tbl)[0]["m"]}
    return st


def ds_of_dashboards(st, dash_ids):
    out = set()
    for d in dash_ids:
        out |= st["dash_ds"].get(d, set())
        out |= st["nf_ds"].get(d, set())
    return out


# ---------- REST 通道 ----------
class Api(object):
    def __init__(self):
        base = os.environ.get("SUP_BASE", "http://superset-web:8088").rstrip("/")
        # 必须用 Session：csrf_token 端点会把 CSRF secret 种进 session cookie，
        # Flask-WTF 校验要求「header 令牌 + 会话 secret」成对（本批实测缺一报
        # "CSRF token/session token is missing"）
        self.http = requests.Session()
        r = self.http.post(base + "/api/v1/security/login",
                           json={"username": os.environ.get("SUP_ADMIN", "admin"),
                                 "password": os.environ.get("SUP_ADMIN_PWD", ""),
                                 "provider": "db", "refresh": True}, timeout=30)
        r.raise_for_status()
        self.base = base
        self.token = r.json()["access_token"]
        # Superset 写端点要求 X-CSRFToken（本批实测：POST security/roles 豁免，
        # PUT dashboard 400 CSRF missing；生产 grant_access.py 同款方案：
        # GET /api/v1/security/csrf_token/ 取 result 塞 header）
        r2 = self.http.get(base + "/api/v1/security/csrf_token/",
                           headers={"Authorization": "Bearer " + self.token}, timeout=30)
        r2.raise_for_status()
        self.csrf = r2.json()["result"]

    def call(self, method, path, body=None):
        r = None
        for attempt in (1, 2):
            try:
                r = self.http.request(method, self.base + path, json=body,
                                      headers={"Authorization": "Bearer " + self.token,
                                               "X-CSRFToken": self.csrf},
                                      timeout=60)
                break
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(2)
        if r is None or r.status_code >= 300:
            raise RuntimeError("REST %s %s -> %s %s" % (
                method, path, r.status_code if r is not None else "?",
                r.text[:400] if r is not None else ""))
        return r


# ---------- 数据集授权 SQL 通道（20261108 create_roles_20261108.sql 已实证模式） ----------
# 单事务三步幂等 INSERT：均 NOT EXISTS 防重；FAB 表无自增序列，id 用
# coalesce(max(id),0)+row_number() 显式给值（语句级快照，同语句内 max 为写前值）。
GRANT_VM_SQL = """
WITH need(ds_id, vm) AS (
    SELECT DISTINCT unnest(%(ds_ids)s::int[]), unnest(%(vm_names)s::text[])
)
INSERT INTO ab_view_menu (id, name)
SELECT (SELECT coalesce(max(id), 0) FROM ab_view_menu)
       + row_number() OVER (ORDER BY n.vm),
       n.vm
FROM need n
WHERE NOT EXISTS (SELECT 1 FROM ab_view_menu x WHERE x.name = n.vm)
"""

GRANT_PV_SQL = """
WITH need(ds_id, vm) AS (
    SELECT DISTINCT unnest(%(ds_ids)s::int[]), unnest(%(vm_names)s::text[])
)
INSERT INTO ab_permission_view (id, permission_id, view_menu_id)
SELECT (SELECT coalesce(max(id), 0) FROM ab_permission_view)
       + row_number() OVER (ORDER BY n.vm),
       p.id, vm.id
FROM need n
JOIN ab_permission p ON p.name = 'datasource_access'
JOIN ab_view_menu vm ON vm.name = n.vm
WHERE NOT EXISTS (
    SELECT 1 FROM ab_permission_view x
    WHERE x.permission_id = p.id AND x.view_menu_id = vm.id)
"""

GRANT_PVR_SQL = """
WITH need(role_id, vm) AS (
    SELECT DISTINCT unnest(%(role_ids)s::int[]), unnest(%(vm_names2)s::text[])
)
INSERT INTO ab_permission_view_role (id, permission_view_id, role_id)
SELECT (SELECT coalesce(max(id), 0) FROM ab_permission_view_role)
       + row_number() OVER (ORDER BY n.role_id, n.vm),
       pv.id, n.role_id
FROM need n
JOIN ab_view_menu vm ON vm.name = n.vm
JOIN ab_permission p ON p.name = 'datasource_access'
JOIN ab_permission_view pv ON pv.permission_id = p.id AND pv.view_menu_id = vm.id
WHERE NOT EXISTS (
    SELECT 1 FROM ab_permission_view_role x
    WHERE x.permission_view_id = pv.id AND x.role_id = n.role_id)
"""


def connect_rw():
    """可写连接：仅用于数据集授权事务（与只读连接分离，缩小误写面）。"""
    pw = os.environ.get("PGPASSWORD") or os.environ.get("POSTGRES_PASSWORD") or ""
    conn = psycopg2.connect(host="postgres", port=5432, dbname="superset",
                            user="superset", password=pw)
    conn.autocommit = False
    return conn


def grant_ds_access(pairs, ds_perm):
    """单事务幂等授予 (role_id, ds_id) 数据集访问。返回渲染后的三条 SQL 文本（存证）。

    pairs: [(role_id, ds_id)]（全 int）；ds_perm: {ds_id: tables.perm}（非空）。
    任何一步失败整体回滚，不留半态。
    """
    ds_ids = sorted({p[1] for p in pairs})
    role_ids = [r for r, _ in sorted(pairs)]
    params = {"ds_ids": ds_ids,
              "vm_names": [ds_perm[d] for d in ds_ids],
              "role_ids": role_ids,
              "vm_names2": [ds_perm[d] for _, d in sorted(pairs)]}
    conn = connect_rw()
    try:
        with conn.cursor() as rc:
            rc.execute("SELECT id FROM ab_permission WHERE name = 'datasource_access'")
            prow = rc.fetchall()
            if len(prow) != 1:
                raise RuntimeError("ab_permission.datasource_access 行数=%d（应为 1）"
                                   % len(prow))
            texts = []
            for sql in (GRANT_VM_SQL, GRANT_PV_SQL, GRANT_PVR_SQL):
                texts.append(rc.mogrify(sql, params).decode("utf-8"))
                rc.execute(sql, params)
        conn.commit()
        with open(GRANT_SQL_PATH, "w", encoding="utf-8") as f:
            f.write("-- %s apply 数据集授权事务（实际执行原文）\n" % BATCH)
            f.write("BEGIN;\n")
            for t in texts:
                f.write(t.strip("\n") + ";\n")
            f.write("COMMIT;\n")
        return texts
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def repair_sequence(seq, table):
    """把 FAB 序列推到 max(id)（只进不退），防 ORM/REST 写入撞主键。

    健康判据：nextval 预期值 > max(id)（is_called=false 时 nextval 返回 last_value 本身）。
    返回 (修前 last_value, max_id) 表示已修复；None 表示本就健康、未改动。
    """
    conn = connect_rw()
    try:
        with conn.cursor() as rc:
            rc.execute("SELECT last_value, is_called FROM %s" % seq)
            last, called = rc.fetchone()
            rc.execute("SELECT coalesce(max(id), 0) FROM %s" % table)
            mx = rc.fetchone()[0]
            if last + (1 if called else 0) > mx:
                conn.rollback()
                return None
            rc.execute("SELECT setval(%s, %s)", (seq, mx))
        conn.commit()
        return (last, mx)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------- 终态矩阵与现状判定 ----------
def final_dash_roles(new_ids):
    """34 张看板 -> 期望终态角色 id 集合（new_ids: 角色名->id，未知时值为 None 占位）。"""
    out = {}
    for d in GAMMA_UNBIND:
        roles = set()
        for name, dashes, _ in NEW_ROLE_MATRIX:
            if d in dashes:
                roles.add(new_ids.get(name, name))   # 未知新角色用名字占位
        for rid, adds in EXISTING_DASH_ADD.items():
            if d in adds:
                roles.add(rid)
        out[d] = roles
    return out


def final_ds_pairs(new_ids):
    """期望终态 (角色, 数据集) 对集合（不含基线 6 条自动并入）。"""
    pairs = set()
    for name, dashes, exp_ds in NEW_ROLE_MATRIX:
        rid = new_ids.get(name, name)
        for ds_id in exp_ds:
            pairs.add((rid, ds_id))
    for rid, dsset in EXISTING_ROLE_DS.items():
        for ds_id in dsset:
            pairs.add((rid, ds_id))
    return pairs | BASELINE_DS_ACCESS


def _pair_key(p):
    """排序键：新角色 dry-run 以名字占位(str)与真实 id(int) 混存时安全排序。"""
    return (isinstance(p[0], str), p[0], p[1])


def _rid_key(x):
    return (isinstance(x, str), x)


def plan(st, problems):
    """面向终态：现状只允许 原始态/终态/两者混合。返回 (角色创建计划, 看板计划, 数据集计划, new_ids)。"""
    new_ids = {}
    # 1) 新角色存在性：已存在则复用，且必须干净（0 成员、绑定不得越出终态）
    for name, dashes, exp_ds in NEW_ROLE_MATRIX:
        if name in st["role_id"]:
            rid = st["role_id"][name]
            if st["members"].get(rid, 0):
                problems.append("F-ROLE 已存在角色 %s(id=%s) 竟有成员，非本批产物，中止"
                                % (name, rid))
            new_ids[name] = rid
    fin_dash = final_dash_roles(new_ids)
    fin_pairs = final_ds_pairs(new_ids)

    # 2) 34 张看板现状判定
    dash_plan = {}      # dash_id -> (before, after)  仅含需动作者
    for d in GAMMA_UNBIND:
        cur = st["dash_roles"].get(d, set())
        if GAMMA_ID in cur:
            cur = cur - {GAMMA_ID}
            if cur:
                problems.append("F-DRIFT 看板 %s 同时挂 Gamma 与其他角色: %s" % (d, sorted(cur)))
                continue
            dash_plan[d] = ({GAMMA_ID}, set(fin_dash[d]))
        else:
            if cur != fin_dash[d]:
                problems.append("F-DRIFT 看板 %s 非原始非终态: %s != %s"
                                % (d, sorted(cur), sorted(fin_dash[d], key=_rid_key)))
    # 3) 看板 34 保留 Gamma
    if st["dash_roles"].get(GAMMA_KEEP[0], set()) != {GAMMA_ID}:
        problems.append("F-KEEP 看板 %s 应仅绑 Gamma: %s"
                        % (GAMMA_KEEP[0], sorted(st["dash_roles"].get(GAMMA_KEEP[0], set()))))
    # 4) Gamma 不得出现在任何其他看板
    extra_gamma = sorted(d for d, rl in st["dash_roles"].items()
                         if GAMMA_ID in rl and d not in GAMMA_UNBIND + GAMMA_KEEP)
    if extra_gamma:
        problems.append("F-DRIFT Gamma 越界绑定看板: %s" % extra_gamma)
    # 5) 既有 4 角色绑定保留
    for rid, dashes in EXISTING_ROLE_DASH.items():
        miss = [d for d in dashes if rid not in st["dash_roles"].get(d, set())]
        if miss:
            problems.append("F-BEFORE 角色 %s 既有看板绑定缺失: %s" % (rid, miss))
    # 6) 数据集现状判定（合并语义，只增不删）
    ds_plan = {}        # ds_id -> (before, after)  仅含需动作者
    need_pairs = fin_pairs
    cur_pairs = set()
    for ds_id, roles in st["ds_roles"].items():
        for rid in roles:
            cur_pairs.add((rid, ds_id))
    drift_pairs = cur_pairs - need_pairs
    if drift_pairs:
        problems.append("F-DRIFT datasource_access 存在终态外条目: %s" % sorted(drift_pairs))
    for rid, ds_id in sorted(need_pairs - cur_pairs, key=_pair_key):
        before = set(st["ds_roles"].get(ds_id, set()))
        item = ds_plan.setdefault(ds_id, (before, set(before)))
        item[1].add(rid)
        if ds_id not in st["ds_meta"]:
            problems.append("F-DS 数据集 %s 不存在于 tables" % ds_id)
    # 6b) view_menu 名可用性：授权用 tables.perm。基线 6 条必须已有同名 view_menu
    #     （实证 tables.perm 与 datasource_access view_menu 命名一致后，其余缺行才由 SQL 自建）
    for rid, ds_id in sorted(BASELINE_DS_ACCESS):
        perm = st["ds_meta"].get(ds_id, (None, None, None))[2]
        if not perm:
            problems.append("F-PERM 基线数据集 %s tables.perm 为空" % ds_id)
        elif perm not in st["vm_names"]:
            problems.append("F-PERM 基线对 (%s,%s) view_menu 缺失: %r"
                            % (rid, ds_id, perm))
    for ds_id in sorted({d for _, d in need_pairs} - {d for _, d in BASELINE_DS_ACCESS}):
        if not st["ds_meta"].get(ds_id, (None, None, None))[2]:
            problems.append("F-PERM 数据集 %s tables.perm 为空，无法授权" % ds_id)
    # 7) 现算数据集与硬编码期望交叉核对（防矩阵誊写误差）
    for name, dashes, exp in NEW_ROLE_MATRIX:
        rid = new_ids.get(name, name)
        calc = ds_of_dashboards(st, dashes)
        unknown = calc - set(st["ds_meta"])
        if unknown:
            problems.append("F-CALC %s 现算数据集不存在: %s" % (name, sorted(unknown)))
        if calc != exp:
            problems.append("F-XCHECK %s 现算 %s != 任务书期望 %s"
                            % (name, sorted(calc), sorted(exp)))
        for ds in calc:
            if (rid, ds) not in fin_pairs:
                problems.append("F-CALC %s 现算 %s 未进终态集" % (name, ds))
    for rid in EXISTING_ROLE_DS:
        calc = ds_of_dashboards(st, EXISTING_ROLE_DASH[rid] + EXISTING_DASH_ADD.get(rid, []))
        if calc != EXISTING_ROLE_DS[rid]:
            problems.append("F-XCHECK 既有角色 %s 现算 %s != 期望 %s"
                            % (rid, sorted(calc), sorted(EXISTING_ROLE_DS[rid])))
    # 8) 看板/数据集存在性与发布状态
    for d in GAMMA_UNBIND + GAMMA_KEEP + [2] + list(range(47, 53)) + list(range(61, 71)):
        if d not in st["dash_title"]:
            problems.append("F-EXIST 看板 %s 不存在" % d)
        elif d in GAMMA_UNBIND and not st["dash_published"].get(d):
            problems.append("F-PUB 看板 %s 未发布" % d)
    return dash_plan, ds_plan, new_ids


def role_label(x, st, new_ids):
    if isinstance(x, str):
        return x if x.startswith("NEW:") else "NEW:" + x
    return st["role_name"].get(x, x)


def build_report(st, mode, dash_plan, ds_plan, new_ids, extra=None):
    def labels(rids):
        return sorted("NEW:" + r if isinstance(r, str)
                      else st["role_name"].get(r, "id:%d" % r)
                      for r in rids)
    rep = {
        "batch": BATCH,
        "stage": "stage1-apply",
        "mode": mode,
        "time_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "new_roles": [{"name": n, "id": new_ids.get(n), "dashboards": d,
                       "datasets": sorted(s)} for n, d, s in NEW_ROLE_MATRIX],
        "existing_dash_add": {str(k): v for k, v in EXISTING_DASH_ADD.items()},
        "gamma_unbind": GAMMA_UNBIND,
        "gamma_keep": GAMMA_KEEP,
        "dashboards": [
            {"id": d, "title": st["dash_title"].get(d),
             "before_roles": labels(dash_plan[d][0]),
             "after_roles": labels(dash_plan[d][1]),
             "after_role_ids": sorted(dash_plan[d][1], key=_rid_key)}
            for d in sorted(dash_plan)],
        "datasets": [
            {"id": ds, "table_name": st["ds_meta"].get(ds, ("?",))[0],
             "before_roles": labels(ds_plan[ds][0]),
             "after_roles": labels(ds_plan[ds][1]),
             "after_role_ids": sorted(ds_plan[ds][1], key=_rid_key)}
            for ds in sorted(ds_plan)],
        "baseline_counts": st["counts"],
    }
    if extra:
        rep.update(extra)
    return rep


def final_verify(st_before, st, new_ids):
    """apply 后全量读回校验（按完整矩阵期望，不依赖本次执行了哪些步骤）。"""
    problems = []
    checks = []

    def add(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": str(detail)})
        if not ok:
            problems.append("%s %s" % (name, detail))

    fin_dash = final_dash_roles(new_ids)
    fin_pairs = final_ds_pairs(new_ids)

    gamma_bound = sorted(d for d, rl in st["dash_roles"].items() if GAMMA_ID in rl)
    add("gamma_only_keeps_34", gamma_bound == GAMMA_KEEP, gamma_bound)

    bad = []
    for d in GAMMA_UNBIND:
        now = st["dash_roles"].get(d, set())
        if now != fin_dash[d]:
            bad.append({"id": d, "expect": sorted(fin_dash[d]), "got": sorted(now)})
    add("dashboards_34_final", not bad, json.dumps(bad, ensure_ascii=False))

    for rid, dashes in EXISTING_ROLE_DASH.items():
        miss = [d for d in dashes if rid not in st["dash_roles"].get(d, set())]
        add("existing_role_%s_kept" % rid, not miss, miss)

    cur_pairs = set()
    for ds_id, roles in st["ds_roles"].items():
        for rid in roles:
            cur_pairs.add((rid, ds_id))
    add("ds_access_pairs_final", cur_pairs == fin_pairs,
        "missing=%s extra=%s" % (sorted(fin_pairs - cur_pairs),
                                 sorted(cur_pairs - fin_pairs)))

    bad_roles = []
    for name, _, _ in NEW_ROLE_MATRIX:
        rid = new_ids.get(name)
        if rid is None or st["role_id"].get(name) != rid:
            bad_roles.append("%s id缺失" % name)
        elif st["members"].get(rid, 0):
            bad_roles.append("%s 有成员 %s" % (name, st["members"].get(rid)))
    add("new_roles_clean", not bad_roles, bad_roles)

    add("role341_member", st["members"].get(ROLE_341, 0) == 1,
        st["members"].get(ROLE_341))
    add("role343_member", st["members"].get(ROLE_343, 0) == 1,
        st["members"].get(ROLE_343))
    add("user_roles_untouched",
        st["counts"]["ab_user_role"] == st_before["counts"]["ab_user_role"],
        "%s->%s" % (st_before["counts"]["ab_user_role"], st["counts"]["ab_user_role"]))
    # 非数据集类 pvr 行数不变（新增 60 条 datasource_access 本身就是 pvr 行）
    nds_before = st_before["counts"]["ab_permission_view_role"] - st_before["counts"]["ds_access"]
    nds_after = st["counts"]["ab_permission_view_role"] - st["counts"]["ds_access"]
    add("non_ds_perm_rows_unchanged", nds_before == nds_after, "%s->%s" % (nds_before, nds_after))
    add("gamma_perm_count_unchanged",
        st["role_pv_count"].get(GAMMA_ID, 0) == st_before["role_pv_count"].get(GAMMA_ID, 0),
        "%s->%s" % (st_before["role_pv_count"].get(GAMMA_ID, 0),
                    st["role_pv_count"].get(GAMMA_ID, 0)))
    add("dashboard_roles_rows_final",
        st["counts"]["dashboard_roles"] == 63, st["counts"]["dashboard_roles"])
    add("ds_access_rows_final",
        st["counts"]["ds_access"] == 6 + FINAL_DS_ACCESS_DELTA, st["counts"]["ds_access"])
    add("ab_role_count_final",
        st["counts"]["ab_role"] == 351, st["counts"]["ab_role"])
    bad_seq = []
    for seq, info in sorted(st["fab_seq"].items()):
        next_would = info["last_value"] + (1 if info["is_called"] else 0)
        if next_would <= info["max_id"]:
            bad_seq.append({"seq": seq, "next_would": next_would,
                            "max_id": info["max_id"]})
    add("fab_sequences_healthy", not bad_seq, json.dumps(bad_seq, ensure_ascii=False))
    return {"checks": checks, "problems": problems,
            "counts_after": st["counts"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真正写入（默认 dry-run）")
    args = ap.parse_args()
    mode = "apply" if args.apply else "dry-run"

    cur, conn = connect_ro()
    st = read_state(cur)
    problems = []
    dash_plan, ds_plan, new_ids = plan(st, problems)

    if problems:
        rep = build_report(st, mode, dash_plan, ds_plan, new_ids, {"problems": problems})
        with open(PLAN_PATH, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
        print("ABORT problems=%d report=%s" % (len(problems), PLAN_PATH))
        for p in problems:
            print("  PROBLEM:", p)
        sys.exit(1)

    n_role_new = sum(1 for n, _, _ in NEW_ROLE_MATRIX if n not in new_ids)
    print("%s_STATE dashboards_todo=%d ds_puts=%d roles_new=%d (of 7)"
          % (mode.upper(), len(dash_plan), len(ds_plan), n_role_new))

    rep = build_report(st, mode, dash_plan, ds_plan, new_ids)
    if not args.apply:
        with open(PLAN_PATH, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
        print("DRYRUN_OK plan=%s" % PLAN_PATH)
        sys.exit(0)

    # ---------- apply ----------
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
        if dash_plan or ds_plan or n_role_new:
            api = Api()
        else:
            api = None

        # 0) 建角色前置序列修复：ab_role_id_seq 滞后于 max(id) 时推齐（只进不退），
        #    否则 REST 建角色走 nextval 撞主键 500（本批实测；20261108 遗留缺陷）
        seq_repairs = []
        rr = repair_sequence("ab_role_id_seq", "ab_role")
        if rr:
            seq_repairs.append({"seq": "ab_role_id_seq",
                                "before_last_value": rr[0], "set_to": rr[1]})
            print("SEQ_REPAIR ab_role_id_seq last=%s -> setval(%s)" % (rr[0], rr[1]))
        rep["sequence_repairs"] = seq_repairs
        with open(CHANGES_PATH, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)

        # 1) 建角色（幂等：已存在则复用）
        for name, dashes, exp in NEW_ROLE_MATRIX:
            if name in new_ids:
                print("REUSE role %s id=%s" % (name, new_ids[name]))
                continue
            api.call("POST", "/api/v1/security/roles/", {"name": name})
            rows = q(cur, "SELECT id FROM ab_role WHERE name = %s", (name,))
            if not rows:
                raise RuntimeError("role create verify fail: %s" % name)
            new_ids[name] = rows[0]["id"]
            st_now = read_state(cur)
            if st_now["members"].get(new_ids[name], 0) \
                    or st_now["role_pv_count"].get(new_ids[name], 0):
                raise RuntimeError("new role %s not clean" % name)
            print("CREATE role %s id=%s" % (name, new_ids[name]))
            # 角色已可解析为真实 id：重算终态并落盘（崩溃一致）
            snap = read_state(cur)
            sub_problems = []
            dash_plan, ds_plan, _ = plan(snap, sub_problems)
            if sub_problems:
                raise RuntimeError("post-create plan problems: %s" % sub_problems)
            rep = build_report(st, "apply", dash_plan, ds_plan, new_ids,
                               {"phase": "planned", "executed": {"dashboards": [], "datasets": []}})
            rep["sequence_repairs"] = seq_repairs
            with open(CHANGES_PATH, "w", encoding="utf-8") as f:
                json.dump(rep, f, ensure_ascii=False, indent=1)

        # 终态重算（真实角色 id）
        snap = read_state(cur)
        sub_problems = []
        dash_plan, ds_plan, _ = plan(snap, sub_problems)
        if sub_problems:
            raise RuntimeError("pre-write plan problems: %s" % sub_problems)
        rep = build_report(st, "apply", dash_plan, ds_plan, new_ids,
                           {"phase": "planned", "executed": {"dashboards": [], "datasets": []}})
        rep["sequence_repairs"] = seq_repairs
        with open(CHANGES_PATH, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)

        # 2) 数据集授权（先授数据集后绑看板：中途失败不产生越权中间态）
        #    SQL 直写单事务（REST dataset 端点无 roles 字段，已证伪弃用）
        executed = rep["executed"]
        pairs = []
        for ds_id in sorted(ds_plan):
            before, after = ds_plan[ds_id]
            for rid in sorted(after - before):
                if not isinstance(rid, int):
                    raise RuntimeError("数据集授权对角色 id 未解析: %r" % (rid,))
                pairs.append((rid, ds_id))
        if pairs:
            ds_perm = {d: st["ds_meta"][d][2] for d in {p[1] for p in pairs}}
            grant_ds_access(pairs, ds_perm)
            # 显式 id 写入后推齐 vm/pv/pvr 三序列（只进不退），防后续 ORM 撞主键
            for _seq, _tbl in FAB_SEQ_TABLES[1:]:
                rr2 = repair_sequence(_seq, _tbl)
                if rr2:
                    seq_repairs.append({"seq": _seq,
                                        "before_last_value": rr2[0], "set_to": rr2[1]})
                    print("SEQ_REPAIR %s last=%s -> setval(%s)"
                          % (_seq, rr2[0], rr2[1]))
            rep["sequence_repairs"] = seq_repairs
            now_st = read_state(cur)
            for ds_id in sorted(ds_plan):
                before, after = ds_plan[ds_id]
                now = set(now_st["ds_roles"].get(ds_id, set()))
                if now != after:
                    raise RuntimeError("ds %s verify fail: expect %s got %s"
                                       % (ds_id, sorted(after), sorted(now)))
                executed["datasets"].append(ds_id)
            rep["executed"] = executed
            rep["grant_sql_trace"] = GRANT_SQL_PATH
            with open(CHANGES_PATH, "w", encoding="utf-8") as f:
                json.dump(rep, f, ensure_ascii=False, indent=1)
            print("DS_GRANT pairs=%d datasets=%d trace=%s"
                  % (len(pairs), len({p[1] for p in pairs}), GRANT_SQL_PATH))

        # 3) 看板绑定（Gamma 解绑 + 新角色接管）
        for d in sorted(dash_plan):
            before, after = dash_plan[d]
            if before == after:
                continue
            api.call("PUT", "/api/v1/dashboard/%d" % d, {"roles": sorted(after)})
            now = set(read_state(cur)["dash_roles"].get(d, set()))
            if now != set(after):
                raise RuntimeError("dashboard %s verify fail: expect %s got %s"
                                   % (d, sorted(after), sorted(now)))
            executed["dashboards"].append(d)
            rep["executed"] = executed
            with open(CHANGES_PATH, "w", encoding="utf-8") as f:
                json.dump(rep, f, ensure_ascii=False, indent=1)
            print("DASH_PUT %d roles=%s" % (d, sorted(after)))

        # 4) 终态校验
        verify = final_verify(st, read_state(cur), new_ids)
        rep["verify"] = verify
        rep["phase"] = "applied" if not verify["problems"] else "applied-with-problems"
        with open(CHANGES_PATH, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
        if verify["problems"]:
            print("APPLY_DONE_WITH_VERIFY_PROBLEMS %s" % CHANGES_PATH)
            for p in verify["problems"]:
                print("  PROBLEM:", p)
            sys.exit(2)
        print("APPLY_OK %s" % CHANGES_PATH)
    finally:
        try:
            fcntl.flock(lockfh, fcntl.LOCK_UN)
        finally:
            lockfh.close()
        conn.close()


if __name__ == "__main__":
    main()
