# -*- coding: utf-8 -*-
"""20261121-RBAC-FRONTEND-POLISH：生成冻结快照 20261121-RBAC-FRONTEND-POLISH-SHA256.json。"""
import hashlib
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FREEZE_DIR = r"F:\python\superset\migration\冻结快照"

FILES = [
    # ---- 批目录：备份与生产导出 ----
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/phase0_backup_and_export.py", None),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/before-assets/home-ui.js", "写前 h17"),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/before-assets/report-ui.js", "写前 f15"),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/before-assets/roles-zh.js", "写前 20261009d"),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/before-assets/nginx.conf", "写前版本串"),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/before-assets/warmup_templates.json", "写前 46 条"),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/evidence/catalog_markdown_raw.json", "25-31,33,34 目录生产导出（CATALOG_REPORTS 依据）"),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/evidence/role_dashboard_bindings.json", "角色→看板绑定（DASH_ROLE_HINT 依据）"),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/evidence/rbac_roles.json", "11 角色清单"),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/evidence/dash_72_75_metadata.json", "72/75 写前元数据"),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/evidence/charts_378_393_396_params.json", "378/393-396 写前 params"),
    # ---- 阶段3：BI 元数据修正 ----
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/phase3_bi_meta.py", "REST 修正（幂等+回读断言）"),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/evidence/phase3_bi_meta_result.json", "全部 OK"),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/capture_warmup_7275.py", "CDP 重录 72/75"),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/evidence/warmup_templates.json", "47 条终版（三端一致）"),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/evidence/phase3b_result.json", "72 图表显式窗 19/19 OK"),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/verify_single_window.py", "Chrome 单窗深页补测"),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/verify_c87_spot.py", "C87 最小抽测"),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/evidence/run_warmup_output.txt", "实跑 47/47 ok"),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/evidence/health_check_output.txt", "18/18 全绿"),
    # ---- 阶段4：部署与验收 ----
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/deploy_rbac_frontend.py", "部署（inode 47580611 保持）"),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/verify_rbac_frontend_polish.py", "多角色双浏览器验收"),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/evidence/iab_acceptance.json", "验收结果 52/52（IAB+Chrome 单窗+C87 抽测）"),
    # ---- 生产对齐与收尾 ----
    ("offline-bundle/custom/home-ui.js", "h18 千人千面"),
    ("offline-bundle/custom/report-ui.js", "f16 角色点名+投屏修复"),
    ("offline-bundle/custom/roles-zh.js", "d2 管辖说明"),
    ("offline-bundle/nginx.conf", "三版本串"),
    ("offline-bundle/scripts/superset_cache_warmup.py", "--roll-month 跨月机制"),
    ("offline-bundle/scripts/warmup_templates.json", "47 条"),
    ("offline-bundle/PRODUCTION-MANIFEST-20261121.json", "全量对齐"),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/build_manifest21.py", None),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/freeze_snapshot21.py", None),
    ("migration/sources/20261121-RBAC-FRONTEND-POLISH/最终报告.md", None),
]


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    entries = []
    for rel, note in FILES:
        p = os.path.join(r"F:\python\superset", rel)
        if not os.path.exists(p):
            entries.append({"file": rel, "missing": True, "note": note or ""})
            continue
        entries.append({"file": rel, "bytes": os.path.getsize(p), "sha256": sha256_file(p), "note": note or ""})
    snap = {
        "batch": "20261121-RBAC-FRONTEND-POLISH",
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": "前端千人千面权限感知与细节收官：验收 52/52 全绿（IAB 首页矩阵 + Chrome 单窗深页 + C87 抽测），warmup 两轮 47/47，体检 18/18；home-ui h17→h18（allowedIds 白名单单飞 + CATALOG_REPORTS 生产导出静态目录 + 五大视图裁剪 + 零权限引导卡）、report-ui f15→f16（DASH_ROLE_HINT 全量角色点名 + 投屏标题根因修复 + 42 双表 456/368px）、roles-zh 20261009d→20261121d2（11 角色管辖说明）；BI 72 默认窗推进 2026-10-01:2026-11-01、75 KPI 393-395 副标题去硬编码、378 高度 14→44 格；warmup 46→47 条 + --roll-month；Chrome+C87×双分辨率×003158/admin 多场景验收；inode 47580611 保持、体检 18/18",
        "production_changes": [
            "/home/superset/custom/home-ui.js：20261119h17 → 20261121h18",
            "/home/superset/custom/report-ui.js：20261119f15 → 20261121f16",
            "/home/superset/custom/roles-zh.js：20261009d → 20261121d2",
            "/home/superset/nginx.conf：三版本串更新（inode 47580611 保持，/tmp 中转 + cp 原地覆写）",
            "dashboards.72：json_metadata 原生筛选默认窗 2026-09-01:2026-10-01 → 2026-10-01:2026-11-01",
            "dashboards.72：position_json 图表 378 meta.height 14→44（112px→352px）",
            "slices.393/394/395：params.subheader『2026-10 全院合计』→『选定期间全院合计』",
            "/home/superset/superset_home/scripts/superset_cache_warmup.py：新增 --roll-month OLD NEW",
            "/home/superset/superset_home/scripts/warmup_templates.json：46→47 条（重录 72 新窗 + 补 75 filter_time）",
        ],
        "rollback": "静态回退：before-assets/ 五文件按 nginx.conf + custom/ + warmup 对应路径回传并 reload（nginx.conf 仍走 /tmp 中转 + cp 保 inode）；BI 元数据回退：phase3_bi_meta.py 中 OLD_WIN/原值反向 PUT（写前值见 evidence/dash_72_75_metadata.json 与 charts_378_393_396_params.json）；人员赋权回退：superset_rbac_manage.py revoke-user",
        "files": entries,
    }
    out = os.path.join(FREEZE_DIR, "20261121-RBAC-FRONTEND-POLISH-SHA256.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
    print("saved", out)
    miss = [e for e in entries if e.get("missing")]
    print("missing:", miss if miss else "无")


if __name__ == "__main__":
    main()
