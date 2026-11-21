# -*- coding: utf-8 -*-
"""20261121-RBAC-FRONTEND-POLISH 阶段0：写前备份 + 生产数据只读导出。

1) 服务器私有备份区 /home/superset/migration-private/20261121-RBAC-FRONTEND-POLISH/before/ 备份：
   nginx.conf、custom/{home-ui.js,report-ui.js,roles-zh.js}、warmup_templates.json；
2) 只读导出（PG 容器 psql -tA json_agg，零写库）：
   a. 看板 25-31,33 的 position_json（目录 Markdown，CATALOG_REPORTS 固化依据）
   b. 看板 34 的 position_json（总目录与其他专题）
   c. 看板 72/75 元数据（json_metadata：默认筛选）+ slices 378,393-396 params
   e. dashboard_roles 全量角色到看板绑定（DASH_ROLE_HINT 反向核对）
   f. 报表授权_ 角色与 人工冻结 角色 id/name 清单
产物全部落本地 before-assets 与 evidence。
凭据环境变量注入（JB_*/TGT_*），不落盘。
"""
import json
import os
import sys

sys.path.insert(0, r"F:\python\superset\migration\tools")
import remote_exec  # noqa: E402
from remote_exec import run  # noqa: E402

BATCH = r"F:\python\superset\migration\sources\20261121-RBAC-FRONTEND-POLISH"
BEFORE = os.path.join(BATCH, "before-assets")
EVID = os.path.join(BATCH, "evidence")
RMT_BEFORE = "/home/superset/migration-private/20261121-RBAC-FRONTEND-POLISH/before"


def get(tgt, remote, local):
    """exec + base64 下载（目标机 sftp 不可用）。"""
    import base64
    rc, out, err = run(tgt, "base64 -w0 %s" % remote, timeout=300)
    assert rc == 0, "read %s failed: %s %s" % (remote, out[-200:], err[-200:])
    with open(local, "wb") as f:
        f.write(base64.b64decode(out.strip()))
    print("  got %s -> %s" % (remote, local))


def psql(tgt, sql):
    """PG 容器只读查询，返回 -tA 文本。"""
    rc, out, err = run(
        tgt,
        'docker exec -e PGPASSWORD="$(grep -E \'^POSTGRES_PASSWORD=\' /home/superset/.env | head -1 | cut -d= -f2-)" '
        'superset-postgres psql -U superset -d superset -tA -c %s' % json.dumps(sql, ensure_ascii=False),
        timeout=300,
    )
    assert rc == 0, "psql failed rc=%d err=%s" % (rc, err[-500:])
    return out


def main():
    os.makedirs(BEFORE, exist_ok=True)
    os.makedirs(EVID, exist_ok=True)
    jb, tgt = remote_exec.connect()
    try:
        print("== step1: server-side backup")
        rc, out, err = run(tgt, (
            "mkdir -p %s && "
            "cp -a /home/superset/nginx.conf %s/nginx.conf && "
            "cp -a /home/superset/custom/home-ui.js %s/home-ui.js && "
            "cp -a /home/superset/custom/report-ui.js %s/report-ui.js && "
            "cp -a /home/superset/custom/roles-zh.js %s/roles-zh.js && "
            "cp -a /home/superset/superset_home/scripts/warmup_templates.json %s/warmup_templates.json && "
            "sha256sum %s/*"
        ) % tuple([RMT_BEFORE] * 7), timeout=300)
        assert rc == 0, out + err
        print(out.strip())

        print("== step2: pull backups to local before-assets")
        for name in ["nginx.conf", "home-ui.js", "report-ui.js", "roles-zh.js", "warmup_templates.json"]:
            get(tgt, "%s/%s" % (RMT_BEFORE, name), os.path.join(BEFORE, name))

        print("== step3: export catalogs 25-31,33,34 position_json")
        rows = psql(tgt, (
            "SELECT coalesce(json_agg(t),'[]') FROM ("
            "SELECT id, dashboard_title, position_json FROM dashboards "
            "WHERE id IN (25,26,27,28,29,30,31,33,34) ORDER BY id) t"
        ))
        arr = json.loads(rows.strip() or "[]")
        catalogs = {int(x["id"]): {"title": x["dashboard_title"], "position_json": x["position_json"]} for x in arr}
        with open(os.path.join(EVID, "catalogs_25_34_position.json"), "w", encoding="utf-8") as f:
            json.dump(catalogs, f, ensure_ascii=False, indent=1)
        print("  catalogs exported: %s" % sorted(catalogs.keys()))

        print("== step4: export 72/75 metadata + charts 378, 393-396")
        rows = psql(tgt, (
            "SELECT coalesce(json_agg(t),'[]') FROM ("
            "SELECT id, dashboard_title, json_metadata, position_json FROM dashboards "
            "WHERE id IN (72,75) ORDER BY id) t"
        ))
        arr = json.loads(rows.strip() or "[]")
        bi = {int(x["id"]): {"title": x["dashboard_title"], "json_metadata": x["json_metadata"], "position_json": x["position_json"]} for x in arr}
        with open(os.path.join(EVID, "dash_72_75_metadata.json"), "w", encoding="utf-8") as f:
            json.dump(bi, f, ensure_ascii=False, indent=1)
        rows = psql(tgt, (
            "SELECT coalesce(json_agg(t),'[]') FROM ("
            "SELECT id, slice_name, params FROM slices "
            "WHERE id IN (378, 393, 394, 395, 396) ORDER BY id) t"
        ))
        arr = json.loads(rows.strip() or "[]")
        charts = {int(x["id"]): {"slice_name": x["slice_name"], "params": x["params"]} for x in arr}
        with open(os.path.join(EVID, "charts_378_393_396_params.json"), "w", encoding="utf-8") as f:
            json.dump(charts, f, ensure_ascii=False, indent=1)
        print("  charts exported: %s" % sorted(charts.keys()))

        print("== step5: export role->dashboard bindings + role list")
        rows = psql(tgt, (
            "SELECT coalesce(json_agg(t),'[]') FROM ("
            "SELECT r.name AS role, json_agg(d.id ORDER BY d.id) AS dash_ids "
            "FROM dashboards d JOIN dashboard_roles dr ON dr.dashboard_id = d.id "
            "JOIN ab_role r ON r.id = dr.role_id "
            "GROUP BY r.name ORDER BY r.name) t"
        ))
        arr = json.loads(rows.strip() or "[]")
        bindings = {x["role"]: x["dash_ids"] for x in arr}
        with open(os.path.join(EVID, "role_dashboard_bindings.json"), "w", encoding="utf-8") as f:
            json.dump(bindings, f, ensure_ascii=False, indent=1)
        rows = psql(tgt, (
            "SELECT coalesce(json_agg(t),'[]') FROM ("
            "SELECT id, name FROM ab_role WHERE name LIKE '报表授权_%' OR name = '人工冻结' ORDER BY id) t"
        ))
        arr = json.loads(rows.strip() or "[]")
        roles = {int(x["id"]): x["name"] for x in arr}
        with open(os.path.join(EVID, "rbac_roles.json"), "w", encoding="utf-8") as f:
            json.dump(roles, f, ensure_ascii=False, indent=1)
        print("  roles: %s" % roles)
        print("PHASE0 DONE")
    finally:
        tgt.close()
        jb.close()


if __name__ == "__main__":
    main()
