这份方案**覆盖了用户点名的主要维度，但尚未完整满足“详细、可交给另一个 AI 一次性执行的 MD 计划”要求**。它目前更接近编制提纲，且现状基线明显落后于已有证据。直接据此生成执行计划，容易重复修复已完成事项，同时漏掉更重要的权限、同步和验收问题。

本次全程只读，未修改任何文件，也未上传脚本或操作生产。以下结论来自本地文档、配置、脚本和已有执行证据；涉及 Superset 通用行为，核对了官方 6.1.0 文档及源码。代码问题属于静态核查，未冒充生产复现。

1. **【阻断交付】方案承诺的执行计划尚未实际形成。**

   第 5 节只是说明以后要生成怎样的《一次性执行计划.md》，第 4 节仍是六组方向。没有任务编号、对象范围、具体步骤、依赖、命令、失败处理及逐项验收。因此，作为送审提纲可以理解；作为用户要求的最终执行文件，尚不合格。

   出处：[方案第 4—6 节](/F:/python/superset/review/round-11/方案.md:43)。

2. **【重要】没有回答“一次免费执行最值得用在哪里”。**

   对账、前端、性能、缓存、监控、打印、退役等全部并列，没有按收益、风险、证据充分程度和外部依赖排序，也没有定义最低必须完成的交付包。下一位 AI 仍须自行选题，免费额度可能耗在重新盘点或等待业务答复上。

   应确定一个可独立完成的核心包，其他事项按优先级递补；外部依赖形成具体材料后跳过，不阻塞整个执行。

   出处：[方案改进维度](/F:/python/superset/review/round-11/方案.md:45)；已有计划已经区分“可完成包”和“外部依赖工单包”，见[生产改进计划](/F:/python/superset/migration/生产系统改进长任务计划-v1-多方互查修订版.md:10)。

3. **【重要】只读规划与后续实施的边界混在一起。**

   第 2 节禁止修改配置、角色和权限，第 5 节又安排“备份→低风险修复→需授权项”。没有明确这些约束分别针对编制者还是接手执行者。“低风险”也不能自动代替实施范围。

   当前只读审查约束应继续遵守；最终计划则须明确用户以后交付执行指令时，哪些工作可以连续推进，哪些动作仍按既有发布、赋权、业务库变更红线处理。

   出处：[方案边界](/F:/python/superset/review/round-11/方案.md:16)、[产出物](/F:/python/superset/review/round-11/方案.md:52)。

4. **【高】关键现状没有落实到可核查的证据入口。**

   §3 声称“起草者掌握，供审查方核实”，但多数数字、状态及问题没有对应文件、采集时刻或运行批次。“已登记差异”“发布清单已在交接包”等写法仍要求执行者重新寻找依据，未达到“不依赖口头交接”。

   应逐项记录来源、证据日期、适用对象及状态，明确 ✅已完成、❌待完成、存疑待证。

   出处：[方案现状摘要](/F:/python/superset/review/round-11/方案.md:23)、[自身验收标准](/F:/python/superset/review/round-11/方案.md:59)。

5. **【高】“不推翻重查”写得过于绝对，可能阻止必要的现场刷新。**

   避免重复劳动是对的，但归档结论不能替代最新状态。当前工作区已经有多次“原结论被后续取证纠正”的案例。应复用历史证据，同时在开工时检查定义、配置、权限和来源是否漂移；发生漂移或证据相互矛盾时允许针对性复查。

   出处：[方案第 19 行](/F:/python/superset/review/round-11/方案.md:19)；[目录索引明确要求开工刷新](/F:/python/superset/目录索引.md:163)。

6. **【高】此前任务完成情况没有形成真正的对账表。**

   方案提到 AB、九报表、同步和兼容层，却没有将既有任务逐项映射为“已完成、需复验、仍缺项、外部阻塞、已被后续方案取代”。尤其没有处理生产改进计划 P1—P21、批 A—G 的剩余项。

   用户明确要求看“之前的任务完成情况”，应交付任务状态矩阵，而不能仅列几个批次名称。

   出处：[方案目标](/F:/python/superset/review/round-11/方案.md:11)；[既有改进问题清单](/F:/python/superset/migration/生产系统改进长任务计划-v1-多方互查修订版.md:29)。

