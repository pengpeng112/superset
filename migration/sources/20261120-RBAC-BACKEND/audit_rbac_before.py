# -*- coding: utf-8 -*-
"""20261120-RBAC-BACKEND 阶段0：全量权限只读审计（不写任何数据）。

在 superset-worker 容器内运行：
  docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" superset-worker \
      /app/.venv/bin/python /app/superset_home/scripts/migration_20261120/audit_rbac_before.py

输出：/tmp/rbac_state_full.json（容器内），随后 docker cp 到宿主迁移私有区。
退出码 0=成功；只读 SELECT，绝不 INSERT/UPDATE/DELETE。
"""
import json
import os
import sys

import psycopg2
import psycopg2.extras

OUT = "/tmp/rbac_state_full.json"
BUILTIN = ("Gamma", "Public", "Alpha", "sql_lab", "Admin")
DANGEROUS_PERMS = [
    "all_datasource_access", "all_database_access", "all_query_access",
    "can_sqllab", "can_execute_sql_query", "can_sql_json", "can_csv",
    "can_export", "can_read_chart", "can_write_dashboard", "can_write_chart",
]

conn = psycopg2.connect(
    host="postgres", port=5432, dbname="superset",
    user="superset", password=os.environ["PGPASSWORD"] or os.environ.get("POSTGRES_PASSWORD", ""),
)
conn.set_session(readonly=True, autocommit=True)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def q(sql, args=None):
    cur.execute(sql, args or ())
    return cur.fetchall()


state = {}

# ---------- 1. 全部看板：published / roles / slices / 数据集 / 原生筛选字典 ----------
dashs = q("SELECT id, dashboard_title, slug, published, json_metadata FROM dashboards ORDER BY id")
slices_by_dash = {}
for row in q("""
    SELECT ds.dashboard_id, s.id AS slice_id, s.slice_name, s.datasource_id, s.datasource_type
    FROM dashboard_slices ds JOIN slices s ON s.id = ds.slice_id ORDER BY ds.dashboard_id, s.id
"""):
    slices_by_dash.setdefault(row["dashboard_id"], []).append(
        {k: row[k] for k in ("slice_id", "slice_name", "datasource_id", "datasource_type")}
    )
roles_by_dash = {}
for row in q("""
    SELECT dr.dashboard_id, r.id AS role_id, r.name AS role_name
    FROM dashboard_roles dr JOIN ab_role r ON r.id = dr.role_id ORDER BY dr.dashboard_id, dr.role_id
"""):
    roles_by_dash.setdefault(row["dashboard_id"], []).append(
        {"role_id": row["role_id"], "role_name": row["role_name"]}
    )

dash_list = []
for d in dashs:
    meta = {}
    try:
        meta = json.loads(d["json_metadata"] or "{}")
    except Exception:
        meta = {}
    nf_ds = []
    for nf in meta.get("native_filter_configuration") or []:
        for tgt in nf.get("targets") or []:
            did = tgt.get("datasetId")
            if did and did not in nf_ds:
                nf_ds.append(did)
    dash_list.append({
        "id": d["id"], "title": d["dashboard_title"], "slug": d["slug"],
        "published": d["published"],
        "roles": roles_by_dash.get(d["id"], []),
        "slices": slices_by_dash.get(d["id"], []),
        "native_filter_dataset_ids": nf_ds,
    })
state["dashboards"] = dash_list
state["dashboard_count"] = len(dash_list)
state["published_count"] = sum(1 for d in dash_list if d["published"])

