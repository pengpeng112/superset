**结论：方案抓住了主要决策，但还不能直接作为另一个 AI 的完整开发执行书。** 三个长任务、A+B 范围、旧对象三分类、用户自行赋权的方向正确；主要缺陷集中在范围映射、中文验收、迁移完整性和部署回退承诺。

本次仅进行了文件读取、统计、哈希核对和官方资料查证，未修改任何文件，也未连接生产执行操作。以下按重要程度列出发现。“总计划”指工作区的报表补迁 v2 权威计划。

1. **【高】“字段用中文”被降格为“允许英文交付”。**  
   方案明确允许无中文来源的列保留英文，最终只报告覆盖率。这不能完整满足用户“报表字段也是中文”的要求。不猜词是合理约束，但应将未确定中文的字段列为待完善项，补充来源、业务含义和中文命名依据；不能直接把英文兜底定义成完成。还应明确中文验收覆盖表格、筛选器、指标及导出列头。  
   出处：[方案第 52–56 行](/F:/python/superset/review/round-7/方案.md:52)、[任务 3](/F:/python/superset/review/round-7/方案.md:87)。

2. **【高】“46 个新对象需提取 SQL”是错误的任务数量口径。**  
   对 v4 清单实际统计，46 个“否”由 **27 个支撑对象、8 个窗口、11 个 dwo** 构成。支撑对象不都具有报表 SQL，窗口与其引用 dwo 又可能重复代表同一功能。因此 46 可以表示“未直接匹配现有提取集的对象行”，不能表示 46 条新报表 SQL。应分别统计需解析的对象、需恢复的查询和需新增的部署对象。  
   出处：[方案第 43–44 行](/F:/python/superset/review/round-7/方案.md:43)、[v4 清单](/F:/python/superset/migration/Q2在用勾选清单-v4.csv)。

3. **【高】“58 个源对象对应同 ID 覆盖”没有成立的证据。**  
   58 来自“直接命中 35＋引用命中 23”。实际其中是 **35 个 dwo 直接命中、22 个窗口引用命中、1 个 dwo 引用命中**。这些行存在依赖重叠；“在 339 提取集”也不证明它已部署到生产。不能据此认定存在 58 个可覆盖旧对象，更不能用它计算退役量。必须建立来源对象到生产 dataset/chart ID、UUID 的逐项映射。  
   出处：[方案第 44 行](/F:/python/superset/review/round-7/方案.md:44)、[覆盖分类](/F:/python/superset/review/round-7/方案.md:96)、[v4 清单](/F:/python/superset/migration/Q2在用勾选清单-v4.csv)。

4. **【高】A+B 的依赖闭包缺失，存在漏迁和误退役风险。**  
   仅按清单已有引用列去重，就发现至少 8 个被 A+B 引用、但不属于 A+B 104 行的 dwo：`d_adis_count`、`d_dept`、`d_dept_dict`、`d_stat_dept_plsx`、`d_tjbb_2`、`d_tjbb_mz`、`d_tjbb_zy`、`d_tjbb_zy_row`。应明确“104 是选择范围，必要依赖随所选功能迁移”，否则执行者可能遗漏这些依赖，或将其生产对象归为范围外退役。  
   出处：[v4 清单](/F:/python/superset/migration/Q2在用勾选清单-v4.csv)、[方案范围定案](/F:/python/superset/review/round-7/方案.md:104)、[退役分类](/F:/python/superset/review/round-7/方案.md:97)。

5. **【高】104 个对象尚未形成完整、可核销的处置台账。**  
   “约 32 个报表单元”没有逐项推导，也没有定义什么构成一个单元。任务 1 可以负责最终定稿，但应预先要求：104 行各有唯一处置状态，映射到功能、依赖、归并对象或排除依据；每个有效入口及参数分支均能追踪到交付物。不能以“做出了约 32 张报表”代替范围完成证明。  
   出处：[方案第 47 行](/F:/python/superset/review/round-7/方案.md:47)、[任务 1](/F:/python/superset/review/round-7/方案.md:85)、[总计划完成定义](/F:/python/superset/superset-报表补迁与一致性验收及人员赋权长任务计划-v2-多方互查修订版.md:45)。

