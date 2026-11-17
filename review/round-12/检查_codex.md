这份方案**基本忠实于用户意图，但尚不完整，不能直接交给执行 AI 实施**。主要问题是：现状基线采信了存在矛盾的验收结论，遗漏了几处直接影响查询操作的缺陷，同时把部分未经证实的美化建议列入了改进池。

本次只读检查了方案、实现代码、既有截图和原始验收记录，没有修改文件，也没有重新登录生产实测。以下区分“已证问题”“静态风险”和“待复验事项”。

1. **【高优先级，已证】“Chromium 87 全过”缺乏原始证据支持，应先纠正基线。**

   方案将其列为已完成事项，但 SYSFINISH 原始记录中，43、44、45、46 页的日期筛选区均出现“网络异常”；58、59 页的日期控件出现“无结果”。表格能显示默认数据，不代表用户能够改变日期并成功查询。这直接影响“方便操作”，应进入首批复验任务。

   出处：[方案第27行](F:/python/superset/review/round-12/方案.md:27)、[43页原始记录](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/t17_chrome87_result.json:58)、[58页原始记录](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/t17_chrome87_result.json:273)、[59页原始记录](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/t17_chrome87_result.json:313)。

2. **【高优先级，已证】58 页“筛选成功”的既有验收存在假阳性，不能继续沿用。**

   验收脚本仍寻找名为“应用”的按钮，而现行按钮已经改为“查询”；结果文件明确记录 `apply_btn:false`。随后脚本以页面中“门诊”出现至少三次判定成功，新增请求实际是选项搜索请求，不能证明报表主查询已切换分支。名为“门诊筛选后”的截图实际还是返回后的分类目录。

   应重新验收完整链路：选择分支→点击“查询”→确认主图表请求携带分支→确认返回结果变化。不能只检查页面文字或 HTTP 200。

   出处：[验收脚本第162行](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/t17_interact58.py:162)、[成功判定第166行](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/t17_interact58.py:166)、[交互结果](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/p6_c87_interactive_result.json)、[所谓筛选后截图](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/p6_c87_58_branch_门诊.png)。

