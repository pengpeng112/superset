# -*- coding: utf-8 -*-
"""20261119-BI-ENHANCE：生成冻结快照 20261119-BI-ENHANCE-SHA256.json。"""
import hashlib
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FREEZE_DIR = r"F:\python\superset\migration\冻结快照"
ROOT = r"F:\python\superset"

FILES = [
    ("migration/sources/20261119-BI-ENHANCE/recon_nursing.py", None),
    ("migration/sources/20261119-BI-ENHANCE/probe_nursing2.py", None),
    ("migration/sources/20261119-BI-ENHANCE/probe_final_recon.py", None),
    ("migration/sources/20261119-BI-ENHANCE/evidence/nursing_sql_recon.json", "勘察对账"),
    ("migration/sources/20261119-BI-ENHANCE/create_bi_nursing.py", None),
    ("migration/sources/20261119-BI-ENHANCE/build_longtable.py", None),
    ("migration/sources/20261119-BI-ENHANCE/rollback_bi_enhance.py", "回退（--dry-run PASS）"),
    ("migration/sources/20261119-BI-ENHANCE/bi_enhance_ledger.json", "台账"),
    ("migration/sources/20261119-BI-ENHANCE/deploy_bi_enhance.py", None),
    ("migration/sources/20261119-BI-ENHANCE/capture_warmup75.py", None),
    ("migration/sources/20261119-BI-ENHANCE/run_warmup_remote.py", None),
    ("migration/sources/20261119-BI-ENHANCE/verify_bi_enhance.py", None),
    ("migration/sources/20261119-BI-ENHANCE/build_manifest19.py", None),
    ("migration/sources/20261119-BI-ENHANCE/freeze_snapshot19.py", None),
    ("migration/sources/20261119-BI-ENHANCE/evidence/bi_enhance_acceptance.json", "66/66 PASS"),
    ("migration/sources/20261119-BI-ENHANCE/evidence/warmup_templates.json", "46 条模板副本"),
    ("migration/sources/20261119-BI-ENHANCE/evidence/print-dash75.pdf", "打印留证"),
    ("migration/sources/20261119-BI-ENHANCE/evidence/print-page36.pdf", "打印留证"),
    ("migration/sources/20261119-BI-ENHANCE/evidence/dash75_check.png", "看板 75 截图"),
    ("offline-bundle/custom/report-dates.js", "生产变更 d19"),
    ("offline-bundle/custom/home-ui.js", "生产变更 h17"),
    ("offline-bundle/custom/report-ui.js", "生产变更 f15"),
    ("offline-bundle/nginx.conf", "生产变更（inode 47580611 保持）"),
    ("offline-bundle/scripts/warmup_templates.json", "生产变更 46 条"),
    ("offline-bundle/PRODUCTION-MANIFEST-20261119.json", None),
    ("migration/sources/20261119-BI-ENHANCE/最终报告.md", None),
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
        "batch": "20261119-BI-ENHANCE",
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": "第 4 个 BI 驾驶舱 75（bi-nursing-bed：KPI×4+TOP15+分级护理环形饼+汇总表，图表 393-399、数据集 375）+ ⭐我的常用报表收藏夹（h17，localStorage 按工号隔离）+ 汇报投屏/打印报表/A4 横向干净打印（f15）+ 预热模板 46 条（d19 同步 75）；验收 66/66 PASS，存量 1-374/1-74 零篡改",
        "production_changes": [
            "/home/superset/custom/report-dates.js（20261111d18 → 20261119d19）",
            "/home/superset/custom/home-ui.js（20261117h16 → 20261119h17）",
            "/home/superset/custom/report-ui.js（20261118f14 → 20261119f15，终版 73d6fcb1…）",
            "/home/superset/nginx.conf（三版本串；inode 47580611 保持，仅 reload）",
            "/home/superset/superset_home/scripts/warmup_templates.json（39→46 条）",
            "元库新增：看板 75 / 图表 393-399 / 数据集 375（零修改存量）",
        ],
        "rollback": "rollback_bi_enhance.py（--dry-run 已验证）删除本批 9 个对象；73:/home/superset/migration-private/20261119-BI-ENHANCE/before/ 写前三 JS/nginx/warmup 备份 + 本地 before-assets/",
        "files": entries,
    }
    out = os.path.join(FREEZE_DIR, "20261119-BI-ENHANCE-SHA256.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
    print("saved", out)
    miss = [e for e in entries if e.get("missing")]
    print("missing:", miss if miss else "无")


if __name__ == "__main__":
    main()
