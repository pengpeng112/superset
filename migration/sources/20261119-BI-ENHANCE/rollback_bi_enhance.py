# -*- coding: utf-8 -*-
"""20261119-BI-ENHANCE 回退脚本（--dry-run 预演 / 实删）。
回退范围（仅本批新建对象，零触碰存量 1-374/1-74）：
  - 看板 slug=bi-nursing-bed（75）
  - 图表：本批 7 张（bi_enhance_ledger.json 记录的 id/名称）
  - 数据集：BI_护理级别人日构成长表（375）
  - Gamma 授权：本批 gamma_grants（本批实测无需授权，通常为空）
用法：
  python rollback_bi_enhance.py --dry-run
  ACC_ADMIN=<口令> python rollback_bi_enhance.py --do
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"F:\python\superset\migration\sources\20261107-BI-DASHBOARDS")
from bi_api import admin, BASE  # noqa: E402

LEDGER_PATH = os.path.join(HERE, "bi_enhance_ledger.json")


def main():
    dry = "--dry-run" in sys.argv
    do = "--do" in sys.argv
    ledger = json.load(open(LEDGER_PATH, encoding="utf-8"))
    chart_ids = [c["id"] for c in ledger.get("charts", []) if c.get("id")]
    ds_ids = [d["id"] for d in ledger.get("new_datasets", []) if d.get("id")]
    dash_ids = [d["id"] for d in ledger.get("dashboards", []) if d.get("id")]
    grants = ledger.get("gamma_grants", [])
    print("回退计划（dry-run=%s）：" % dry)
    print("  dashboards:", dash_ids)
    print("  charts:", chart_ids)
    print("  datasets:", ds_ids)
    print("  gamma grants:", grants or "无（本批未做任何授权变更）")
    s = admin()
    if not do:
        # dry-run：逐对象 GET 存在性核验
        ok = True
        for cid in chart_ids:
            r = s.get(BASE + "/api/v1/chart/%d" % cid, timeout=30)
            print("  chart %s -> %s %s" % (cid, r.status_code,
                  (r.json()["result"]["slice_name"] if r.ok else "")[:40]))
            ok = ok and r.ok
        for did in ds_ids:
            r = s.get(BASE + "/api/v1/dataset/%d" % did, timeout=30)
            print("  dataset %s -> %s %s" % (did, r.status_code,
                  (r.json()["result"]["table_name"] if r.ok else "")[:40]))
            ok = ok and r.ok
        for did in dash_ids:
            r = s.get(BASE + "/api/v1/dashboard/%d" % did, timeout=30)
            print("  dashboard %s -> %s %s slug=%s" % (did, r.status_code,
                  (r.json()["result"]["dashboard_title"] if r.ok else "")[:40],
                  r.json()["result"].get("slug") if r.ok else ""))
            ok = ok and r.ok
        print("DRY-RUN %s" % ("PASS（全部对象存在，可安全回退）" if ok else "FAIL（对象缺失，人工核对）"))
        return
    # 实删：先删图表（解除看板关联），再删数据集，再删看板
    for cid in chart_ids:
        r = s.delete(BASE + "/api/v1/chart/%d" % cid, timeout=60)
        print("  DEL chart %s -> %s" % (cid, r.status_code))
    for did in ds_ids:
        r = s.delete(BASE + "/api/v1/dataset/%d" % did, timeout=60)
        print("  DEL dataset %s -> %s" % (did, r.status_code))
    for did in dash_ids:
        r = s.delete(BASE + "/api/v1/dashboard/%d" % did, timeout=60)
        print("  DEL dashboard %s -> %s" % (did, r.status_code))
    print("回退完成 %s" % time.strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    main()
