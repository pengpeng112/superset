**Superset 可以保留为优先试点候选，但这份方案尚不能认定“完整满足需求”。** 主要问题是：混用了正式版与开发版能力、把百万行查询导出转移到了系统之外、遗漏了权限闭环，并误判了部分替代工具。

本次只读核查，未修改任何文件；结论来自官方文档和源码，未做院内连接、部署或性能实测。下文“方案”“清单”分别指 [方案.md](C:/Users/Administrator/.zcode/workspace/default/review/round-2/方案.md) 和 [参考_需求与论断清单.md](C:/Users/Administrator/.zcode/workspace/default/review/round-2/参考_需求与论断清单.md)。

1. **【重要错误】“仪表盘原生一键导出 Excel”不能作为当前正式版的已具备能力。**  
   核查时 GitHub 标记的正式版为 **6.1.0**；方案引用的整盘 Excel 导出文档标为 **Next**，6.1.0 的仪表盘 API 没有对应 `export_xlsx` 接口。单图表 XLSX 与整盘多工作表 XLSX 必须区分。出处：方案第55行；[正式版发布](https://github.com/apache/superset/releases/tag/6.1.0)、[Next 导出文档](https://superset.apache.org/user-docs/using-superset/exporting-dashboard-data/)、[6.1.0 仪表盘源码](https://github.com/apache/superset/blob/6.1.0/superset/dashboards/api.py)。

2. **【需求缺口】百万行脚本导出没有覆盖用户要求的查询系统体验。**  
   原话包含“类似 Excel 表格的上百万条数据的查询和导出”；方案只归纳成数据量，然后安排 AI 写文件。科室人员如何自行筛选、分页查看、发起导出、查看进度，没有落点。双轨架构可以提出，但目前只能算替代实现，不能直接记为 R4 已满足。出处：方案第20、32、48、87行。

3. **【权限缺口】轨道二不会自动继承 Superset RLS。**  
   Python 从数据平台查询、把文件放共享目录，经过的是另一条授权路径。方案未定义申请人身份、数据范围、文件访问权限、下载审计和过期删除；可能出现“页面按科室过滤，文件却包含全院明细”。出处：方案第48行；[Superset RLS 的适用对象是数据集查询](https://superset.apache.org/admin-docs/6.1.0/security/#row-level-security)。

4. **【架构矛盾】“受控限量查询通道”如何取得完整百万行，尚未解决。**  
   方案没有证明数据平台提供分页、游标或批量导出。仅写“Python 流式”不能突破平台返回上限；分批查询还需要稳定排序和一致性机制，避免漏行、重复及批次间数据变化。出处：方案第39、48、76行。此项属于基于方案描述的工程判断。

5. **【需求改写】R3 被不必要地收窄为“必须以 API 写进 BI”。**  
   原话要求外部 AI 查数后直接生成报表，并未限定 REST API。清单还允许“可编程报表定义格式”，方案却把 API 写成硬组合，可能错误淘汰 XML、HTML 或其他可编辑模板方案。出处：方案第18、31、98行；清单第18行。

6. **【实施语义不清】方案实现的是“保存 SQL 后重新查库”，不是直接使用 `$sjzc` 查询结果。**  
   Superset 虚拟数据集保存查询定义，实际查看时由 Superset 自己查询。必须说明 `$sjzc` 只是发现结构、验证口径，还是其结果需要被上传或物化；否则两次查询的凭据、时间点和权限可能不同。出处：清单第71、72行；[虚拟数据集说明](https://superset.apache.org/admin-docs/6.1.0/security/#rls-and-virtual-sql-based-datasets)。

7. **【重要遗漏】Superset 已有官方 MCP，方案只写社区 MCP。**  
   6.1.0 包含官方 `mcp_service`，支持创建虚拟数据集、图表和仪表盘，直接对应外部 AI 建报表需求。“AI 建报表无广泛案例”不能替代对官方能力的评估。出处：方案第54、74行；[6.1.0 官方 AI 指南](https://superset.apache.org/user-docs/6.1.0/using-superset/using-ai-with-superset/)、[官方 MCP 源码](https://github.com/apache/superset/tree/6.1.0/superset/mcp_service)。

8. **【论断6不完整】百万行不能只检查 `ROW_LIMIT` 和 `SQL_MAX_ROW`。**  
   6.1.0 另有 `TABLE_VIZ_MAX_ROW_SERVER=500000`；SQL Lab 默认查询量是 `DEFAULT_SQLLAB_LIMIT=1000`，界面显示上限是 `DISPLAY_MAX_ROW=10000`。图表保存的 `row_limit`、分页和普通／完整导出路径也影响结果。参数可调，不等于已经证明百万行完整导出。出处：方案第56行；[6.1.0 配置源码](https://github.com/apache/superset/blob/6.1.0/superset/config.py)。

9. **【证据错误】issue #35139 不是“官方确认百万行可行”。**  
   相关解答主要来自 `dosubot[bot]`，并且用户反复报告配置调大仍只导出五万行。它不能充当维护者确认，更不是性能验证。出处：方案第56行；[issue #35139](https://github.com/apache/superset/issues/35139)。

10. **【论断7错误】“百万行导出必须 Celery 异步，否则必然超时／OOM”过于绝对。**  
    6.1.0 已有 CSV 流式导出，源码使用 `stream_results` 和 `fetchmany`。后台查询、流式下载、后台生成 XLSX 是不同机制，不能统称“异步导出”。异步也不能保证 XLSX 构建过程内存有界。出处：方案第57行、清单第42行；[流式导出源码](https://github.com/apache/superset/blob/6.1.0/superset/commands/streaming_export/base.py)。

11. **【重要版本风险】嵌入、流式导出和执行身份需要一起验证。**  
    #40933 报告 6.1.0 嵌入态流式 CSV 缺少 Guest Token，返回401；#40465 报告流式路径在 Trino 上遗漏执行上下文。前者后来关闭，也不能据此认定原始6.1.0安装包已修复。不能直接推断 Oracle 同样受影响，但必须核对补丁版本并测试。出处：方案第57、62行；[#40933](https://github.com/apache/superset/issues/40933)、[#40465](https://github.com/apache/superset/issues/40465)。

12. **【论断12过时】不需要一概改用 `@preset-sdk/embedded`。**  
    当前官方6.1.0 README明确推荐 **`@superset-ui/embedded-sdk`**。#21829 中换包只是旧用户的解决经验，不能成为当前实施要求。导出还受 iframe sandbox、按钮显示和角色权限影响。出处：方案第62行；[官方 SDK README](https://github.com/apache/superset/blob/6.1.0/superset-embedded-sdk/README.md)、[旧评论](https://github.com/apache/superset/issues/21829#issuecomment-1333380774)。

13. **【接口细节】Guest Token 请求的字段应是 `rls`，JWT 内部才是 `rls_rules`。**  
    方案说“token 携带 `rls_rules`”本身可以成立，但不能把它照抄为 `/guest_token/` 请求字段。官方示例明确区分了两者。出处：方案第61行；[SDK 的两种令牌示例](https://github.com/apache/superset/blob/6.1.0/superset-embedded-sdk/README.md#creating-a-guest-token)。

14. **【嵌入授权缺口】Guest Token 不会自动识别门户里的科室权限。**  
    宿主后端必须根据已认证身份生成资源范围与 RLS；用户名字段不会自动继承同名 Superset 用户的全部角色。还需实现令牌刷新、允许嵌入的域和签名密钥配置。出处：方案第61、86行；[官方嵌入认证说明](https://github.com/apache/superset/blob/6.1.0/superset-embedded-sdk/README.md#authenticationauthorization-with-guest-tokens)。

15. **【RLS不等于组织权限】科室、人员“不同层级”尚无具体模型。**  
    内置 RLS 是过滤机制，不是医院组织树。普通医生、科主任、跨科室人员、院级管理者的数据范围需要映射；多条规则还涉及 AND／OR 分组。试验“一条科室规则”不足以验收层级权限。出处：方案第33、58、84行；[RLS 类型与组合规则](https://superset.apache.org/admin-docs/6.1.0/security/#row-level-security)。

16. **【重要边界】SQL Lab 默认不受同样的 RLS 约束。**  
    6.1.0 的 `RLS_IN_SQLLAB` 默认关闭，源码还提示开启后的解析机制可能存在绕过。因此不能向受限科室用户随意开放 SQL Lab 或整库访问，然后声称全路径行级隔离。出处：方案第58、59行；[配置源码](https://github.com/apache/superset/blob/6.1.0/superset/config.py)、[安全文档](https://superset.apache.org/admin-docs/6.1.0/security/#rls-and-virtual-sql-based-datasets)。

17. **【人工制作的安全边界遗漏】Jinja 动态权限不是开箱即用。**  
    `current_username()` 对应的模板处理需要开启 `ENABLE_TEMPLATE_PROCESSING`。官方把可编辑图表／虚拟数据集的用户视为可信用户，并明确说明服务器模板执行风险。方案同时允许科室 GUI 微调，必须区分浏览者与可信报表开发者。出处：方案第47、58行、清单第75行；[SQL Templating 安全说明](https://superset.apache.org/admin-docs/6.1.0/configuration/sql-templating/)。

18. **【论断9需补条件】角色体系存在，但仪表盘授权不能省略配置。**  
    按仪表盘显式绑定角色需要考虑 `DASHBOARD_RBAC`，6.1.0 默认关闭；数据集访问、仪表盘访问、行级过滤是不同层次。验收应检查越权直接访问链接和 API，而不只是菜单里看不到。出处：清单第44行；[Dashboard RBAC](https://superset.apache.org/admin-docs/6.1.0/security/#dashboard-level-access-dashboard_rbac)。

19. **【新增邮件风险】定时报表不会按每个收件人的身份重新过滤。**  
    源码选定一个执行用户，生成通知内容后发送给收件人列表。高权限人员创建的报表邮件，可能把其可见数据发给低权限科室人员。免费定时邮件能力成立，但按收件人隔离不能默认成立。出处：方案第47、63、85行；[执行用户选择](https://github.com/apache/superset/blob/6.1.0/superset/tasks/utils.py)、[报表执行与发送](https://github.com/apache/superset/blob/6.1.0/superset/commands/report/execute.py)。

20. **【论断2缺少兼容条件】Oracle 直连成立，但“安装驱动即可”不足。**  
    必须核对 Oracle 版本、驱动版本、Thin／Thick 模式和连接配置。默认 Thin 模式要求 Oracle12.1及以后；旧库需要匹配的客户端与 Thick 模式。医院若仍有旧 Oracle，这会直接影响部署。出处：方案第52、83行；[Superset Oracle 文档](https://superset.apache.org/user-docs/databases/supported/oracle/)、[驱动兼容说明](https://python-oracledb.readthedocs.io/en/latest/user_guide/installation.html#supported-oracle-database-versions)。

21. **【数据库验收不全】SQL Server 被列入背景，却没有实施和验收步骤。**  
    Vastbase 的 PostgreSQL兼容性也不能只测“连接成功”，还要测元数据读取、日期函数、分页、中文及大结果导出。出处：方案第39、73、83行；[Superset 驱动安装说明](https://superset.apache.org/admin-docs/6.1.0/installation/docker-builds/)。

22. **【内网实施不完整】缺少离线依赖和生产运维方案。**  
    正式版镜像需要补数据库驱动；无外网环境还需预备镜像、包、浏览器和前端依赖。官方 Compose可用于测试，但官方明确不推荐直接用于生产，Windows也无官方支持。方案还缺备份恢复、升级回滚、监控和容量规划。出处：方案第39、75、82行；[6.1.0 镜像说明](https://superset.apache.org/admin-docs/6.1.0/installation/docker-builds/)、[Compose边界](https://superset.apache.org/admin-docs/6.1.0/installation/docker-compose/)。

23. **【Excel完整性遗漏】工作表上限正确，但仍需防止数据损坏。**  
    一张 `.xlsx` 工作表最多1,048,576行；有一行表头时最多容纳1,048,575条数据。身份证号等超过15位的编号应按文本导出。还应验收实际行数、金额汇总、中文、空值和时间字段，而非只检查下载成功。出处：方案第57行；[Microsoft Excel限制](https://support.microsoft.com/en-us/excel/excel-specifications-and-limits?facet1=marketing)。

24. **【明确误判】Metabase 的 Oracle 驱动不是仅付费版提供。**  
    官方文档指导把 `ojdbc8.jar` 放入插件目录即可连接 Oracle。Metabase仍可因原生行列权限收费墙降级，但必须换成正确理由。出处：方案第67行、清单第56行；[Oracle连接说明](https://www.metabase.com/docs/latest/databases/connections/oracle)、[行列权限收费边界](https://www.metabase.com/docs/latest/permissions/row-and-column-security)。

25. **【应恢复候选】DataGear“无程序化建报表 API”的排除理由错误。**  
    源码存在 `/dataSet/saveAdd/...`、`/chart/saveAdd`、`/dashboard/saveAdd` 和看板设计保存接口；同时支持HTML模板和可视化编辑。没有内置 AI也不妨碍外部 AI生成报表。接口稳定性、认证及维护成本需要评估，但不能直接排除。出处：方案第67行、清单第62行；[DataGear项目说明](https://github.com/datageartech/datagear)、[数据集控制器](https://github.com/datageartech/datagear/blob/master/datagear-web/src/main/java/org/datagear/web/controller/DataSetController.java)、[看板控制器](https://github.com/datageartech/datagear/blob/master/datagear-web/src/main/java/org/datagear/web/controller/DashboardController.java)。

26. **【DataGear还有两项相关能力被遗漏】按当前用户过滤、流式分工作表导出。**  
    后端提供 `DG_USER`、`DG_ROLE_NAMES`，可供参数化数据集返回不同数据；Excel导出使用 `SXSSFWorkbook(500)`，超过工作表行数时自动新建sheet。它值得进入中文、轻量部署候选比较。不过数据源导出模块是否遵循报表用户权限，仍需单独验证。出处：清单第62行；[身份参数源码](https://github.com/datageartech/datagear/blob/master/datagear-web/src/main/java/org/datagear/web/analysis/DataSetQueryParams.java)、[Excel导出源码](https://github.com/datageartech/datagear/blob/master/datagear-dataexchange/src/main/java/org/datagear/dataexchange/support/ExcelDataExportService.java)。

27. **【重要遗漏候选】Seal Report值得与Superset对比试点。**  
    当前项目采用MIT许可，支持Oracle/MySQL、人工设计、XML报表定义、Web API、Excel/CSV、调度和按登录用户／组过滤。对于明细表、固定格式报表，以及AI直接编辑本地报表定义的需求，它可能更贴近。百万行性能、中文体验和权限闭环尚未证明，不能宣称全面胜出。出处：方案候选清单第66—70行；[官方项目](https://github.com/ariacom/Seal-Report)、[报表格式](https://sealreport.org/Reports)、[Web API](https://sealreport.org/demo/WebInterfaceAPI.html)、[按用户过滤](https://sealreport.org/Recipes#lineDynamicSecurity)。

28. **【部分排除依据失真】维护状态和漏洞年份应改成可核对证据。**  
    Datart有2023年的代码修复和2025年的安全文档提交，“2022后停更”不准确，虽仍可判断维护不足。AJ-Report对应CVE-2024-7314在2024年已公开，2025是公告更新年份之一。是否排除应看目标版本修复情况，而非只看“曾有漏洞”。出处：方案第67行、清单第63、64行；[Datart提交记录](https://github.com/running-elephant/datart/commits/master/)、[AJ-Report漏洞公告](https://github.com/advisories/ghsa-29j3-7mhp-wmwm)。

29. **【R7不应成为BI淘汰条件】本地修改能力主要取决于Agent执行环境。**  
    能调用BI API，不等于能修改本地文件；能执行本地命令，也不等于拥有BI编辑权限。R7应明确修改对象、部署位置和权限。本轮明确只读，因此没有执行修改，但不影响评估将来可编辑的报表定义或配置。出处：方案第10、35、41、101行；本轮用户约束。

30. **【验收标准不足且偏向既定结论】“找不到全满足替代就维持Superset”不能证明Superset合格。**  
    应先要求候选通过同一组验收：AI新建与修改后人工可继续编辑；百万行以上无截断；不同科室、跨科室及院级账号隔离；直登、嵌入、导出和邮件权限一致；断网运行、重启恢复及并发可接受。现有“一两张报表＋一条RLS”不能支持全院推广，六项风险也尚未给出处置。出处：方案第84、87、91—94行。

未发现需要推翻的基础事实包括：**Apache Superset主体采用Apache2.0许可，具有报表资产REST API、开源RLS/RBAC、可配置的LDAP/OAuth角色映射、免费Alerts & Reports和中文语言包**。这些能力成立，但不能替代上述版本、权限和性能验证。出处：[许可](https://github.com/apache/superset/blob/6.1.0/LICENSE.txt)、[API](https://github.com/apache/superset/blob/6.1.0/docs/developer_docs/api.mdx)、[认证映射](https://flask-appbuilder.readthedocs.io/en/latest/security.html)、[定时报表](https://superset.apache.org/admin-docs/6.1.0/configuration/alerts-reports/)、[中文包](https://github.com/apache/superset/blob/6.1.0/superset/translations/zh/LC_MESSAGES/messages.po)。
