# -*- coding: utf-8 -*-
"""生成 20261106-CHINESE-TABLEUI 冻结 SHA256 JSON。"""
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
    assets = {
        "custom/report-ui.js": {"sha256": sha(os.path.join(ROOT, "offline-bundle/custom/report-ui.js")), "version": "20261106f11"},
        "nginx.conf": {"sha256": sha(os.path.join(ROOT, "offline-bundle/nginx.conf")), "version": "inode 47580611 保持"},
    }
    freeze = {
        "run_id": "20261106-CHINESE-TABLEUI",
        "date": "2026-11-08",
        "summary": "在用查询页数据集英文表头 verbose_name 批量汉化（59 列）+ report-ui 20261106f11 宽表首列冻结/数值右对齐/零值柔化/合计行高亮",
        "assets_final": assets,
        "production_before_assets": {
            "custom/report-ui.js": "aa05c5ec64a0c712b1ca36078ad82c7f028e971c7fc37419bae14acbe958321f (20261105f10)",
            "nginx.conf": "cdf805a1a5e3b15ed9cd66b0210d7c643f591956ef21ba6e29bdf610b38e9d94 (inode 47580611)",
            "server_backup_dir": "73:/home/superset/migration-private/20261106-CHINESE-TABLEUI/"
        },
        "metadata_write": {
            "scope": "table_columns.verbose_name 仅 59 行（列 id 清单见 column_verbose_patch.json）；column_name/SQL/保护对象零触碰",
            "backup": "columns_before.json（59 行 old_verbose_name，全部为空或=column_name）；回退脚本 rollback_columns.py→rollback_columns.sql",
            "write_lock": "服务器 /tmp/user_sync.lock flock 互斥；UPDATE 各 1 行共 59 行；写后核验 columns_after.tsv 59/59 与映射一致",
            "cache": "Redis db0(CACHE)/db1(DATA_CACHE) FLUSHDB（22/0→0/0）；db2/db3/db4 未触碰（DBSIZE 24/3/1440 写前后不变）"
        },
        "protection_verification": {
            "counts_before_after": "charts=65 datasets=75 dashboards=49 users=2383 published=47 roles=342 rls=0 完全一致",
            "hash_groups": "8 大组 20 子组哈希写前=写后（G2_columns 组哈希不含 verbose_name 字段，本批写入项不改变任何组哈希；写入范围由 UPDATE 语句的 id+table_id+column_name 三重限定与 59 行 UPDATE 1 结果证）",
            "nginx_inode": "47580611 保持；容器零重启；superset init 未运行"
        },
        "acceptance": {
            "matrix": "Chrome 156.0.8078.81 + Chromium 87.0.4272.0 × 1920×1080/1366×768 × admin；主矩阵 acc3（12 页：35/36/41/45/46/47/50/51/58/59/60/65）4 轮 + 必选条件页专项 acc3b（51/58/59 真实选科室/门诊/visit_id 后查询）4 轮",
            "total": 316,
            "pass": 300,
            "fail": 16,
            "fail_breakdown": {
                "superseded_by_acc3b": 8,
                "note": "主矩阵 51/58 的 8 项 FAIL 系必选条件页无数据表（守卫拦截首查属预期），acc3b 专项真实设条件后 4 轮全部 PASS（科室下拉/门诊分支/visit_id 输入交互）→ 51/58 终判 PASS",
                "page59_slow_query": 8,
                "note59": "59 页 visit_id 1-99 为全量大查询（>300s 无表，守卫放行正常）；属业务慢查与本批变更无关（verbose_name 不进 SQL）；该页数据集 337 的 4 列汉化（HJ/VISIT_ID1/VISIT_ID2/STAT_BEGIN）已由 columns_after.tsv 数据库级核验；59 页为任务必验 10 页之外的自选页"
            },
            "evidence": "chinese-tableui-acceptance.json/.csv、acc3-*.json、acc3b-*.json、shots/ 脱敏截图"
        },
        "key_files": [
            "migration/sources/20261106-CHINESE-TABLEUI/最终报告.md",
            "migration/sources/20261106-CHINESE-TABLEUI/untranslated_columns_scan.json（84 列扫描）",
            "migration/sources/20261106-CHINESE-TABLEUI/column_verbose_patch.json（59 列映射含依据）",
            "migration/sources/20261106-CHINESE-TABLEUI/skipped_ambiguous_columns.json（25 列不写入及原因）",
            "migration/sources/20261106-CHINESE-TABLEUI/columns_before.json + rollback_columns.py（回退）",
            "migration/sources/20261106-CHINESE-TABLEUI/columns_after.tsv（写后核验 59/59）"
        ],
        "rollback": "见最终报告 §回退"
    }
    out = os.path.abspath(os.path.join(HERE, "..", "..", "冻结快照", "20261106-CHINESE-TABLEUI-SHA256.json"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(freeze, f, ensure_ascii=False, indent=1)
    print("freeze ->", out)
    for k, v in assets.items():
        print(k, v["sha256"], v["version"])


if __name__ == "__main__":
    main()
