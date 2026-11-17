"""离线初始化/校验 round-5 计划包。不连接生产，不覆盖已存在台账。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PLAN = ROOT / "superset-报表补迁与一致性验收及人员赋权长任务计划-v1.md"
BASELINE = HERE.parent / "round-4" / "SRD源对象339条台账.csv"

# 依赖是同一批次/对象的门禁；跨批次可重复执行同一阶段，不能一次通过替代所有报表。
TASKS = {
    "P0-S1": ("既有授权/round-4", "现场版本、对象/权限/运行差异、只读能力证据", "现场差异已登记，未执行业务写入"),
    "P0-S2": ("P0-S1", "私有新备份、对象快照、保护对象与恢复验证", "临时库能恢复；既有专项授权可恢复"),
    "P0-S3": ("P0-S1", "run_id、私有目录、互斥锁及同步调度契约", "身份/权限写入互斥，秘密不进公开证据"),
    "P1-S1": ("P0-S1/P0-S2/P0-S3", "环境注入、唯一键、分页、幂等与原子落账实现", "无硬编码凭据，重跑不重复，失败可恢复"),
    "P1-S2": ("P1-S1", "本机实际 API/关联契约、测试对象及读回证据", "布局关系真实建立，前端和关系读回一致"),
    "P1-S3": ("P1-S1/P1-S2", "编译/部署/对账/授权/回退工具与 dry-run 计划", "默认 dry-run、绑定计划 SHA、错误响应不当成功"),
    "P1-S4": ("P1-S3", "幂等、权限、参数、失败及恢复测试证据", "dry-run 无写入，必要故障测试通过"),
    "P2-S1": ("P0-S1", "原 PBD/SRD 版本清单与 21/812 差异依据", "339 外对象和非 SQL 类型已盘点"),
    "P2-S2": ("P2-S1", "菜单/窗口/来源/分支功能目录、在用功能 N", "功能不以来源数代替，每个处置有证据"),
    "P2-S3": ("P2-S1/既有客户端授权", "合法旧客户端或明确的独立参考恢复方案", "不改原资产/源库；有可验证当前旧入口"),
    "P2-S4": ("P2-S2/P2-S3", "逐功能独立参考链和参考优先级", "参考不是迁移 SQL 自对，缺参考项不计准确"),
    "P3-S1": ("P0-S1/P2-S2/P8-S1基础控制", "实际权限来源/值域/继承/拒绝/时效契约", "表存在与真实客户端采用关系已实证"),
    "P3-S2": ("P3-S1", "私有精确身份映射及公开代号/异常统计", "不按姓名模糊匹配，不匹配人员不赋权"),
    "P3-S3": ("P3-S1/P3-S2", "人员×报表×操作×范围×有效期矩阵", "未知/冲突单列；专项授权保护，非最大并集"),
    "P3-S4": ("P3-S3", "参数默认值与真实授权范围分离证据", "科室参数不能覆盖服务端强制权限"),
    "P4-S1": ("P2-S4/P3-S3", "逐报表口径卡和可编译定义版本", "时间/状态/粒度/版本/精度/范围明确"),
    "P4-S2": ("P4-S1", "参数映射及查询块参数化实现", "无全量默认，NULL/ALL/边界与旧系统一致"),
    "P4-S3": ("P4-S1/P4-S2", "计算/过滤/排序/汇总/外部与打印实现", "必要业务计算未遗漏，范围在聚合前生效"),
    "P4-S4": ("P4-S1/P1-S4/P8-S1基础控制", "130 未覆盖及已有语义故障逐条分类修复", "44 其他未覆盖不猜原因，不靠删条件造数据"),
    "P4-S5": ("P4-S2/P4-S3/P4-S4", "既有对象纠偏、列/图表/看板关系和重复处置", "关系与原专项功能无回归，重复有映射后软退役"),
    "P5-S1": ("P2-S4/P4-S5/P8-S1基础控制", "旧新参考的数据版本/时间控制证据", "动态变化受控，不能混用日结/月快照"),
    "P5-S2": ("P5-S1", "每报表必做边界/范围/计算/截断用例", "覆盖业务有效分支，不仅双方空或正常月份"),
    "P5-S3": ("P5-S2", "完整范围机器差异统计及私有比较记录", "计数/金额/分组/计算/多重集一致，未截断"),
    "P5-S4": ("P5-S3", "旧参考→SQL→API/页面/导出分段验证", "不是仅 SQL 一致，输出链路均相符"),
    "P5-S5": ("P5-S4", "差异归因与修复或具体阻塞清单", "所有必做用例通过，未解释差异不放行"),
    "P6-S1": ("P3-S4/P5-S5", "基础角色、报表/范围角色、可见数据集模型", "不靠 Gamma/数据库全访问或隐藏列授权"),
    "P6-S2": ("P6-S1", "A甲/B乙交叉权限模型与兼容分组", "报表与范围绑定，不产生无关范围并集"),
    "P6-S3": ("P6-S2", "Base 拒绝/Regular 范围/关系不变量", "无映射拒绝，多维组合与聚合前范围正确"),
    "P6-S4": ("P6-S3", "强制范围与 UI 相交、可信身份、缓存版本", "URL/API 参数不能扩权，撤权缓存不复用"),
    "P6-S5": ("P6-S4", "导出/打印差距判断与服务端适配或阻塞", "同人各报表操作有据，全出口防绕过"),
    "P6-S6": ("P6-S5/P0-S2/P0-S3", "期望/实际授权差异、审核身份读回、对象回退包", "仅测试绑定，正式赋权留P9，不覆盖受保护专项授权"),
    "P7-S1": ("P6-S6/P1-S4", "身份与报表权限同步单一权威及真实 dry-run", "不新增默认 Gamma；异常空源保护/锁/撤权已实现"),
    "P7-S2": ("P7-S1", "入职/调科/离职/删除/重跑/422/空源证据", "下一同步不覆盖授权，删除和失活处理正确"),
    "P7-S3": ("P7-S2/P6-S6", "API/字段/导出/缓存/多角色/撤权负向矩阵", "非业务 Admin 实测，正负向与旧会话均通过"),
    "P8-S1": ("P0-S1/P1-S1基础控制先行；真实功能扩面前复验", "有界查询、总 deadline、并发和源端取消证据", "首次源库取数前生效；HTTP 超时不冒充数据库取消"),
    "P8-S2": ("P5-S5/P7-S3/P8-S1", "5–10 个不同复杂度样板及 G0–G5 证据", "涵盖未迁/计算/聚合/真实参数/交叉权限"),
    "P8-S3": ("P8-S2", "简单10–20/复杂1–5功能批次与冻结证据", "逐批完整门禁，新增问题回退本批而不重跑全部"),
    "P8-S4": ("P3-S4/P8-S1/适用批次", "超大明细受控任务/下载/审计与结果一致性", "复用授权，异步下载不能绕过权限"),
    "P9-S1": ("本批 G0–G5/P7-S3/P8-S3", "已确认人员绑定、发布和业务周期观察", "真实业务身份可用，旧新一致且无越权"),
    "P9-S2": ("P0-S2/P6-S6/本批回退验证", "对象级回退演练、授权先收缩、同步恢复", "不删 RLS 先暴露数据，不整体还原覆盖他人变更"),
    "P9-S3": ("全部在用功能验收/P9-S1/P9-S2", "覆盖/对账/权限/同步/备份/运维最终交接包", "在用功能100%，必做通过，未解释阻塞0"),
    "P9-S4": ("P9-S3/独立下线授权", "停旧条件说明或明确保留旧系统", "本任务不自行下线旧系统"),
}

TEMPLATES = {
    "功能目录.csv": ["report_key", "语义版本", "模块", "菜单引用", "窗口", "DataWindow引用", "source_keys", "调用分支", "旧数据版本", "在用状态", "在用依据", "实现路线", "对象映射引用", "口径状态", "权限模型状态", "独立参考状态", "对账状态", "权限状态", "性能状态", "发布状态", "验收状态", "阻塞引用", "证据路径", "更新时间"],
    "参数映射.csv": ["report_key", "语义版本", "调用分支", "参数键", "Retrieve顺序", "PB类型", "原默认值引用", "必选", "NULL语义", "ALL语义", "事件时间字段", "范围归属", "查询块位置", "原边界规则", "目标输入", "目标绑定规则", "服务端校验", "安全引用规则", "边界case_ids", "证据路径", "状态"],
    "计算映射.csv": ["report_key", "语义版本", "source_key", "计算项", "原控件或脚本", "原表达式引用", "作用域", "Filter或Sort影响", "NULL规则", "单位", "精度", "舍入顺序", "零分母规则", "目标表达式引用", "实现路线", "独立验证case_ids", "证据路径", "状态"],
    "权限矩阵.csv": ["principal_ref", "report_key", "操作", "scope_type", "scope_ref", "字段范围引用", "来源契约版本", "来源规则引用", "ALLOW_DENY_UNKNOWN", "继承与拒绝引用", "valid_from", "valid_to", "有效期引用", "在职状态依据", "旧当前结论", "新专项例外引用", "confidence", "decision_status", "冲突状态", "目标角色引用", "目标数据集引用", "目标RLS引用", "确认依据", "期望SHA", "实际SHA", "发布状态", "证据路径"],
    "人员映射.csv": ["principal_ref", "旧身份private_ref", "员工身份private_ref", "目标用户private_ref", "精确匹配方法", "证据引用", "匹配状态", "在职状态", "源完整性状态", "专项保护引用", "异常引用", "同步管理范围版本", "更新时间"],
    "对账用例.csv": ["case_id", "report_key", "语义版本", "场景", "必做", "参数定义引用", "principal_ref", "scope_ref", "数据版本", "数据时间控制引用", "旧独立参考类型", "参考证据引用", "比较字段引用", "比较粒度", "完整性校验方式", "预期边界或不变量", "缓存策略", "状态"],
    "对账结果.csv": ["run_id", "batch_id", "case_id", "attempt", "report_key", "定义SHA", "旧参考SHA或HMAC引用", "参考独立性", "数据时间控制状态", "完整范围状态", "是否截断", "旧行数", "新行数", "计数差异数", "金额差异数", "分组缺失数", "分组额外数", "逐行或多重集差异数", "计算差异数", "显示等值差异说明", "SQL段状态", "API段状态", "界面或导出段状态", "缓存策略", "耗时毫秒", "结论", "差异归因", "公开证据路径", "私有证据引用", "执行时间"],
    "权限测试.csv": ["run_id", "batch_id", "test_id", "attempt", "report_key", "principal_ref", "人员类型", "角色组合引用", "入口", "操作", "参数范围引用", "预期ALLOW_DENY", "预期数据及字段范围引用", "实际访问结果", "实际范围摘要引用", "是否扩权", "缓存预热状态", "撤权与旧会话状态", "同步前后版本", "导出旁路状态", "结论", "公开证据路径", "执行时间"],
    "变更记录.csv": ["run_id", "batch_id", "change_id", "report_key", "source_key", "对象类型", "对象ID或private_ref", "对象UUID", "动作", "管理范围版本", "计划SHA", "变更前SHA", "变更后SHA", "并发漂移检查", "apply状态", "API读回状态", "受保护对象回归", "私有回退包引用", "回退验证状态", "证据路径", "执行时间", "下一动作"],
    "阻塞事项.csv": ["block_id", "阶段任务", "report_keys", "source_keys", "principal_refs", "原状态", "具体原因", "所缺证据", "已尝试及结果", "是否需外部信息", "所需最小补充信息", "可继续的独立任务", "解除条件", "状态", "公开证据路径", "创建时间", "更新时间"],
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_initial_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as handle:
            existing = next(csv.reader(handle), [])
        if existing != fields:
            raise ValueError(f"已有文件表头不同，拒绝覆盖：{path.relative_to(ROOT)}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def initialize() -> None:
    baseline = read_rows(BASELINE)
    assert len(baseline) == 339, "仅适用于 round-4 的 339 条初始基线"
    counts = Counter(row["模块"] for row in baseline)
    created = Counter(row["模块"] for row in baseline if int(row["对象份数"]) > 0)
    module_rows = [{"模块": module, "源对象数": str(counts[module]), "已建不同来源数": str(created[module]), "未覆盖来源数": str(counts[module] - created[module]), "业务功能数": "待P2确认", "基线依据": "round-4/SRD源对象339条台账.csv", "刷新状态": "待P0刷新"} for module in sorted(counts)]
    write_initial_csv(HERE / "模块迁移基线.csv", list(module_rows[0]), module_rows)

    source_rows = []
    for row in baseline:
        source_rows.append({
            "source_key": f"srd339:{row['模块']}:{row['数据窗口']}:{row['源序号']}",
            "源序号": row["源序号"], "模块": row["模块"], "数据窗口": row["数据窗口"],
            "原提取标题_未核实": row["提取标题（需核对）"], "基线状态": row["状态"],
            "基线对象份数": row["对象份数"], "基线数据集ID": row["数据集ID"], "基线图表ID": row["图表ID"],
            "源参数名": row["源参数名"], "源含compute控件": row["源含compute控件"],
            "原资产SHA": "", "语义版本": "", "处置类型": "待确认", "在用依据": "", "report_keys": "",
            "来源状态": "已盘点_round4提取记录", "独立参考状态": "待核实", "口径状态": "待还原",
            "权限模型状态": "待确认", "对象状态": "已有_待纠偏" if int(row["对象份数"]) else "未建",
            "对账状态": "未验证", "权限测试状态": "未验证", "性能状态": "未验证", "发布状态": "本计划未发布",
            "目标对象映射引用": "", "定义SHA": "", "batch_id": "", "阻塞引用": "", "公开证据路径": "", "下一动作": "P0刷新后P2核实来源及业务入口", "更新时间": "2026-10-06",
        })
    write_initial_csv(HERE / "源对象执行台账.csv", list(source_rows[0]), source_rows)

    titles = dict(re.findall(r"^### (P\d+-S\d+) (.+)$", PLAN.read_text(encoding="utf-8"), flags=re.M))
    if set(titles) != set(TASKS):
        raise ValueError("计划步骤与初始化清单不一致")
    task_rows = [{"任务ID": key, "阶段": key.split("-")[0], "任务": titles[key], "前置依赖": value[0], "预期输出": value[1], "验收要求": value[2], "执行范围": "按运行/批次/报表重复适用", "计划依据": f"../../{PLAN.name}#{key.lower()}-" + titles[key].lower().replace(" ", "-"), "状态": "待执行", "验收状态": "未验证", "run_id": "", "batch_id": "", "开始时间": "", "完成时间": "", "证据路径": "", "阻塞引用": "", "下一动作": "按专项计划本节执行"} for key, value in TASKS.items()]
    write_initial_csv(HERE / "执行清单.csv", list(task_rows[0]), task_rows)
    for name, fields in TEMPLATES.items():
        write_initial_csv(HERE / "模板" / name, fields, [])


def check() -> dict:
    previous_manifest = json.loads((HERE.parent / "round-4" / "哈希记录.json").read_text(encoding="utf-8-sig"))
    for record in previous_manifest["files"]:
        previous_path = ROOT / record["file"]
        assert hashlib.sha256(previous_path.read_bytes()).hexdigest() == record["sha256"], record["file"]
    rows = read_rows(HERE / "源对象执行台账.csv")
    initial = [row for row in rows if row["source_key"].startswith("srd339:")]
    assert len(initial) == 339
    assert len({row["source_key"] for row in rows}) == len(rows)
    created = sum(int(row["基线对象份数"]) > 0 for row in initial)
    assert created == 209
    assert sum(int(row["基线对象份数"]) for row in initial) == 212
    original_sql_failures = sum("原 SQL 试跑失败记录" in row["基线状态"] for row in initial)
    other_missing = sum("未在 SQL 失败清单" in row["基线状态"] for row in initial)
    assert original_sql_failures == 86 and other_missing == 44
    modules = read_rows(HERE / "模块迁移基线.csv")
    assert sum(int(row["源对象数"]) for row in modules) == 339
    assert sum(int(row["已建不同来源数"]) for row in modules) == 209
    assert sum(int(row["未覆盖来源数"]) for row in modules) == 130
    task_rows = read_rows(HERE / "执行清单.csv")
    assert {row["任务ID"] for row in task_rows} == set(TASKS)
    for row in task_rows:
        dependency, output, acceptance = TASKS[row["任务ID"]]
        assert (row["前置依赖"], row["预期输出"], row["验收要求"]) == (dependency, output, acceptance), row["任务ID"]
    for name, fields in TEMPLATES.items():
        with (HERE / "模板" / name).open(encoding="utf-8-sig", newline="") as handle:
            assert next(csv.reader(handle), []) == fields, name

    markdown_paths = [PLAN, *sorted(HERE.rglob("*.md"))]
    missing_links = []
    checked_links = 0
    for path in markdown_paths:
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8-sig")):
            target = target.strip("<>").split("#", 1)[0]
            if not target or re.match(r"[a-z]+://", target, flags=re.I):
                continue
            # 检查本计划包中的相对文件链接，不解释未来批次目录占位符。
            target_path = path.parent / unquote(target)
            checked_links += 1
            if not target_path.exists() and target_path.resolve() not in {HERE / "哈希记录.json", HERE / "计划包校验结果.json"}:
                missing_links.append({"file": str(path.relative_to(ROOT)), "target": target})
    assert not missing_links, missing_links

    report = {
        "性质": "离线计划包校验，不是业务/权限验收", "检查时间UTC": datetime.now(timezone.utc).isoformat(),
        "初始来源数": len(initial), "已建不同来源数": created, "初始图表对象数": 212, "未覆盖来源数": 339 - created,
        "原SQL失败记录数": original_sql_failures, "其他未覆盖数": other_missing,
        "模块数": len(modules), "阶段数": 10, "步骤数": len(task_rows), "CSV模板数": len(TEMPLATES),
        "本地链接检查数": checked_links, "缺失链接": missing_links,
        "前轮冻结文件核验数": len(previous_manifest["files"]), "前轮冻结文件未改变": True,
        "步骤状态统计": dict(Counter(row["状态"] for row in task_rows)),
        "结果": "通过", "生产迁移执行": False, "业务一致性已验证": False, "人员赋权已执行": False,
    }
    (HERE / "计划包校验结果.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def freeze() -> None:
    hash_path = HERE / "哈希记录.json"
    if hash_path.exists():
        raise FileExistsError("初始哈希已存在，后续执行应在新批次记录哈希，拒绝覆盖")
    paths = [PLAN, *sorted(path for path in HERE.rglob("*") if path.is_file() and "__pycache__" not in path.parts)]
    manifest = {"轮次": "round-5", "性质": "初始计划交付冻结，非生产验收", "生成时间UTC": datetime.now(timezone.utc).isoformat(), "算法": "sha256", "文件": []}
    for path in paths:
        data = path.read_bytes()
        manifest["文件"].append({"路径": str(path.relative_to(ROOT)).replace("\\", "/"), "字节数": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    hash_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只校验已有台账，更新本轮计划包校验结果")
    parser.add_argument("--freeze", action="store_true", help="初次冻结哈希，已存在时拒绝覆盖")
    args = parser.parse_args()
    if not args.check:
        initialize()
    result = check()
    if args.freeze:
        freeze()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