7. **【高】对象数量缺少当前基线。**

   329 图表、328 数据集、29 看板是九报表实施前的 AB 终态。后续 EXEC 新建对象，COMPAT 记录的终态为 **332 图表、334 数据集、29 看板**。方案虽然将 329/328 标为 AB 批次，但没有给出后续总量，接手者容易把历史数量当开工检查标准。

   出处：[方案第 31 行](/F:/python/superset/review/round-11/方案.md:31)；[执行进度第 29 行](/F:/python/superset/migration/执行进度.md:29)。

8. **【高】九报表对账现状严重过时。**

   方案仍称仅 Z01 部分指标、Z05 对账，继续列出 Z01 转入 +1、H01 日期偏移等问题。后续 COMPAT 已按原口径修复，当前记录是 **8/9 原 SQL＋公式完整通过，H03 部分通过**；v5 同窗复核又验证了手术两个分支、检查和床旁结算。

   原 SQL 重放通过仍不等于独立旧客户端验收，应保留这一区别。继续把 EXEC 遗留项安排为待修，会浪费额度，并可能破坏后续修复。

   出处：[方案第 32、45 行](/F:/python/superset/review/round-11/方案.md:32)；[当前九行状态表](/F:/python/superset/migration/batches/质控护理九报表/交接包/9行状态表-20261011-COMPAT.md:7)；[同窗复核进度](/F:/python/superset/migration/执行进度.md:17)。

9. **【高】遗漏了九报表真正剩余的关键缺口：H03。**

   应明确列出普通护理列的原运行时减法证据、两个附区标题及旧客户端实际输出验收。现有证据只支持 468 个主指标单元和 34 项附区指标，不能概括为护理日报全表通过。

   另一个容易误改的细节是：原程序护理级别、呼吸机查询取昨日快照，流量取所选日期。不能为了日期“统一”擅自改变这一语义。

   出处：[当前状态表 H03](/F:/python/superset/migration/batches/质控护理九报表/交接包/9行状态表-20261011-COMPAT.md:15)；[COMPAT 报告第 53 行](/F:/python/superset/migration/batches/质控护理九报表/交接包/原口径修复与对账报告-20261011-COMPAT.md:53)。

10. **【高】“当前长表 vs 旧交叉表”的描述已被后续实施修正。**

    Z06 已恢复动态交叉表和合计，图表 283 使用 `pivot_table_v2`。真正剩余的是浏览器呈现、旧客户端比对和导出版式；服务端 CSV 是底层记录，并未证明与旧打印矩阵相同。

    出处：[方案前端方向](/F:/python/superset/review/round-11/方案.md:47)；[COMPAT 图表调整](/F:/python/superset/migration/batches/质控护理九报表/交接包/原口径修复与对账报告-20261011-COMPAT.md:57)、[交接限制](/F:/python/superset/migration/batches/质控护理九报表/交接包/原口径修复与对账报告-20261011-COMPAT.md:76)。

11. **【高】beat 根因已经修复，方案仍安排重新诊断。**

    10 月 12 日已查明 `beat_schedule.schedule` 错写字符串，改为 Celery `crontab`，只重建 beat；重启计数归零，调度文件持续更新。当前没有定时报告。

    后续任务应是持续运行和调度健康复验，不能继续沿用旧“celery --app 参数”根因，也不能把容器重建后的运行时间短本身当故障。

    出处：[方案运维方向](/F:/python/superset/review/round-11/方案.md:50)；[10 月 12 日修复记录](/F:/python/superset/migration/执行进度.md:7)；[当前配置](/F:/python/superset/offline-bundle/config/superset_config.py:61)。