6. **【高】“共用同一主 dw 就归并”不足以证明功能等价。**  
   同一 dw 可能被不同窗口用不同 Retrieve 参数、过滤、计算、统计级别或打印布局调用。清单中也有标题相同的多个月报窗口。归并必须依据业务版本、调用链和有效参数分支，保留原入口到新功能的映射；不能只按 dw 名或中文标题合并。  
   出处：[方案第 47 行](/F:/python/superset/review/round-7/方案.md:47)、[v4 清单](/F:/python/superset/migration/Q2在用勾选清单-v4.csv)、[总计划功能键要求](/F:/python/superset/superset-报表补迁与一致性验收及人员赋权长任务计划-v2-多方互查修订版.md:247)。

7. **【高】旧对象三分类的数量、集合和对象类型没有闭合。**  
   保留栏列出的图表 1–5 与 7–14 合计是 **13 张**，不是约 15 张；退役公式中的 212 已包含 307/308/309 三个重复对象，再额外加 3 会重复计算；13 个看板又混入“约 250 图表”的表述。应分别对图表、数据集、看板建立互斥且穷尽的 ID 集合，再生成精确数量。  
   出处：[方案三分类表](/F:/python/superset/review/round-7/方案.md:95)、[总计划现网基线](/F:/python/superset/superset-报表补迁与一致性验收及人员赋权长任务计划-v2-多方互查修订版.md:80)。

8. **【高】看板 4–6 没有归入任何处置类别。**  
   方案保留看板 1–3、退役看板 7–19，遗漏源库批看板 4、5、6。已有快照显示它们分别引用 3、50、30 张图表，关联均为 0。即使其图表全部退役，看板也必须明确处置，否则仍留下旧入口和布局引用。  
   出处：[方案第 95–97 行](/F:/python/superset/review/round-7/方案.md:95)、[生产元数据刷新快照的 dashboards 数组](/F:/python/superset/migration/sources/20261007-073508/生产元数据刷新.json)。

9. **【高】“保留看板 3 原样不动、已验收/发布中”与现场证据不符。**  
   快照显示看板 3 未发布、关联为 0，布局含核心 8 张图表；病案看板 1 也未发布。因此可以保护核心图表 SQL 和已有权限，但不能据此将看板 3 的入口认定为已完成。应区分“保护口径不改”和“布局/关联是否需要修复”。  
   出处：[方案保留分类](/F:/python/superset/review/round-7/方案.md:95)、[生产元数据刷新快照](/F:/python/superset/migration/sources/20261007-073508/生产元数据刷新.json)、[总计划附录 C](/F:/python/superset/superset-报表补迁与一致性验收及人员赋权长任务计划-v2-多方互查修订版.md:839)。

10. **【高】“本批不迁”被扩大解释为“不会再用”。**  
    用户确定的是 A+B 本批迁移、C 本批不迁；这不等于所有范围外资源永久无用。三分类处置已经获准，无须重新询问，但每个退役对象仍应依据所属批次、依赖关系、现有引用和保护清单判断，不能仅凭不在 A+B 名单便退役。  
    出处：[范围记录](/F:/python/superset/review/round-7/方案.md:34)、[退役理由](/F:/python/superset/review/round-7/方案.md:97)。

11. **【高】生产退役早于浏览器功能验收，顺序存在风险。**  
    任务 2 已执行软退役，任务 3 才逐报表做浏览器验证。一旦任务 3 发现筛选、显示或导出不可用，旧资源已先被处置。应在任务 2 每个批次内完成最低限度的浏览器功能验证和回退准备，再退役对应旧对象；任务 3 负责全量汇总验收。仍可保持三个长任务。  
    出处：[任务 2、3](/F:/python/superset/review/round-7/方案.md:86)、[总计划批次循环](/F:/python/superset/superset-报表补迁与一致性验收及人员赋权长任务计划-v2-多方互查修订版.md:648)。

