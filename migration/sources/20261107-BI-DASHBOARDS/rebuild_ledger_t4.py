# -*- coding: utf-8 -*-
"""20261107-BI-DASHBOARDS T4：从生产重建 bi_created_ledger.json（含 uuid）。
现存：看板 72/73/74、图表 id>354、数据集 id>372；另列中途已删除的 355-370、388、看板 71 备查。"""
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from bi_api import *  # noqa

s = admin()
HERE = os.path.dirname(os.path.abspath(__file__))

# 看板
dashes = []
for did in (72, 73, 74):
    d = get_dashboard(s, did)
    dashes.append({"type": "dashboard", "id": did, "uuid": d["uuid"], "title": d["dashboard_title"], "preexisting": False})
# 图表（全量列表后本地过滤，中文名 Rison 查重不可靠——坑5）
r = s.get(BASE + "/api/v1/chart/?q=" + json.dumps({"page_size": 1000}), timeout=120)
charts_all = r.json()["result"]
charts = [{"type": "chart", "id": c["id"], "uuid": c["uuid"], "title": c["slice_name"], "viz_type": c["viz_type"], "datasource_id": c["datasource_id"], "preexisting": False}
          for c in charts_all if c["id"] > 354]
# 数据集
r = s.get(BASE + "/api/v1/dataset/?q=" + json.dumps({"page_size": 1000}), timeout=120)
dsets_all = r.json()["result"]
dsets = [{"type": "dataset", "id": d["id"], "uuid": d["uuid"], "table_name": d["table_name"], "preexisting": False}
         for d in dsets_all if d["id"] > 372]

ledger = {
    "batch": "20261107-BI-DASHBOARDS",
    "rebuilt_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    "note": "T4 从生产枚举重建；deleted_* 为本批创建后中途已删除对象，仅备查，不可回滚恢复。",
    "dashboards": dashes,
    "charts": charts,
    "datasets": dsets,
    "deleted_for_reference": {
        "charts": list(range(355, 371)) + [388],
        "dashboards": [71],
    },
}
io.open(HERE + "/bi_created_ledger.json", "w", encoding="utf-8").write(json.dumps(ledger, ensure_ascii=False, indent=1))
print("dashboards:", [(d["id"], d["title"], d["uuid"]) for d in dashes])
print("charts (%d):" % len(charts), [(c["id"], c["title"]) for c in charts])
print("datasets:", [(d["id"], d["table_name"], d["uuid"]) for d in dsets])
print("deleted_for_reference:", ledger["deleted_for_reference"])
