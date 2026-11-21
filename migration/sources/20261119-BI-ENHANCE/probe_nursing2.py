# -*- coding: utf-8 -*-
"""20261119-BI-ENHANCE 阶段0b：护理数据集实际数据勘察（月份分布/合计行/长表 METRIC 明细/日表行数/对账）。
只读。输出追加写 evidence/nursing_sql_recon.json（data 字段）。凭据环境变量。
"""
import json
import os
import sys
import time

sys.path.insert(0, r"F:\python\superset\migration\sources\20261107-BI-DASHBOARDS")
from bi_api import admin, guest, q, S, BASE  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def agg(col, label=None):
    return {"expressionType": "SIMPLE", "column": {"column_name": col}, "aggregate": "SUM", "label": label or col}


def main():
    s = admin()
    outp = os.path.join(HERE, "evidence", "nursing_sql_recon.json")
    rec = json.load(open(outp, encoding="utf-8"))
    rec["data"] = {}

    def probe(key, ds, query, viz="table", note=""):
        x = q(s, ds, query, viz=viz, force=True)
        rec["data"][key] = {"http": x.get("http"), "sec": x.get("sec"), "rows": x.get("rows"),
                            "err": (x.get("err") or "")[:200],
                            "data": (x.get("data") or [])[:60], "note": note}
        print("%-22s http=%s %.1fs rows=%s %s" % (key, x.get("http"), x.get("sec"), x.get("rows"),
                                                  (json.dumps((x.get('data') or [])[:3], ensure_ascii=False)[:200])), flush=True)

    # ds350 月份分布（最近 4 个月 + 行数）
    probe("ds350.months", 350, {"columns": ["STAT_BEGIN"], "metrics": [agg("DISCH_N", "出院人数"), agg("BED_END", "实有病床")],
                                "groupby": [], "row_limit": 30, "order_desc": False}, note="按 STAT_BEGIN 分布")
    # ds350 最新月按 KS 分布（看有无合计行）
    probe("ds350.byKS", 350, {"columns": ["KS"], "metrics": [agg("DISCH_N"), agg("OPEN_DAYS"), agg("USED_DAYS"), agg("OCC_DAYS")],
                              "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": "Latest month"}],
                              "row_limit": 100}, note="最新月按护理单元")
    # ds352 长表：METRIC 结构（最新月）
    probe("ds352.metrics", 352, {"columns": ["METRIC"], "metrics": [agg("VAL", "数值")],
                                 "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": "Latest month"}],
                                 "row_limit": 100}, note="汇总附区 METRIC 清单")
    # ds352 SECTION 清单
    probe("ds352.sections", 352, {"columns": ["SECTION", "METRIC"], "metrics": [agg("VAL", "数值")],
                                  "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": "Latest month"}],
                                  "row_limit": 100}, note="SECTION+METRIC")
    # ds351 日表行数（单日）与单日是否多行（PLSX）
    probe("ds351.oneday", 351, {"columns": ["KS", "PLSX"], "metrics": [agg("SPEC_CARE", "特级"), agg("CRIT_ILL", "病危"), agg("LVL2", "二级")],
                                "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": "Last day"}],
                                "row_limit": 60}, note="最近一天行结构")
    # ds351 月度单列合计对比（验证按月 SUM 是否翻倍：与 ds352 全院汇总对）
    probe("ds351.monthSUM", 351, {"columns": [], "metrics": [agg("SPEC_CARE", "特级"), agg("CRIT_ILL", "病危"), agg("CRIT_SEVERE", "病重"),
                                                             agg("GEN_LVL1", "普通"), agg("LVL2", "二级"), agg("LVL3", "三级"), agg("DISCH_NUM", "出院")],
                                  "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": "Latest month"}],
                                  "row_limit": 10}, note="最新月全表 SUM")
    # ds355 月份分布与样本
    probe("ds355.months", 355, {"columns": [], "metrics": [agg("入院人数", "入院"), agg("占用床日", "占用床日")],
                                "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": "Latest month"}],
                                "row_limit": 5}, note="最新月合计")
    probe("ds355.byUnit", 355, {"columns": ["护理单元名称"], "metrics": [agg("入院人数"), agg("占用床日"), agg("开放床位")],
                                "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": "Last day"}],
                                "row_limit": 60}, note="最近一天按单元")
    # ds350 全月全院 SUM（含合计行）vs 排除合计行（对账翻倍检测）
    probe("ds350.monthAll", 350, {"columns": [], "metrics": [agg("DISCH_N", "出院"), agg("OPEN_DAYS"), agg("USED_DAYS"), agg("OCC_DAYS"), agg("BED_END")],
                                  "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": "Latest month"}],
                                  "row_limit": 5}, note="最新月全表SUM(含合计行)")
    probe("ds350.monthNoSum", 350, {"columns": [], "metrics": [agg("DISCH_N", "出院"), agg("OPEN_DAYS"), agg("USED_DAYS"), agg("OCC_DAYS"), agg("BED_END")],
                                    "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": "Latest month"}],
                                    "extras": {"having": "", "where": "KS NOT IN ('合计','总计','全院','计')"},
                                    "row_limit": 5}, note="最新月SUM排除合计行")
    probe("ds350.rowCount", 350, {"columns": ["KS"], "metrics": [agg("BED_END", "床位")],
                                  "filters": [{"col": "STAT_BEGIN", "op": "TEMPORAL_RANGE", "val": "Latest month"}],
                                  "row_limit": 100}, note="最新月全行清单")
    # 月份最大值：直接查 STAT_BEGIN 降序
    probe("ds350.latest", 350, {"columns": ["STAT_BEGIN"], "metrics": [agg("DISCH_N", "出院")], "row_limit": 6, "order_desc": True},
          note="STAT_BEGIN 降序前6")

    # Gamma 权限实质探测：guest POST chart/data 看错误正文（区分 CSRF 与数据源权限）
    g = guest()
    rec["gamma_probe"] = {}
    for ds in (350, 352, 351, 355, 349, 373, 374, 338):
        x = q(g, ds, {"metrics": [agg("BED_END", "床位")] if ds == 350 else [S("COUNT(*)")], "row_limit": 1}, viz="table")
        err = (x.get("err") or "")[:300]
        kind = "?"
        if x.get("http") == 200:
            kind = "OK"
        elif "CSRF" in err or "csrf" in err:
            kind = "CSRF-BLOCKED(权限无法判定,以浏览器验收为准)"
        elif "permission" in err.lower() or "access" in err.lower() or "授权" in err:
            kind = "DATASET-DENIED"
        rec["gamma_probe"][str(ds)] = {"http": x.get("http"), "kind": kind, "err": err}
        print("gamma ds%s http=%s kind=%s %s" % (ds, x.get("http"), kind, err[:120]), flush=True)

    json.dump(rec, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("saved", outp)


if __name__ == "__main__":
    main()