12. **【高】复杂 compute 仅“登记差异”，会允许缺少必需指标的报表被算作迁好。**  
    无旧基准可以标未验证交付，不代表可以省略已知计算逻辑。应区分纯格式表达式与业务必需指标，对后者还原分子分母、分组、舍入、空值和处理顺序；无法实现的列为功能缺项。“简单合计迁 SQL 聚合列”也必须验证是否改变明细粒度。  
    出处：[方案第 78 行](/F:/python/superset/review/round-7/方案.md:78)、[总计划 PB 语义要求](/F:/python/superset/superset-报表补迁与一致性验收及人员赋权长任务计划-v2-多方互查修订版.md:399)、[发布候选验收](/F:/python/superset/superset-报表补迁与一致性验收及人员赋权长任务计划-v2-多方互查修订版.md:443)。

13. **【高】参数从试跑进入 Superset 实际页面的实现路径没有分解清楚。**  
    方案写了 DATE 绑定和参数恢复，但没有明确窗口参数默认值、必填、全选哨兵、下拉字典、动态 SQL 分支，如何接入原生过滤器、模板和图表查询。开发 AI 很可能做到“Python 能执行 SQL”，却没有可用的用户参数入口。应在任务 1 定稿参数契约，任务 2 实现并验证实际页面查询。Superset 模板上下文及参数机制见[官方 6.1.0 文档](https://superset.apache.org/admin-docs/6.1.0/configuration/sql-templating/)。  
    出处：[技术路径](/F:/python/superset/review/round-7/方案.md:64)、[覆盖更新内容](/F:/python/superset/review/round-7/方案.md:96)、[总计划参数恢复](/F:/python/superset/superset-报表补迁与一致性验收及人员赋权长任务计划-v2-多方互查修订版.md:386)。

14. **【高】“样板 13/14 通过”只能证明有限技术试跑，不能证明参数和业务逻辑恢复。**  
    当前试跑脚本把所有绑定参数设为 `None`，最多取 5 行。这样的测试可以发现部分语法、类型和访问错误，却可能让实际应有数据的报表返回空集，也没有验证真实参数下的负载。任务 1 应加入合法参数、有业务时期、边界日期、空结果及必要分支用例，保留这些用例供页面验证复用。  
    出处：[方案第 64 行](/F:/python/superset/review/round-7/方案.md:64)、[试跑脚本第 67 行](/F:/python/superset/migration/tools/p4_sample_trial.py:67)、[执行进度记录“技术试跑 13、对账 0”](/F:/python/superset/migration/执行进度.md:31)。

15. **【高】“SQL 提取已验证”的证据不足以支持“全部复用已验证组件”。**  
    已读取的两个取证 JSON 中，`d_jzfz_2024.dwo` 的“内嵌SQL样例”为空；相关窗口确实有 SQL 片段，但保存结果被截到 260 字符。`pbl_full_parse.py` 主要解析对象目录、窗口文本和引用，也不是完整查询语义提取器。不能据此认定提取不可能，但方案需补出完整 SQL 所在文件、来源版本、长度/哈希及校验结果，并把提取器补全明确列入任务 1。  
    出处：[方案第 44、63 行](/F:/python/superset/review/round-7/方案.md:63)、[近期取证 JSON](/F:/python/superset/migration/batches/近期修改对象取证.json)、[样例截断代码](/F:/python/superset/migration/tools/pbd_recent_extract.py:105)、[全量解析器说明](/F:/python/superset/migration/tools/pbl_full_parse.py:3)。

16. **【高】部署工具没有落实方案依赖的“变更前对象哈希未漂移”保护。**  
    `deploy_batch` 的 `--plan-hash` 校验的是批次定义文件，更新对象时没有比较预期旧对象哈希。持锁只能防遵守同一锁契约的程序，不能代替人工修改冲突检测。因此可能覆盖 dry-run 后发生的有效编辑。应将旧对象指纹、保护对象排除、冲突退出及对象级快照作为任务 2 的前置要求。  
    出处：[方案部署与安全承诺](/F:/python/superset/review/round-7/方案.md:66)、[部署工具更新分支](/F:/python/superset/migration/tools/deploy_batch.py:119)、[批次文件哈希检查](/F:/python/superset/migration/tools/deploy_batch.py:191)、[总计划同 ID 更新要求](/F:/python/superset/superset-报表补迁与一致性验收及人员赋权长任务计划-v2-多方互查修订版.md:434)。

17. **【高】现有失败回退链不能覆盖“已写入但读回失败”的对象。**  
    更新分支在写入前只把 `before` 放在内存，成功读回后才记入台账；写入成功但读回失败时，失败记录没有恢复字段。回退工具又只选择终态成功记录，会漏掉此类已变更对象。应在首次写入前持久化快照，并按“可能已写入”处理超时、异常和读回失败。  
    出处：[部署工具第 124–143 行](/F:/python/superset/migration/tools/deploy_batch.py:124)、[回退工具选择记录](/F:/python/superset/migration/tools/rollback_batch.py:48)、[总计划 G5](/F:/python/superset/superset-报表补迁与一致性验收及人员赋权长任务计划-v2-多方互查修订版.md:165)。

18. **【高】现有回退工具可能硬删不属于本批创建的对象。**  
    `skipped_exists` 被列为 DONE；回退工具对 DONE 中 `action=create` 的记录一律生成删除操作，没有区分“本批新建”与“原已存在、此次跳过”。此外，图表引用检查用“看板 ID 等于图表 ID”查询，并未检查真实图表—看板关系，数据集则直接返回引用数 0。方案不能把这一组件当作已可靠的生产回退基础。  
    出处：[DONE 定义](/F:/python/superset/migration/tools/lib/core.py:95)、[创建查重记录](/F:/python/superset/migration/tools/deploy_batch.py:97)、[回退删除计划](/F:/python/superset/migration/tools/rollback_batch.py:50)、[引用检查](/F:/python/superset/migration/tools/rollback_batch.py:27)。

19. **【中高】断点续作缺少不同部署对象的唯一键约定。**  
    `--resume` 只按 `source_key` 查终态。如果同一来源键用于数据集、图表和看板，后续项可能被错误跳过；台账也没有用计划哈希判定旧终态是否仍适用于新定义。应规定键至少区分业务功能、目标 kind 和操作版本，并明确失败后重跑及变更计划后的续作规则。  
    出处：[方案断点续作承诺](/F:/python/superset/review/round-7/方案.md:66)、[部署工具续作分支](/F:/python/superset/migration/tools/deploy_batch.py:219)、[台账检索实现](/F:/python/superset/migration/tools/lib/core.py:107)。

20. **【中高】现有软退役工具与中文前缀及幂等承诺不符。**  
    方案要求 `[已退役]`，工具实际生成 `[RETIRED 批次]`；非 resume 重跑会再次叠加前缀，且截断到 200 字符，不能保证仅凭现名恢复。应明确中文前缀、重复执行不再改名、原名持久保存、按对象类型验证名称长度。  
    出处：[方案退役要求](/F:/python/superset/review/round-7/方案.md:97)、[工具软退役分支](/F:/python/superset/migration/tools/deploy_batch.py:146)。

21. **【中高】按中文名称查重的工具有确定缺陷。**  
    `rison_q()` 用 `set("…\u4e00-\u9fff")` 表示中文范围，实际只加入两个端点字符和横线，常见汉字并不在允许集合内。因此用中文 `slice_name` 或 `dashboard_title` 匹配会抛错。可采用稳定 ID 映射，但新对象查重仍须有可靠实现；这应列入开发前工具修补。  
    出处：[中文命名要求](/F:/python/superset/review/round-7/方案.md:34)、[名称匹配路径](/F:/python/superset/migration/tools/deploy_batch.py:47)、[字符白名单实现](/F:/python/superset/migration/tools/lib/superset_api.py:27)。

22. **【中高】现有口径卡编译工具没有实际生成部署定义。**  
    `--check-only` 设置 `default=True` 且没有关闭入口，程序始终走校验分支；即便进入另一分支，也只是输出原 spec 和检查结果，没有生成 dataset/chart payload。compute 只记 warning，也未落实注释承诺的 metrics 校验。任务 1 的“dry-run 就绪”因此还需要明确的编译/生成开发工作，不能只靠现组件复用。  
    出处：[任务 1 产出](/F:/python/superset/review/round-7/方案.md:85)、[编译工具参数](/F:/python/superset/migration/tools/compile_report.py:74)、[输出分支](/F:/python/superset/migration/tools/compile_report.py:118)。

23. **【中高】缺少中文显示字段与稳定机器字段的明确实施契约。**  
    方案只有中文来源优先级，没有说明怎样更新显示名、计算指标、表格列标签和导出标题，也未要求同步核查过滤器及 query_context 引用。应沿用总计划“机器字段稳定、中文显示名对齐”的方式。Superset 6.1.0 数据集接口具有列和指标的 `verbose_name` 字段，可作为实现依据。  
    出处：[方案中文化部分](/F:/python/superset/review/round-7/方案.md:49)、[总计划字段整改](/F:/python/superset/superset-报表补迁与一致性验收及人员赋权长任务计划-v2-多方互查修订版.md:434)、[官方 6.1.0 数据集接口源码](https://github.com/apache/superset/blob/6.1.0/superset/datasets/api.py)。

24. **【中高】“不发布”可以作为交付状态，但不能作为访问隔离证明。**  
    用户自行赋权的口径应保留，不需要恢复全员授权迁移。但方案至少应交付每个资源的现有访问状态和明确授权步骤，并验证迁移没有扩大访问。官方 6.1.0 源码明确：常规 RBAC 路径不统一检查 published，图表也有独立数据集访问路径。不能把“未发布”写成唯一隔离措施。  
    出处：[方案权限处理](/F:/python/superset/review/round-7/方案.md:69)、[总计划已有提醒](/F:/python/superset/superset-报表补迁与一致性验收及人员赋权长任务计划-v2-多方互查修订版.md:517)、[官方 6.1.0 权限实现](https://github.com/apache/superset/blob/6.1.0/superset/security/manager.py#L2481-L2526)。

25. **【中】Q3 与总计划门禁的覆盖关系没有写清。**  
    未发布等待用户赋权，有执行进度第 22 行支持，不能仅凭 Q3“照常发布”就要求现在无角色发布。但方案又说“门禁以总计划为准”，而总计划 G2 要求独立旧基准。应明确：Q3 仅豁免缺少独立旧基准造成的交付阻塞，仍保留功能、参数、负载和回退验收；“已交付”“待用户赋权”“旧一致性未验证”分别记录。  
    出处：[方案优先级声明](/F:/python/superset/review/round-7/方案.md:25)、[Q3 处理](/F:/python/superset/review/round-7/方案.md:68)、[用户自行赋权记录](/F:/python/superset/migration/执行进度.md:22)、[总计划 G2](/F:/python/superset/superset-报表补迁与一致性验收及人员赋权长任务计划-v2-多方互查修订版.md:162)。

26. **【中】不能把“所有报表都无旧基准”作为永久前提。**  
    登录未恢复不代表没有冻结样本或其他独立参考。对能取得的基准仍应进行比对；缺基准者按用户决定标未验证交付。标记还应落到用户可见的报表说明和交接台账，而不只是单独交一份未验证清单。  
    出处：[方案对账行](/F:/python/superset/review/round-7/方案.md:68)、[任务 3](/F:/python/superset/review/round-7/方案.md:87)、[总计划参考证据优先级](/F:/python/superset/superset-报表补迁与一致性验收及人员赋权长任务计划-v2-多方互查修订版.md:327)。

27. **【中】归并、排除和标题净化尚有具体遗漏。**  
    “备份版 3”没有给出三个对象及各自 canonical 映射；同类清单还有 `d_tjbb_zy_new_210304`、`d_tjbb_zy_new_191213`，不能仅凭后缀决定废弃。`w_main` 是程序自动更新窗口、`w_pbf_wait` 是进度窗口，也不应纳入报表单元。三个异常窗口标题已有较清晰的文本样例，但 `w_exam_person_performed` 同时出现门诊和住院分支，净化一个标题不能替代分支核查。  
    出处：[方案剔除规则](/F:/python/superset/review/round-7/方案.md:45)、[标题净化规则](/F:/python/superset/review/round-7/方案.md:51)、[v4 清单具体行](/F:/python/superset/migration/Q2在用勾选清单-v4.csv:27)。

28. **【中】任务验收偏重“有文件、有截图”，缺少可执行的通过标准。**  
    应在三个长任务内部明确：输入版本和哈希、对象映射完整性、必需参数/指标、真实查询成功、页面筛选、结果截断、合计和导出完整性、失败修复与重验、不可实现项状态。旧基准缺失可以例外交付，技术查询失败或已知功能缺失则不能一并标成“旧一致性未验证”。  
    出处：[三个任务验收列](/F:/python/superset/review/round-7/方案.md:85)、[总计划完成定义](/F:/python/superset/superset-报表补迁与一致性验收及人员赋权长任务计划-v2-多方互查修订版.md:49)、[大明细双轨要求](/F:/python/superset/superset-报表补迁与一致性验收及人员赋权长任务计划-v2-多方互查修订版.md:670)。

29. **【中】“原文照录”的审查来源声明不真实。**  
    round-7 方案新增独立“旧对象三分类”章节，并改写计划关系；当前活动文档没有该章节，仍保留旧 T1–T10 对应关系。活动文档实际 SHA256 为 `ee694ef5…5289e`，与所引冻结记录一致。因此冻结哈希证明的是当前活动文档，不能证明 round-7 后半部分是其逐字副本。应将方案标为拟修订稿，列出相对冻结版本的修改。  
    出处：[照录声明](/F:/python/superset/review/round-7/方案.md:26)、[方案新增章节](/F:/python/superset/review/round-7/方案.md:91)、[活动文档末章](/F:/python/superset/migration/AB迁移分析与任务分解.md:60)、[冻结记录](/F:/python/superset/migration/冻结快照/P1批次哈希.json:133)。

30. **【中】三任务改版没有彻底消除旧任务编号及交接歧义。**  
    方案仍出现 T1、T2、T3、T10；活动进度仍写“执行 T1”触发。新“任务 2”是生产部署，旧 T2 则是资产分析，这种歧义会直接影响另一 AI 的执行顺序。交接版应统一三个任务的编号，并给出每任务输入、输出路径、前置条件和恢复检查点。“不中途请示”可保留，但应说明技术失败暂停相关项、继续独立项，不能理解为失败也继续写入。  
    出处：[方案旧编号残留](/F:/python/superset/review/round-7/方案.md:75)、[执行约定](/F:/python/superset/review/round-7/方案.md:89)、[活动进度](/F:/python/superset/migration/执行进度.md:8)。

31. **【中】截图证据与工作量预算缺少必要限定。**  
    截图应遵守总计划已有患者信息约束，采用脱敏、空白结构或受控存储，不能直接把患者明细放入交接包。总计 6–7 天的预算也尚未涵盖依赖补解析、工具修补、参数页面开发及复杂计算实测；宜标为初估，并在任务 1 结束后按真实报表单元和复杂度重估。  
    出处：[任务 3 截图要求及工期](/F:/python/superset/review/round-7/方案.md:87)、[总计划截图约束](/F:/python/superset/superset-报表补迁与一致性验收及人员赋权长任务计划-v2-多方互查修订版.md:321)、[总计划实测后重估要求](/F:/python/superset/superset-报表补迁与一致性验收及人员赋权长任务计划-v2-多方互查修订版.md:173)。