12. **【高】用户同步必须区分已修项与尚待运行验证项。**

    RLS 翻页、dry-run 写入、422 误计成功三项已修并上传；只读复验已获取 335/335 规则，但尚未重跑完整同步，下一次真实验证依赖 06:00 cron。

    方案只有“同步失败告警”，遗漏了这次修复的验收闭环：真实运行退出码、失败统计、重复 RLS、用户及角色变化、保护对象是否变化。

    出处：[方案第 50 行](/F:/python/superset/review/round-11/方案.md:50)；[最新同步修复记录](/F:/python/superset/migration/执行进度.md:8)。

13. **【中】“浏览器 UI 渲染复验未做”缺少对象和版本限定。**

    九报表完整页面验收确实尚未完成，但系统整体已有 AB 七组看板、病案日期筛选、员工改密的 Chromium 87 实测；10 月 12 日还复验了看板 33，并观察多个看板能够打开出数。

    应明确哪些对象未验、哪些只做冒烟、哪些完成交互闭环。新版浏览器空网格仍是待查，不能当已复现故障处理。

    出处：[方案第 37 行](/F:/python/superset/review/round-11/方案.md:37)；[AB 浏览器记录](/F:/python/superset/migration/执行进度.md:160)、[改密验收](/F:/python/superset/migration/执行进度.md:79)、[最新体检](/F:/python/superset/migration/执行进度.md:9)。

14. **【高】未处理历史 v5 对账脚本会产生误导结果的问题。**

    原 v5 使用历史 CSV，只剔除“总计”而未剔除“合计”，按名称归并、把缺失和 NULL 当零，并允许数量容差。原样重跑仍有差异，但新采集同窗严格比较四项全部通过。

    计划中的“自动化对账脚本入库”必须规定采用哪套比较规则、如何自检，不能把历史脚本直接固化为回归标准。

    出处：[方案测试方向](/F:/python/superset/review/round-11/方案.md:49)；[v5 重跑报告](/F:/python/superset/migration/batches/质控护理九报表/交接包/v5重跑对账-20261011.md:18)。

