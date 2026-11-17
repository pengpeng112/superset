# -*- coding: utf-8 -*-
"""根据只读快照生成对象台账；不连接业务数据库，不更改生产对象。"""
import argparse
import collections
import csv
import hashlib
import json
import re
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_csv(name, rows):
    with (HERE / name).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--meta", type=Path, default=Path("C:/temp/dw_work/srd_meta_all.json"))
    parser.add_argument("--raw-dir", type=Path, default=Path("C:/temp/dw_work/pbl_out"))
    args = parser.parse_args()
    metas = load(args.meta)
    snapshot = load(HERE / "生产元数据只读快照.json")
    semantics = load(HERE / "迁移语义与权限补充核查.json")
    mapping = semantics["source_mapping"]
    datasets = {d["id"]: d for d in snapshot["datasets"]}
    columns = collections.defaultdict(list)
    for c in semantics["column_metadata"]:
        columns[c["table_id"]].append(c)
    charts = collections.defaultdict(list)
    for c in snapshot["charts"]:
        charts[c["datasource_id"]].append(c)
    by_source = collections.defaultdict(list)
    for d in mapping:
        by_source[d["source_index"]].append(d)
    fail_file = snapshot["files"]["/app/superset_home/scripts/srd_fail_detail.json"]
    fail_keys = {(x["pbd"], x["dw"]) for x in fail_file["identifiers"]}
    raw = {}
    raw_manifest = []
    for p in sorted(args.raw_dir.glob("*.srd.json")):
        content = p.read_bytes()
        objects = json.loads(content)
        pbd = p.name.removesuffix("_dw.pbl.srd.json")
        raw_manifest.append({"file": p.name, "count": len(objects), "sha256": hashlib.sha256(content).hexdigest()})
        for dw, text in objects.items():
            raw[(pbd, dw)] = text

    source_rows = []
    for i, m in enumerate(metas, 1):
        deployed = by_source[i]
        status = "已建对象，业务待验收" if deployed else "未建对象：原 SQL 试跑失败记录" if (m["pbd"], m["dw"]) in fail_keys else "未建对象：未在 SQL 失败清单，原因待追溯"
        source_rows.append({
            "源序号": i, "模块": m["pbd"], "数据窗口": m["dw"], "提取标题（需核对）": m.get("title", ""),
            "状态": status, "对象份数": len(deployed), "数据集ID": ";".join(str(d["id"]) for d in deployed),
            "图表ID": ";".join(str(c["id"]) for d in deployed for c in charts[d["id"]]),
            "源参数名": ";".join(sorted(set(re.findall(r"(?<![:\w]):([A-Za-z_][A-Za-z0-9_.]*)", m["sql"])))),
            "源含compute控件": bool(re.search(r"\bcompute\(", raw.get((m["pbd"], m["dw"]), ""), re.I)),
        })
    report_rows = []
    for m in mapping:
        d = datasets[m["id"]]
        cs = columns[m["id"]]
        for c in charts[m["id"]]:
            report_rows.append({
                "图表ID": c["id"], "数据集ID": m["id"], "源序号": m["source_index"], "模块": m["pbd"], "数据窗口": m["dw"],
                "图表标题": c["slice_name"], "重复源对象": len(by_source[m["source_index"]]) > 1,
                "含NULL比较": bool(d["null_predicates"]), "存在WHERE不可满足查询块": bool(m["provably_rejected_query_blocks"]),
                "顶层WHERE不可满足": m["top_where_provably_rejects"],
                "NULL化后与提取SQL结构一致": m["source_ast_equal_after_null"],
                "日期主列": d["main_dttm_col"] or "", "可识别日期列数": sum(bool(col["is_dttm"]) for col in cs),
                "中文列数": sum(bool(re.search(r"[\u4e00-\u9fff]", col["column_name"])) for col in cs), "列数": len(cs),
                "含GROUP_BY": d["has_group_by"], "含ORDER_BY": d["has_order_by"], "含UNION": d["has_union"],
                "源含compute控件": bool(re.search(r"\bcompute\(", raw.get((m["pbd"], m["dw"]), ""), re.I)),
                "参数名": ";".join(m["source_bind_names"]), "结果上限": c["row_limit"],
                "业务验收": "未验证", "修复建议": "恢复参数及计算口径后验收" if d["null_predicates"] else "核对计算、中文列头、权限及完整性后验收",
            })
    save_csv("SRD源对象339条台账.csv", source_rows)
    save_csv("SRD图表212条复核台账.csv", report_rows)
    summary = {
        "source_count": len(metas), "srd_chart_count": len(report_rows), "unique_source_deployed": len({d["source_index"] for d in mapping}),
        "missing_source_count": sum(not by_source[i] for i in range(1, len(metas) + 1)),
        "missing_with_sql_failure_record": sum(not by_source[i] and (m["pbd"], m["dw"]) in fail_keys for i, m in enumerate(metas, 1)),
        "missing_without_sql_failure_record": sum(not by_source[i] and (m["pbd"], m["dw"]) not in fail_keys for i, m in enumerate(metas, 1)),
        "duplicate_extra_objects": sum(max(0, len(ds) - 1) for ds in by_source.values()),
        "null_affected_chart_count": sum(r["含NULL比较"] for r in report_rows), "top_where_rejected_count": sum(r["顶层WHERE不可满足"] for r in report_rows),
        "unique_null_affected_source_count": len({r["源序号"] for r in report_rows if r["含NULL比较"]}),
        "source_compute_count_deployed_unique": len({r["源序号"] for r in report_rows if r["源含compute控件"]}),
        "chinese_column_count": sum(r["中文列数"] for r in report_rows), "column_count": sum(r["列数"] for r in report_rows),
        "raw_srd_json_file_count": len(raw_manifest), "raw_srd_object_count": sum(p["count"] for p in raw_manifest),
        "source_meta_sha256": hashlib.sha256(args.meta.read_bytes()).hexdigest(), "raw_srd_manifest": raw_manifest,
    }
    assert summary["unique_source_deployed"] + summary["missing_source_count"] == summary["source_count"]
    assert summary["missing_with_sql_failure_record"] + summary["missing_without_sql_failure_record"] == summary["missing_source_count"]
    assert summary["unique_source_deployed"] + summary["duplicate_extra_objects"] == summary["srd_chart_count"]
    assert summary["source_meta_sha256"] == snapshot["files"]["/app/superset_home/scripts/srd_meta_all.json"]["sha256"]
    (HERE / "复核统计.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "raw_srd_manifest"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
