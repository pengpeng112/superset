# -*- coding: utf-8 -*-
"""20261118-DETAIL-UX：生成本批冻结快照 SHA256（批次产物 + 生产变更文件）。"""
import hashlib
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FREEZE_DIR = r"F:\python\superset\migration\冻结快照"

FILES = [
    ("migration/sources/20261118-DETAIL-UX/diagnose_clip_before.py", None),
    ("migration/sources/20261118-DETAIL-UX/evidence/clip_before.json", None),
    ("migration/sources/20261118-DETAIL-UX/deploy_f14.py", None),
    ("migration/sources/20261118-DETAIL-UX/verify_detail_ux.py", None),
    ("migration/sources/20261118-DETAIL-UX/reverify_a3.py", "A3 段重验（max-padding 补丁后）"),
    ("migration/sources/20261118-DETAIL-UX/reverify_p32.py", "32 号会话停滞单独重验"),
    ("migration/sources/20261118-DETAIL-UX/build_manifest.py", None),
    ("migration/sources/20261118-DETAIL-UX/freeze_snapshot.py", None),
    ("migration/sources/20261118-DETAIL-UX/evidence/detail_ux_acceptance.json", "111/111 PASS"),
    ("offline-bundle/custom/report-ui.js", "生产变更：/home/superset/custom/report-ui.js"),
    ("offline-bundle/nginx.conf", "生产变更：/home/superset/nginx.conf（inode 47580611 保持）"),
    ("offline-bundle/PRODUCTION-MANIFEST-20261118.json", None),
    ("migration/sources/20261118-DETAIL-UX/最终报告.md", None),
    ("migration/sources/20261118-DETAIL-UX/before-assets/report-ui.js", "写前备份（f13 生产原样）"),
    ("migration/sources/20261118-DETAIL-UX/before-assets/nginx.conf", "写前备份"),
]


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    root = r"F:\python\superset"
    entries = []
    for rel, note in FILES:
        p = os.path.join(root, rel.replace("/", os.sep))
        if not os.path.exists(p):
            entries.append({"file": rel, "missing": True, "note": note or ""})
            continue
        entries.append({
            "file": rel,
            "bytes": os.path.getsize(p),
            "sha256": sha256_file(p),
            "note": note or "",
        })
    snap = {
        "batch": "20261118-DETAIL-UX",
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": "明细表裁切/双滚动条根治（report-ui 20261108f13→20261118f14）+ 工具条收起筛选/全屏看表 + 滚动条加粗 + 长文本气泡 + 灾备清扫（2 个 $f 脏文件与 12 个 profile 缓存目录）",
        "production_changes": [
            "/home/superset/custom/report-ui.js（20261108f13 → 20261118f14）",
            "/home/superset/nginx.conf（report-ui 版本串更新；inode 47580611 保持，仅 nginx -t + reload，零容器重启）",
        ],
        "rollback": "73:/home/superset/migration-private/20261118-DETAIL-UX/before/（report-ui.js/monthly-report.js/nginx.conf 写前备份）",
        "files": entries,
    }
    out = os.path.join(FREEZE_DIR, "20261118-DETAIL-UX-SHA256.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
    print("saved", out)
    for e in entries:
        print(("MISSING " if e.get("missing") else "%s  %s" % (e.get("sha256", "")[:16], e["file"])))


if __name__ == "__main__":
    main()
