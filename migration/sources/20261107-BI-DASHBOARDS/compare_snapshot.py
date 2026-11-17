# -*- coding: utf-8 -*-
"""对比 snapshot_bi.sh 输出与写前快照 snapshot-before.raw。
用法：python compare_snapshot.py <新快照.raw>   （默认 snapshot-review.raw）
判定：EXIST_* 必须逐组等于写前同名全量组；G4/G5/G7/G8 全量组必须相同；
     G1/G3 全量组因本批新增对象变化属预期；G2/G6 全量组仅在本批新建数据集时允许变化（新增行见 NEW_* 清单）。"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(p):
    d = {}
    for ln in io.open(p, encoding="utf-8"):
        ln = ln.strip()
        if ln.startswith("HASH "):
            parts = ln.split()
            d[parts[1]] = (parts[2], parts[3])
        elif ln.startswith("COUNTS "):
            d["COUNTS"] = ln
    return d


def main():
    newp = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "snapshot-review.raw")
    b = load(os.path.join(HERE, "snapshot-before.raw"))
    a = load(newp)
    print("BEFORE", b.get("COUNTS"))
    print("NOW   ", a.get("COUNTS"))
    bad = []
    for k in sorted(x for x in a if x.startswith("EXIST_")):
        base = k[len("EXIST_"):]
        ok = base in b and b[base][1] == a[k][1]
        print("%-28s %s" % (k, "EQUAL" if ok else "DIFF!!"))
        if not ok:
            bad.append(k)
    for k in ("G4_users", "G5_roles", "G5_user_role", "G6_permissions", "G6_perm_view_role",
              "G7_rls_filters", "G7_rls_tables", "G7_rls_roles", "G8_favstar"):
        ok = k in a and k in b and a[k][1] == b[k][1]
        print("%-28s %s" % (k, "SAME" if ok else "CHANGED!!"))
        if not ok:
            bad.append(k)
    for k in ("G1_dashboards", "G1_dashboard_slices", "G1_dashboard_roles", "G3_charts",
              "G2_datasets", "G2_columns", "G2_metrics", "G6_view_menu", "G6_perm_view"):
        if k in a and k in b:
            print("%-28s %s (%s -> %s)" % (k, "SAME" if a[k][1] == b[k][1] else "changed(新增对象)", b[k][0], a[k][0]))
    print("RESULT:", "PASS 原有对象零修改" if not bad else "FAIL %s" % bad)


if __name__ == "__main__":
    main()