# ---------- 2. 全部角色：成员数 + permission_view 清单 ----------
roles = q("SELECT id, name FROM ab_role ORDER BY id")
members = q("""
    SELECT r.id AS role_id, count(u.id) AS n, count(*) FILTER (WHERE u.active) AS active_n
    FROM ab_role r LEFT JOIN ab_user_role ur ON ur.role_id = r.id
    LEFT JOIN ab_user u ON u.id = ur.user_id GROUP BY r.id
""")
member_map = {m["role_id"]: {"n": m["n"], "active_n": m["active_n"]} for m in members}
pv_rows = q("""
    SELECT pvr.role_id, p.name AS perm, vm.name AS view_menu
    FROM ab_permission_view_role pvr
    JOIN ab_permission_view pv ON pv.id = pvr.permission_view_id
    JOIN ab_permission p ON p.id = pv.permission_id
    JOIN ab_view_menu vm ON vm.id = pv.view_menu_id
    ORDER BY pvr.role_id, p.name, vm.name
""")
pv_map = {}
for r in pv_rows:
    pv_map.setdefault(r["role_id"], []).append(f'{r["perm"]} on {r["view_menu"]}')

role_list = []
for r in roles:
    role_list.append({
        "id": r["id"], "name": r["name"],
        "members": member_map.get(r["id"], {}).get("n", 0),
        "active_members": member_map.get(r["id"], {}).get("active_n", 0),
        "permission_views": pv_map.get(r["id"], []),
    })
state["roles"] = role_list
state["role_count"] = len(role_list)

# ---------- 3. 内置角色高危权限核查 + 成员名单 ----------
builtin_detail = {}
for b in BUILTIN:
    rd = next((x for x in role_list if x["name"] == b), None)
    if not rd:
        builtin_detail[b] = {"exists": False}
        continue
    pvs = rd["permission_views"]
    hits = [p for p in DANGEROUS_PERMS if any(x.startswith(p + " ") for x in pvs)]
    user_rows = q("""
        SELECT u.username, u.active FROM ab_user_role ur
        JOIN ab_user u ON u.id = ur.user_id WHERE ur.role_id = %s ORDER BY u.username
    """, (rd["id"],))
    users = [{"username": x["username"], "active": x["active"]} for x in user_rows]
    builtin_detail[b] = {
        "exists": True, "id": rd["id"], "members": rd["members"],
        "active_members": rd["active_members"],
        "permission_count": len(pvs), "permission_views": pvs,
        "dangerous_perm_hits": hits,
        "member_usernames": users,
    }
state["builtin_roles"] = builtin_detail

# Gamma 绑定的看板（大锅饭现状）
gamma = builtin_detail.get("Gamma", {})
gamma_id = gamma.get("id")
state["gamma_bound_dashboards"] = [
    {"id": d["id"], "title": d["title"], "published": d["published"]}
    for d in dash_list
    if gamma_id and any(x["role_id"] == gamma_id for x in d["roles"])
]

# ---------- 4. 数据集清单（供阶段1映射） ----------
state["datasets"] = [
    {"id": r["id"], "table_name": r["table_name"], "schema": r["schema"], "db_id": r["database_id"]}
    for r in q("SELECT id, table_name, schema, database_id FROM tables ORDER BY id")
]
state["dataset_count"] = len(state["datasets"])

# ---------- 5. 科室角色在职人数（脱敏统计） ----------
dept_roles = []
for r in role_list:
    if r["name"].startswith("科室_") or r["name"].startswith("role_"):
        dept_roles.append({
            "role_id": r["id"], "role_name": r["name"],
            "active_members": r["active_members"], "members": r["members"],
        })
dept_roles.sort(key=lambda x: -x["active_members"])
state["dept_roles"] = dept_roles

# ---------- 6. 全局计数 ----------
state["counts"] = {
    "ab_user_role": q("SELECT count(*) AS n FROM ab_user_role")[0]["n"],
    "dashboard_roles": q("SELECT count(*) AS n FROM dashboard_roles")[0]["n"],
    "ab_role": q("SELECT count(*) AS n FROM ab_role")[0]["n"],
    "rls_filters": q("SELECT count(*) AS n FROM row_level_security_filters")[0]["n"],
    "users_total": q("SELECT count(*) AS n FROM ab_user")[0]["n"],
    "users_active": q("SELECT count(*) AS n FROM ab_user WHERE active")[0]["n"],
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False, indent=1)
print("AUDIT_OK", OUT, "roles=%d dashboards=%d" % (state["role_count"], state["dashboard_count"]))
sys.exit(0)
