# -*- coding: utf-8 -*-
"""生成 20261105-TOOLBAR-GUARD 冻结 SHA256 JSON。"""
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def main():
    assets = {}
    for rel, name in [
        ("offline-bundle/custom/report-ui.js", "custom/report-ui.js"),
        ("offline-bundle/custom/report-guards.js", "custom/report-guards.js"),
        ("offline-bundle/nginx.conf", "nginx.conf"),
    ]:
        p = os.path.join(ROOT, rel)
        assets[name] = {"local_sha256": sha(p), "version": None}
    assets["custom/report-ui.js"]["version"] = "20261105f10"
    assets["custom/report-guards.js"]["version"] = "20261105g4"
    assets["nginx.conf"]["version"] = "inode 47580611 保持"

    freeze = {
        "run_id": "20261105-TOOLBAR-GUARD",
        "date": "2026-11-07/08",
        "summary": "查询页显式报表工具条（导出Excel/CSV/行数耗时/行高切换）+ 5万/10万行截断强警告 + 62/65 跨度防呆守卫 + 61 首载兜底收窄",
        "assets_final": assets,
        "production_before_assets": {
            "custom/report-ui.js": "d21a7fb9e9525c4d35c9f065df53e60af7f2fdce2c394e6d985e0f5768394af0 (20261104f9)",
            "custom/report-guards.js": "2de2a627a9ae3a7e26fca3db4b66c5ddfd32d0897a1d0d800e57f9b275de3d5d (20261022g3)",
            "nginx.conf": "a0029e16d2c93c776b4299be7a50f6215fa3dc18729f3b319f9799458ee06d5d (inode 47580611)",
            "server_backup_dir": "73:/home/superset/migration-private/20261105-TOOLBAR-GUARD/before-assets/"
        },
        "production_metadata_changes": {
            "dataset_363_sql_sha256": {
                "before": "f5e3a9bafcc5329e11e471b505e22e2499b59877f766326338116a22dd7b3810",
                "after": "708107a6a36616831d62a6e59023e5d633fd11c12b31a412b9aa54d4364d2aad",
                "scope": "仅无筛选兜底窗口收窄：to 兜底 TRUNC(SYSDATE,'MM') → TRUNC(ADD_MONTHS(SYSDATE,-1),'MM')+7（上月前7天）；from 兜底与用户选择分支不变"
            },
            "dashboard_61_position_json_sha256": {
                "before": "7aa3196542f11c74165101616783fd65c92474382a5c5336edf9a854eedd70ed",
                "after": "b3f4590f481fc94b234df9b3639de123ff48ce541eb65d8017309210eed6e2af",
                "scope": "仅 MD-BACK 头部说明（text+code）：修正“默认当月”并追加任务指定句；其余组件/结构不变"
            }
        },
        "protection_verification": {
            "counts_before_after": "charts=65 datasets=75 dashboards=49 users=2383 published=47 roles=342 rls=0 完全一致",
            "hash_groups": "8 大组 20 子组中仅 G1_dashboards 与 G2_datasets 因 61/363 两行获准预期变更；G1_dashboards_ex61 与 G2_datasets_ex363 及其余 16 子组写前=写后",
            "nginx_inode": "47580611 保持；容器零重启；superset init 未运行"
        },
        "acceptance": {
            "matrix": "Chrome 156.0.8078.81 × {1920×1080, 1366×768} + Chromium 87.0.4272.0 × {1920×1080, 1366×768}，账号 admin",
            "total": 126,
            "pass": 126,
            "fail": 0,
            "evidence": "toolbar-guard-acceptance.json/.csv、acc2-*.json、density-c87-*.json、shots/ 脱敏截图、downloads/ 导出文件样本"
        },
        "key_files": [
            "migration/sources/20261105-TOOLBAR-GUARD/最终报告.md",
            "migration/sources/20261105-TOOLBAR-GUARD/snapshot-before.raw / snapshot-after.raw",
            "migration/sources/20261105-TOOLBAR-GUARD/ds363_before.sql / ds363_after.sql / update_ds363.sql",
            "migration/sources/20261105-TOOLBAR-GUARD/d61_position_before.json / d61_position_after.json / update_d61.sql",
            "migration/sources/20261105-TOOLBAR-GUARD/acc2_run.py（验收驱动）",
            "migration/sources/20261105-TOOLBAR-GUARD/diag*.py（过程诊断，保留供复查）"
        ],
        "rollback": "见最终报告 §回退"
    }
    out = os.path.abspath(os.path.join(HERE, "..", "..", "冻结快照", "20261105-TOOLBAR-GUARD-SHA256.json"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(freeze, f, ensure_ascii=False, indent=1)
    print("freeze ->", out)
    for k, v in assets.items():
        print(k, v["local_sha256"], v["version"])


if __name__ == "__main__":
    main()