3. **【高优先级，静态已证】59 页存在控件参数名与模板读取名不一致，方案没有识别。**

   筛选定义绑定大写 `VISIT_ID1`、`VISIT_ID2`，SQL 模板读取小写 `visit_id1`、`visit_id2`。Superset 6.1.0 的模板过滤器按字段名精确匹配。因此，直接用小写参数调用接口成功，不能证明页面上的大写字段控件有效。

   应将其列为参数绑定缺陷核查，验证真实页面请求及最终消费的参数；不能靠猜默认值或放宽查询范围解决。

   出处：[筛选定义第155行](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/t02t05_build_spec.py:155)、[SQL模板第1行](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/candidates/new_337.sql:1)、[Superset 6.1.0 官方模板实现](https://raw.githubusercontent.com/apache/superset/6.1.0/superset/jinja_context.py)。

4. **【高优先级，静态风险】51、52 页的科室选项存在循环依赖，可能无法完成首次选择。**

   两页科室下拉分别从业务数据集332、333枚举 `DEPT_STAYED`，而这两个数据集在未选科室时使用 `A.DEPT_STAYED = NULL`，不返回记录。由此可能形成“必须先选科室才有数据，而下拉必须先有数据才有科室”的循环。

   UIFIX 已经处理过类似问题：打开 `searchAllOptions` 不能让受条件限制的 SQL 自动产生其他选项。定稿应要求验证两页下拉在首次进入、清空、无业务记录时是否仍能提供合法选项；如需调整选项来源，应单独界定范围，保留业务查询的未选拒绝逻辑。

   出处：[51/52页筛选定义](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/t02t05_build_spec.py:136)、[332查询](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/candidates/new_332.sql:1)、[333查询](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/candidates/new_333.sql:1)、[UIFIX同类问题说明](F:/python/superset/migration/sources/20261015-UIFIX/结果说明-20261015.md:13)。

5. **【高优先级，静态已证】遗漏月报旧数据重新显示问题，不能只安排加载动画。**

   月报加载、失败或期间不一致时，只清理显示区域并禁用导出，旧 `data` 数组仍然保留；搜索和翻页事件仍会调用 `table()`，重新使用这些数组。于是，在失败或等待期间操作搜索、分页，存在把旧结果重新画出来的路径。

   方案 G 将问题概括为骨架屏、进度提示，遗漏了数据状态正确性。上轮最终报告明确将“两源状态机”留给下一批，应该在本方案中接续为优先任务。

   出处：[月报搜索与分页事件](F:/python/superset/offline-bundle/custom/monthly-report.js:59)、[加载及失败处理](F:/python/superset/offline-bundle/custom/monthly-report.js:74)、[明确遗留记录](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/最终报告.md:66)、[方案G](F:/python/superset/review/round-12/方案.md:37)。

6. **【高优先级，静态已证】月报首次失败、单源失败和两源不同步，没有完整处理契约。**

   代码在检查失败状态之前，先要求两侧都存在 `queriesResponse[0]`；任意一侧没有响应对象就直接返回。这不能保证首次失败时出现可理解、可恢复的提示。当前一致性检查也主要比较返回数据第一行的期间，尚不能证明两侧属于同一次已提交查询。

   验收应覆盖首次失败、一侧失败、响应乱序、连续查询、单侧空结果、重试恢复，并要求所有非成功状态禁止操作旧结果。正常请求继续使用真实响应，故障验证单独标记。

   出处：[月报第68行起](F:/python/superset/offline-bundle/custom/monthly-report.js:68)、[上轮T09明确要求](F:/python/superset/migration/当前系统完善改进一次性执行计划-v1-20261015.md:187)。

7. **【高优先级，已证】快捷日期与新增报表约束冲突，容易引导用户查出空结果。**

   日期组件根据当前显示模式生成快捷项；默认范围模式统一提供“近7天”“本月”。因此，要求完整自然月的50—52页也会出现“近7天”；要求单日的53—57页同样显示“近7天”“本月”。原始页面记录已经证实这种组合。

   另外，单日识别正则只匹配 `Z03/H03/日报`，没有识别新增的 `P53-DAY` 等标识和“统计日期（单日）”，这些页面不会得到可选“单日”切换。应按报表契约提供合法快捷项，同时继续遵守默认起止范围的用户约定。

   出处：[日期模式判断](F:/python/superset/offline-bundle/custom/report-dates.js:31)、[快捷项生成](F:/python/superset/offline-bundle/custom/report-dates.js:57)、[50页实录](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/t17_chrome87_result.json:208)、[53页实录](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/t17_chrome87_result.json:238)。

8. **【高优先级，静态已证】“非法范围返回0行并提示”不能依赖结果中的“提示”列。**

   以332数据集为例，非法月份使 `bnd` 变为空，而主查询与 `bnd` 联合后没有记录；放在结果列中的提示文字也随之没有承载行。用户看到的可能只是“没有数据”，无法知道应该改成整月。

   计划应明确区分未填必选项、范围不合法、合法查询无数据、请求失败，并在控件附近给出可操作提示。不能把这些都纳入“空数据文案中文化”。

   出处：[332查询的chk/bnd及提示列](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/candidates/new_332.sql:9)、[方案A](F:/python/superset/review/round-12/方案.md:31)。

9. **【中优先级，已证】42、49 页的分类返回导航被改成普通文字，方案漏掉实际导航退化。**

   SYSFINISH 更新说明时，将“← 返回 护理部报表”“← 返回 统计报表·急诊”写成普通字符串，没有 Markdown 链接。49页原始记录中，虽然正文显示“返回”，链接列表却只有顶部“报表目录”。

   应恢复可点击的分类返回入口，并验证鼠标、键盘及浏览器后退。这个问题比增加“最近使用”更应先处理。

   出处：[说明更新脚本第13行](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/t06t09_notes_worker.py:13)、[49页链接记录](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/t17_chrome87_result.json:176)、[方案B](F:/python/superset/review/round-12/方案.md:32)。

10. **【中优先级，已证】58、59 页仍显示“SQL缺陷未修”，与最新处理状态不一致。**

    原始页面文字仍写“既有 SQL 缺陷未修（ORA-00907）”，但最新最终报告已经记录SQL修复。用户会同时看到旧故障说明和当前空结果，难以判断应该选条件、等待修复还是联系信息科。

    应逐页核对状态说明，保留真实待验、必选参数及外部依赖，不得直接统一成“已完成”。

    出处：[58页正文](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/t17_chrome87_result.json:273)、[59页正文](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/t17_chrome87_result.json:313)、[SQL修复记录](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/最终报告.md:27)。

11. **【中优先级，已证】缺少“待查询条件”和“结果实际条件”的明确区分。**

    现有月报截图中，日期输入为空、显示占位文字，结果却是2026年9月。代码收到 `No filter` 时清空输入，但实际默认业务窗由SQL决定。页面同时有“×”和“清除所有”，方案没有规定两者的可见解释及重置后的状态。

    应显示当前结果实际期间，提示条件已修改但尚未查询，并明确“清除”恢复默认窗。默认范围控件已经完成，不代表这套反馈已经完成。

    出处：[月报截图](F:/python/superset/migration/sources/20261015-RANGEUI/final-monthly-1366x768.png)、[日期同步和清除逻辑](F:/python/superset/offline-bundle/custom/report-dates.js:40)、[上轮条件反馈要求](F:/python/superset/migration/当前系统完善改进一次性执行计划-v1-20261015.md:148)。

12. **【中优先级，已证】“CSV已好”表述过宽，遗漏导出范围与按钮承诺不一致。**

    月报按钮写“导出整张报表”，实际导出函数调用 `rows()`，会应用当前搜索词。因此搜索后导出的是筛选结果，用户容易误以为拿到了完整报表。文件名固定，也不携带期间；CSV没有单独的期间说明。

    此外，最新45页导出证据的表头仍为 `KS,BED_END,OPEN_DAYS,DISCH_N,USAGE_RATE`，不能据此概括全部CSV中文化通过。应逐种导出路径核查按钮含义、行列完整性、期间、中文标题及格式。

    出处：[月报搜索与导出逻辑](F:/python/superset/offline-bundle/custom/monthly-report.js:37)、[导出按钮](F:/python/superset/offline-bundle/custom/monthly-report.js:60)、[45页CSV原始结果](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/t10t11t12.json:5)、[方案E](F:/python/superset/review/round-12/方案.md:35)。

13. **【中优先级，方案风险】数值格式不能直接统一为“率值两位、负数红字、千分位”。**

    方案没有逐列区分人数、金额、代码、比率和已有百分数值。统一处理可能丢失代码前导零、将百分数再次放大、掩盖原小数精度，或把NULL误显示为0。负值着色也不应代替业务含义。

    应建立逐列显示规则，记录单位、原始缩放、小数位及NULL表现。月报目前已经将数值右对齐，不能把它再当作所有页面都未完成的事项。

    出处：[方案H](F:/python/superset/review/round-12/方案.md:38)、[月报现有右对齐样式](F:/python/superset/offline-bundle/custom/monthly-report.js:19)、[既有字段格式约束](F:/python/superset/migration/当前系统完善改进一次性执行计划-v1-20261015.md:214)。

14. **【中优先级，方案风险】合计置底和冻结列需要明确语义，不能作为通用样式直接实施。**

    “合计行是数据行”本身不构成缺陷。必须明确合计属于全结果还是当前搜索结果，避免重复计算或把分页数据求和当总计。

    月报左右两栏按各自科别和顺序排列，不是同一科别的关联行；冻结列应分别保留两侧识别信息。不能为了对齐或固定合计而按科别重新连接、重排、补零，改变既定报表表现。

    出处：[方案A](F:/python/superset/review/round-12/方案.md:31)、[月报独立排列实现](F:/python/superset/offline-bundle/custom/monthly-report.js:44)、[月报现有说明](F:/python/superset/offline-bundle/custom/monthly-report.js:61)。

15. **【中优先级，待澄清】“无搜索、无常用”应限定为定制目录入口，避免重复建设。**

    Superset 6.1.0官方实现已经包含看板名称/slug搜索和收藏筛选，现有截图标题旁也有星标。定制分类目录缺少统一检索入口，可以是成立的体验问题；将其写成整个系统没有相关能力不够准确。

    应先评估如何让已有能力更容易找到，再决定是否新增目录搜索或收藏入口；若增加本机最近使用，还需明确账号切换及失效链接处理。

    出处：[方案B](F:/python/superset/review/round-12/方案.md:32)、[当前月报截图](F:/python/superset/migration/sources/20261015-RANGEUI/final-monthly-1366x768.png)、[Superset 6.1.0官方看板列表实现](https://github.com/apache/superset/blob/6.1.0/superset-frontend/src/pages/DashboardList/index.tsx)。

16. **【中优先级，证据不足】现代浏览器问题不宜预先定性为“水合异常”，也不能简单认为两份报告互相否定。**

    UIFIX记录的是内容DOM存在但被裁切；SYSFINISH记录的是其他页面出现空渲染。不同页面、不同时间和不同现象可以同时成立。“未改页面也空白”能够支持问题不局限于本批修改，尚不足以单独证明根因就是水合。

    应记录准确浏览器版本、页面、加载方式、网络失败、控制台异常和DOM状态，再决定修改哪一层。同时，方案要求本批“双浏览器可验”，又把现代浏览器故障放进取证档，需要明确哪些任务可独立通过、哪些被阻塞。

    出处：[方案D及三档要求](F:/python/superset/review/round-12/方案.md:34)、[UIFIX观察](F:/python/superset/migration/sources/20261015-UIFIX/结果说明-20261015.md:10)、[SYSFINISH浏览器结论](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/最终报告.md:46)。

17. **【中优先级，范围遗漏】“当前系统前端”尚未明确覆盖哪些用户和操作链。**

    方案集中在27个查询页，未明确首页、登录/会话失效、个人信息与改密、目录可见性是否纳入分析。现有验收主要是管理员界面，而27页实际开放仍为0；管理员看到的编辑入口和操作复杂度不能直接代表员工体验。

    应用现有合法身份区分管理员、普通使用者和无权限访问者；没有获批的员工正向场景可以标待验，不需为界面评估新增授权。401/404引导也应按实际导航和API响应场景设计，避免将所有失败都当成独立错误页。

    出处：[方案范围及错误引导项](F:/python/superset/review/round-12/方案.md:20)、[实际开放状态](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/最终报告.md:14)、[匿名页面壳200、数据API401记录](F:/python/superset/migration/sources/20261015-2030-SYSFINISH/t10t11t12.json:2)。

18. **【中优先级，实施风险】只写“custom层、文件级回退”不足以覆盖拟议变更。**

    修复导航文字、筛选标签、表头、附表分组，可能涉及看板布局、筛选元数据、图表显示配置及翻译资源，并非只改一个JS文件。Superset官方表格已有列定制能力，应先评估配置方式，避免把所有调整继续堆进DOM补丁。

    每项应列实际修改对象、写前值和哈希、允许变化字段、回退条件；资产部署还须涵盖版本查询串、nginx注入、CSP和缓存。文件回退不能代替元数据回退。

    出处：[方案第42行](F:/python/superset/review/round-12/方案.md:42)、[现行nginx注入配置](F:/python/superset/offline-bundle/nginx.conf)、[既有资产发布契约](F:/python/superset/migration/当前系统完善改进一次性执行计划-v1-20261015.md:254)、[Superset 6.1.0表格配置实现](https://github.com/apache/superset/blob/6.1.0/superset-frontend/plugins/plugin-chart-table/src/controlPanel.tsx)。

19. **【中优先级，静态风险】可维护性分析漏掉两个关键脚本的适配与降级行为。**

    方案主要点名 `report-ui.js`，实际日期组件依赖 React Fiber寻找回调，月报依赖内部store和固定图表ID。日期元数据加载失败后缓存为空对象，后续 `load()` 会直接返回，缺少重试；控件隐藏前也未验证桥接提交一定可用。

    这不仅是未来升级风险，也可能影响当前首次加载和网络失败恢复。应增加桥接失败保留原生控件、元数据重试、SPA往返清理和防重复注入的验收。

    出处：[方案F](F:/python/superset/review/round-12/方案.md:36)、[日期桥接与元数据加载](F:/python/superset/offline-bundle/custom/report-dates.js:24)、[隐藏原生控件](F:/python/superset/offline-bundle/custom/report-dates.js:61)、[月报store依赖](F:/python/superset/offline-bundle/custom/monthly-report.js:33)。

20. **【中优先级，验收遗漏】两种分辨率和截图通过，不能直接证明“直观方便”。**

    方案缺少完整任务验收，例如：从首页找到目标报表、修改合法条件、提交查询、识别结果期间、导出正确范围、返回分类。还应检查键盘Tab/Enter/Escape、日历只选一端、浏览器缩放，以及40px说明区的长文字是否容易发现和读完。

    护理日报的附区拟折叠，也应明确默认展开状态、内容提示、打印和导出是否保留，不能用减少可见内容作为方便操作的唯一指标。

    出处：[方案A及验收安排](F:/python/superset/review/round-12/方案.md:31)、[既有键盘与状态验收要求](F:/python/superset/migration/当前系统完善改进一次性执行计划-v1-20261015.md:196)、[RANGEUI对说明区的实现说明](F:/python/superset/migration/sources/20261015-RANGEUI/结果说明-20261015.md)。

21. **【中优先级，证据不足】打印可以进入需求核查，但“从未对照老系统”说得过满。**

    当前材料没有提供打印专项验收，不等于可以证明历史上从未对照。用户原话也没有明确要求恢复完整旧打印版式。

    应先确认哪些报表确实需要打印、纸张和方向要求，再决定优先级。若实施，须验证全结果、续页表头、横纵滚动区和附表内容，不能只打印当前50行或屏幕可见区域。

    出处：[方案E](F:/python/superset/review/round-12/方案.md:35)、[月报分页实现](F:/python/superset/offline-bundle/custom/monthly-report.js:39)、[既有打印要求](F:/python/superset/migration/当前系统完善改进一次性执行计划-v1-20261015.md:218)。

22. **【计划完整性问题】“综合各AI意见”和“可交接执行”目前仍是承诺，缺少落实结构。**

    方案尚没有逐项任务编号、优先级、依赖、工作量、完成判据和意见处置表。ZCode初审也承认拟议池部分来自猜测、缺对象级证据。各AI提出的建议应逐条记录来源、复核证据、采纳/暂缓/拒绝理由和最终任务，不能仅将建议合并后称为共识。

    定稿应优先安排上述查询链路、参数绑定、状态正确性和导航退化问题，再安排列冻结、搜索、打印等体验增强。每项至少写明页面/图表/数据集、复现方式、修改边界、验收用例、回退对象和依赖；资料不齐的建议保留“存疑”，无需等待所有可选需求确认后才推进已证缺陷。

    出处：[方案目标](F:/python/superset/review/round-12/方案.md:11)、[拟议结构及自身验收](F:/python/superset/review/round-12/方案.md:40)、[ZCode独立初审](F:/python/superset/review/round-12/审查_zcode.md)。
