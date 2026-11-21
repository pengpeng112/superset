# -*- coding: utf-8 -*-
"""20261120-RBAC-BACKEND：生成冻结快照 20261120-RBAC-BACKEND-SHA256.json。"""
import hashlib
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FREEZE_DIR = r"F:\python\superset\migration\冻结快照"
ROOT = r"F:\python\superset"

FILES = [
    # ---- 批目录：审计与备份 ----
    ("migration/sources/20261120-RBAC-BACKEND/audit_rbac_before.py", None),
    ("migration/sources/20261120-RBAC-BACKEND/before/rbac_state_full.json", "阶段0全量状态快照"),
    # ---- 阶段1：矩阵落地 ----
    ("migration/sources/20261120-RBAC-BACKEND/apply_rbac_matrix.py", "阶段1落地(APPLY_OK)"),
    ("migration/sources/20261120-RBAC-BACKEND/rollback_rbac_matrix.py", "回退(--dry-run 保护性拒绝实证)"),
    ("migration/sources/20261120-RBAC-BACKEND/evidence/apply/rbac_apply_plan.json", "写前计划"),
    ("migration/sources/20261120-RBAC-BACKEND/evidence/apply/rbac_changes_applied.json", "终报告 16 校验全过"),
    ("migration/sources/20261120-RBAC-BACKEND/evidence/apply/rbac_grant_sql.sql", "授权 SQL trace"),
    # ---- 阶段2：工具三件套 + 311 绑定 ----
    ("migration/sources/20261120-RBAC-BACKEND/superset_rbac_manage.py", "常驻工具"),
    ("migration/sources/20261120-RBAC-BACKEND/rbac_policy.json", "17 科室政策"),
    ("migration/sources/20261120-RBAC-BACKEND/全院角色矩阵与科室赋权操作手册.md", "操作手册"),
    ("migration/sources/20261120-RBAC-BACKEND/evidence/rbac_sync_policy_dryrun.json", "157人/310绑定预览"),
    ("migration/sources/20261120-RBAC-BACKEND/evidence/rbac_sync_policy_apply.json", "310绑定落库"),
    ("migration/sources/20261120-RBAC-BACKEND/evidence/rbac_audit_after.json", "apply后审计"),
    ("migration/sources/20261120-RBAC-BACKEND/evidence/rbac_status_after.json", "apply后状态"),
    # ---- 阶段4：验收 20/20 ----
    ("migration/sources/20261120-RBAC-BACKEND/verify_rbac_backend.py", "验收脚本"),
    ("migration/sources/20261120-RBAC-BACKEND/evidence/verify/rbac_verify_report.json", "20/20 全绿"),
    # ---- 审计证据 ----
    ("migration/sources/20261120-RBAC-BACKEND/evidence/security_audit_before.json", "F1-F6 审计发现"),
    ("migration/sources/20261120-RBAC-BACKEND/evidence/全院HIS科室列表与人数统计-脱敏.csv", "科室字典脱敏"),
    # ---- 生产对齐与收尾 ----
    ("offline-bundle/scripts/superset_rbac_manage.py", "生产常驻"),
    ("offline-bundle/scripts/rbac_policy.json", "生产常驻"),
    ("offline-bundle/scripts/superset_health_check.sh", "升 18 项（第9项 RBAC 恒常）"),
    ("offline-bundle/PRODUCTION-MANIFEST-20261120.json", "35/35 对齐"),
    ("migration/sources/20261120-RBAC-BACKEND/build_manifest20.py", None),
    ("migration/sources/20261120-RBAC-BACKEND/freeze_snapshot20.py", None),
    ("migration/sources/20261120-RBAC-BACKEND/最终报告.md", None),
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
        p = os.path.join(ROOT, rel.replace("/", os.sep))
        if not os.path.exists(p):
            entries.append({"file": rel, "missing": True, "note": note or ""})
            continue
        entries.append({"file": rel, "bytes": os.path.getsize(p), "sha256": sha256_file(p), "note": note or ""})
    snap = {
        "batch": "20261120-RBAC-BACKEND",
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": "Gamma 大锅饭终结：35 张业务看板从 Gamma 解绑（仅留外壳 34），11 个报表授权_ 角色矩阵管辖全部 52 张已发布看板，datasource_access 6→66 对数据闸门，17 职能科室 311 绑定落位；渗透验收 20/20 全绿（003158 正负向闭环、001283/001643 摘除拒绝 exit3），体检升 18 项全绿，offline-bundle 35/35 对齐；f15b 不触发（导出实测 200 非 403）",
        "production_changes": [
            "ab_role：344→351（新增 346-352 七个报表授权_角色，341/343/344/345 保留）",
            "dashboard_roles：51→63（Gamma 解绑 34 张业务看板，仅留外壳 34）",
            "datasource_access：6→66 对（43 个数据集，SQL 单事务幂等授权 + 序列修复）",
            "ab_user_role：4767→5077（17 科室 311 绑定 + 1 受保护=312，FAB PUT 合并保留既有角色）",
            "/home/superset/superset_home/scripts/：新增 superset_rbac_manage.py + rbac_policy.json",
            "/home/superset/superset_home/scripts/superset_health_check.sh：17→18 项（第 9 项 RBAC 恒常）",
            "migration_20261120/：apply_rbac_matrix.py / rollback_rbac_matrix.py / verify_rbac_backend.py / audit_rbac_before.py",
        ],
        "rollback": "rollback_rbac_matrix.py（正确顺序：先 revoke-dept 清人员赋权再 --apply；字节级兜底=before/rbac_tables_before.sql.gz 11 表 COPY 全量）；工具层护栏：报表授权_前缀校验 + 001283/001643 受保护摘除拒绝 exit3 + flock /tmp/user_sync.lock",
        "files": entries,
    }
    out = os.path.join(FREEZE_DIR, "20261120-RBAC-BACKEND-SHA256.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
    print("saved", out)
    miss = [e for e in entries if e.get("missing")]
    print("missing:", miss if miss else "无")


if __name__ == "__main__":
    main()