15. **【高】遗漏 HIS 数据范围隔离这一已有明确风险。**

    既有计划记录：335 条科室 RLS 全部挂在 ODS 科室字典，HIS 报表数据集没有因此自动得到科室隔离。方案只写“角色映射、范围”，没有要求逐报表声明全院汇总、科室汇总或患者明细，也没有规定在聚合前如何限制范围。

    应将数据范围确认及负向验证列为发布前任务。绑定看板角色主要解决访问入口；不能拿它替代行级数据范围控制。官方也明确，看板 RBAC 可绕过数据集访问检查、无角色时回退到数据集权限。

    出处：[既有 P4](/F:/python/superset/migration/生产系统改进长任务计划-v1-多方互查修订版.md:36)、[A1](/F:/python/superset/migration/生产系统改进长任务计划-v1-多方互查修订版.md:68)；[Superset 6.1.0 官方权限说明](https://superset.apache.org/admin-docs/6.1.0/security/)。

16. **【高】遗漏筛选值安全引用与请求篡改测试。**

    旧参数化生成器明确以“页面枚举、代码域无单引号”为理由不做转义；另一个生成器直接把 `filter_values` 首值包进 SQL 引号。页面下拉限制不能证明直接 API 请求安全。

    应先从当前生产读回筛选模板，确定受影响对象，再做安全引用、值域及非法请求拒绝验证；目前证据支持“存在风险生成路径”，尚不能宣称所有生产报表都可利用。6.1.0 官方源码提供了按数据库方言生成字面量的 `where_in` 实现。

    出处：[旧生成器说明](/F:/python/superset/migration/tools/ab_t2_param_sql.py:8)、[直接拼接函数](/F:/python/superset/migration/tools/ab_t3_ph3b_param.py:58)；[既有 A0](/F:/python/superset/migration/生产系统改进长任务计划-v1-多方互查修订版.md:67)；[官方 6.1.0 模板源码](https://raw.githubusercontent.com/apache/superset/6.1.0/superset/jinja_context.py)。

17. **【高】同步脚本仍有三项未解决的身份生命周期问题。**

    本地当前代码显示：

    - 在职源用户若被人工停用，同步仍会写回 `active=True`，没有区分人工冻结与离职停用。
    - 用户工号从源表物理消失后，因为不在 `all_codes`，会被跳过，不能因此停用。
    - 没有源数据完整性门禁；在职集合异常为空、全体工号集合仍正常时，会进入批量停用路径。

    这三项应安排离线模拟和生产副本核对，不能因前述三项修复完成而报告“同步已全部完善”。

    出处：[在职用户更新](/F:/python/superset/offline-bundle/scripts/superset_user_sync.py:368)、[停用逻辑](/F:/python/superset/offline-bundle/scripts/superset_user_sync.py:389)、[主流程](/F:/python/superset/offline-bundle/scripts/superset_user_sync.py:502)；[既有 E2](/F:/python/superset/migration/生产系统改进长任务计划-v1-多方互查修订版.md:95)。

18. **【高】遗漏 SQL Lab 权限审计。**

    既有计划明确要求检查动作、资源、角色、数据库及 `sql_lab` 成员。方案只围绕九报表授权，未安排验证员工是否还能通过 SQL Lab、相关 API 或其他数据库权限取得超出报表范围的数据。

    不应预设已有越权，也不应未经审计直接收敛成“只有 Admin”；应先形成实际权限矩阵和负向结果。

    出处：[既有 D2](/F:/python/superset/migration/生产系统改进长任务计划-v1-多方互查修订版.md:84)；[官方 SQL Lab 权限说明](https://superset.apache.org/admin-docs/6.1.0/security/)。

19. **【高】缓存规划缺少撤权生效和时间变化的验收。**

    方案提到缓存策略和缓存检查，却没有生效时限、旧会话/API token/数据缓存三路测试，也没有区分 Redis 各库用途。当前 db0/1 是相关缓存，db2 为筛选和 Explore 状态，db3/4 为 Celery broker/result，不能笼统清空 Redis。

    H03 含昨日快照，默认日期也会随时间变化，还应检查实际缓存超时与失效行为。不能直接把 `CACHE_CONFIG` 的 86400 秒当所有图表 TTL；官方规定图表、数据集、数据库配置可覆盖数据缓存默认值。

    出处：[方案 B、D](/F:/python/superset/review/round-11/方案.md:46)；[Redis 配置](/F:/python/superset/offline-bundle/config/superset_config.py:44)；[既有 E3](/F:/python/superset/migration/生产系统改进长任务计划-v1-多方互查修订版.md:96)；[官方缓存说明](https://superset.apache.org/admin-docs/6.1.0/configuration/cache/)。

20. **【高】权限与发布准备不能只覆盖九个业务功能。**

    既有改进计划登记了 11 张待发布看板，图表 324 还有 25/32/33 三个入口；另有孤儿图表和目录看板。九功能不等于九个独立访问资源。

    应生成当前“看板—图表—数据集—角色—数据范围”矩阵，验证共享图表入口同权、目录链接及直接请求。10 月 12 日普通员工无法打开相关看板的 404，也应作为当前状态证据，不能未经授权直接改成开放。

    出处：[方案第 41、48 行](/F:/python/superset/review/round-11/方案.md:41)；[既有 P1](/F:/python/superset/migration/生产系统改进长任务计划-v1-多方互查修订版.md:33)、[D1](/F:/python/superset/migration/生产系统改进长任务计划-v1-多方互查修订版.md:83)；[最新员工访问观察](/F:/python/superset/migration/执行进度.md:11)。

21. **【高】急诊分诊的修复链被简化，顺能预约两单元则完全遗漏。**

    急诊当前生产 SQL 是 `clinic_master` 探测语句，正式 `v_clinic_triage` SQL 尚未部署。即使视图获 SELECT 权限，页面也不会自动出现正式名单，还需要替换数据集 321 SQL并完成参数、列、图表及真实页面验收。

    顺能预约两个 MySQL 单元因连接未提供仍未部署，应列为独立外部依赖，准备好后续执行材料。

    出处：[方案功能方向](/F:/python/superset/review/round-11/方案.md:45)；[AB 阻塞清单第 1、2 项](/F:/python/superset/migration/batches/AB迁移/交接包/未验证与阻塞清单.md:9)。

22. **【中高】已有其他功能缺口未被明确纳入或排除。**

    至少包括 `d_zkzb_query` 除零边界、`d_1/d_2` 手术数据时点、`d_4` 再入院间隔参数、聚合报表页面改窗、出院列表科室筛选列，以及无看板入口图表。

    这些有具体对象和证据，比笼统的“部分月/跨年能力回归”更可执行。出院列表补筛选时必须保留服务端 fail-closed 范围，不能为了出数取消限制。

    出处：[AB 遗留清单](/F:/python/superset/migration/batches/AB迁移/交接包/未验证与阻塞清单.md:24)；[既有 B1、B2](/F:/python/superset/migration/生产系统改进长任务计划-v1-多方互查修订版.md:72)。

23. **【中】823 列中文名不能未经核对继续作为当前工作量。**

    AB 交接包登记 823 列；后续改进计划按新增映射改成 814，并要求以最新 CSV 为准；九报表实施之后又发生列调整。现有文档之间本来就存在快照差异。

    应核对当前待完善清单、已应用映射及在用字段优先级。执行要求还应继承用户“原表头一致、拒绝语义推断”的明确口径，未知项形成确认材料。

    出处：[方案第 33、45 行](/F:/python/superset/review/round-11/方案.md:33)；[既有 P8](/F:/python/superset/migration/生产系统改进长任务计划-v1-多方互查修订版.md:40)；[原表头要求](/F:/python/superset/migration/执行进度.md:107)。

24. **【高】把 `STAT_BEGIN/STAT_DATE` 混用当作统一改造目标，缺少业务依据。**

    字段名不同本身不证明错误。当前不同报表分别保留月窗、周窗、日报、原开区间及结束日 23:59:59；COMPAT 已通过接口半开范围换回原窗口边界。

    应统一参数契约和验证方法，逐表保留原业务语义。简单批量统一列名、日期谓词或默认月份，可能重新引入已修复的错窗问题。

    出处：[方案架构方向](/F:/python/superset/review/round-11/方案.md:46)；[COMPAT 日期契约](/F:/python/superset/migration/batches/质控护理九报表/交接包/原口径修复与对账报告-20261011-COMPAT.md:25)；[各报表筛选配置](/F:/python/superset/migration/sources/20261011-QC-NURSE-COMPAT/finish.py:46)。

25. **【高】性能与测试计划遗漏实际 Superset 查询链路的负载门禁。**

    QueryGate 只保护迁移工具的直接查询，不保护浏览器 `chart/data`、列 refresh 或筛选候选值查询，也不是跨进程并发控制。当前 web 有 4 个进程、每进程 8 线程，worker 并发为 2；这些配置不能证明源库负载受控。

    应分别验证工具查询和应用查询的限时、源端取消、串行测试方式及熔断后处理，避免同时加载多个重型看板。性能优化也须继承禁止擅自执行 `EXPLAIN PLAN`、业务 DDL 的红线。

    出处：[方案测试及性能方向](/F:/python/superset/review/round-11/方案.md:46)；[九报表计划对两条链路的明确区分](/F:/python/superset/migration/质控科与护理部9张报表迁移复核长任务生产计划-v1.1-执行复核修订版.md:266)；[compose 并发配置](/F:/python/superset/offline-bundle/compose/docker-compose.yml:65)。

26. **【高】“超 1000 行截断探测”不是完整的导出验收标准。**

    当前九报表图表上限已恢复 50000，QueryGate 默认最多抓取 200000 行。单纯查询成功、返回量等于上限或界面有分页，都不能证明结果完整。

    QueryGate 当前只执行 `fetchmany(max_rows)`，返回的是已抓取行数，没有截断标志。计划应按实际出口检查总量、触顶、分页、汇总和 JSON/CSV 一致性，采用有界额外一行探测等方法识别截断。

    出处：[方案第 49 行](/F:/python/superset/review/round-11/方案.md:49)；[QueryGate 抓取逻辑](/F:/python/superset/migration/tools/lib/query_gate.py:131)；[专项完整性要求](/F:/python/superset/migration/质控科与护理部9张报表迁移复核长任务生产计划-v1.1-执行复核修订版.md:272)。

27. **【高，代码问题】通用对账工具产生差异时会报错，还可能掩盖字段差异。**

    `reconcile_report.py` 的 Counter 键由 `row_key()` 返回元组，但差异摘要对键调用 `k.encode()`；只要产生差异元素，就会遇到元组没有 `.encode()` 的错误。

    此外，所有字符串都尝试转 Decimal，会把文本代码 `"001"` 与 `"1"` 归一；比较没有先检查双方列名和顺序，分组列缺失也被静默忽略。这些行为与严格保留原行键的对账要求存在冲突。

    应先修复并验证比较器，再将其列为通用验收依赖；需要差异样本和错误样本，不能只验证相等数据。

    出处：[字符串归一](/F:/python/superset/migration/tools/reconcile_report.py:31)、[列索引处理](/F:/python/superset/migration/tools/reconcile_report.py:55)、[差异摘要错误](/F:/python/superset/migration/tools/reconcile_report.py:78)。

28. **【高，代码问题】回退工具的引用检查查询了错误对象。**

    `rollback_batch.references()` 接收图表 ID，却在 dashboard 列表上过滤 `dashboard.id == chart_id`。这是两类对象的 ID 比较，没有检查该图表实际挂在哪些看板上；数据集则直接返回零引用。

    因此不能把现有函数当作“有引用就不删”的可靠门禁。回退前应验证真实关联、后续修改及恢复顺序，优先使用对应批次完整对象快照。

    出处：[错误引用检查](/F:/python/superset/migration/tools/rollback_batch.py:27)；[COMPAT 回退要求](/F:/python/superset/migration/batches/质控护理九报表/交接包/原口径修复与对账报告-20261011-COMPAT.md:78)。

29. **【高，测试证据风险】复用浏览器探针时必须禁用图表假数据分支。**

    `20261009-chrome87/cdp.py` 包含 Fetch 拦截：遇到 `/api/v1/chart/data` 会返回固定虚构 JSON，还可以替换静态资源。若照搬启动方式并启用该分支，截图有内容并不能证明生产查询、日期过滤或权限正确。

    计划应明确真实业务验收不启用此拦截，并保留真实请求、响应、控制台和页面证据。这个发现不意味着既有所有浏览器验收都是假数据；它说明复用工具必须检查运行方式。

    出处：[探针假响应分支](/F:/python/superset/migration/sources/20261009-chrome87/cdp.py:27)；[目录索引警示](/F:/python/superset/目录索引.md:110)。

30. **【中】前端任务没有形成可验收的交互规格。**

    “多行表头、打印版式、错误中文提示”仍不足以让执行者决定做成什么。应指定报表、浏览器、分辨率、宽表滚动、合计和空值呈现、打印方向及文件出口；对员工入口、无权限链接和目录页也应定义预期。

    Chrome 80/87 兼容层已经有 247 文件指纹和升级重建契约，应复用该机制。新版空网格先取证，不能未经复现改兼容分流。

    出处：[方案前端方向](/F:/python/superset/review/round-11/方案.md:47)；[兼容包说明](/F:/python/superset/offline-bundle/compat/README.md:16)；[既有前端任务](/F:/python/superset/migration/生产系统改进长任务计划-v1-多方互查修订版.md:100)。

31. **【高】“备份恢复月检”没有覆盖完整系统恢复，也忽略了备份脚本的失败产物问题。**

    当前脚本主要备份元库和 `secrets`，没有在同一流程中归档实际 `.env`、compose、配置、品牌、翻译和兼容资源。已有 pg_restore 零错误演练不等于恢复后能解密连接、保持权限并正确查询。

    脚本还直接写最终日期文件名：失败可能留下部分 dump，同日重跑会覆盖原文件。应规划临时文件成功后替换、完整性标识、恢复应用级验证及备份失败监测；私密材料继续放受控位置。

    出处：[备份脚本](/F:/python/superset/offline-bundle/scripts/pg_backup.sh:7)；[既有 E4 恢复范围](/F:/python/superset/migration/生产系统改进长任务计划-v1-多方互查修订版.md:97)。

32. **【高】缺少生产更新防误操作要求，尤其是初始化服务和配置副本差异。**

    当前 compose 仍含执行 `superset init` 的初始化服务，而工作区明确禁止在现有生产运行该命令。后续计划必须具体指定可重建的服务，防止执行者照搬完整启动流程。官方说明内置角色权限会在 `superset init` 时重新同步。

    另据目录索引，生产配置与本地副本并不完全相同，不能整文件覆盖；P2 旧哈希也不能核对 10 月 12 日已更新的配置和同步脚本。

    出处：[compose 初始化命令](/F:/python/superset/offline-bundle/compose/docker-compose.yml:53)；[目录索引更新约定](/F:/python/superset/目录索引.md:19)、[旧哈希提醒](/F:/python/superset/目录索引.md:175)；[官方角色同步说明](https://superset.apache.org/admin-docs/6.1.0/security/)。

33. **【中高】架构盘点没有覆盖当前明确的部署取舍和未完成验证。**

    当前公开入口是 HTTP，配置仍设 `SESSION_COOKIE_SECURE=False` 并注明 HTTPS 里程碑。方案的架构部分应评估这一现状、离线更新方式、单机故障恢复及实际健康检测，而非仅列缓存和模板统一。

    选型及部署计划还要求 Vastbase、SQL Server 等数据库验证；本方案聚焦 Oracle 系报表可以，但应声明哪些连接能力已有证据、哪些尚未验证，避免把当前 Oracle 成果扩展为整个数据平台全链路完成。

    出处：[当前 Cookie 配置](/F:/python/superset/offline-bundle/config/superset_config.py:84)、[HTTP 端口](/F:/python/superset/offline-bundle/compose/docker-compose.yml:90)；[选型验证要求](/F:/python/superset/superset-选型复核清单-v2-多方互查修订版.md:90)。

34. **【高】超大明细双轨只被列为“未做”，没有安排处置。**

    方案没有明确本次是否实施、选什么样板、如何复用权限、怎样真实分页和异步导出，以及任务隔离、取件复验、过期删除和审计。

    若免费执行预算不足，应明确交付到设计、接口或样板的哪一级，并如实保留未完成状态。提高 Superset 行上限或让信息科代导共享文件不能替代既定双轨要求。

    出处：[方案第 37 行](/F:/python/superset/review/round-11/方案.md:37)；[总计划大明细轨道](/F:/python/superset/superset-报表补迁与一致性验收及人员赋权长任务计划-v2-多方互查修订版.md:670)。

35. **【重要】没有把时间门禁和外部依赖设计成一次执行可以交接的结果。**

    次日 06:00 同步、长期运行观察、跨月结账、业务旧客户端验收及退役观察期，都不能靠一轮短执行立即完成。最终计划应规定：当场完成哪些动作，后续留下什么可执行检查、结果判据和责任交接，何时仍标“待观察”。

    停旧和硬删除仍应继承“全部在用功能完成后观察一个月、跨一次月末结账、另行审批”的已有口径。单项待证不应阻塞其他可完成任务。

    出处：[方案自身验收](/F:/python/superset/review/round-11/方案.md:57)；[同步待运行验证](/F:/python/superset/migration/执行进度.md:8)；[退役观察期](/F:/python/superset/migration/batches/AB迁移/交接包/未验证与阻塞清单.md:43)；[总计划一次性执行定义](/F:/python/superset/superset-报表补迁与一致性验收及人员赋权长任务计划-v2-多方互查修订版.md:28)。

我建议修订时先以 **COMPAT／V5-REPLAY／10 月 12 日体检**重建现状和任务状态矩阵，再把免费执行核心包集中在：验收工具可靠性、同步剩余缺陷、访问范围验证、真实浏览器及导出验收、恢复与监测闭环。已修复的 SQL 和配置保留为回归基线；H03 旧证据、外部数据库连接、发布赋权和长期观察分别形成可交接的剩余项。
