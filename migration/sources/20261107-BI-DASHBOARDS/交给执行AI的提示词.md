在 F:\python\superset 工作区一次性完成【20261107-BI-DASHBOARDS 剩余任务：3 个可视化 BI 驾驶舱的修复、验收与落账】。直接执行到底，不要只给分析或计划。

一、背景与依据
- 看板 72/73/74 和图表 371–387、389–391 已在生产创建并发布；前端 home-ui 20261107h8、report-ui 20261107f12、report-dates 20261107d14 已上线；原有对象至今零修改（已用快照证明）。
- 线上仍有问题：8 张图渲染报错，看板 74 普通员工打不开，目录 34 搜索框丢失，多张图口径错误。验收和落账还没做。
- 唯一执行依据：migration/sources/20261107-BI-DASHBOARDS/剩余任务一次性执行计划-交接版.md（v1.1）。
  - 先读 AGENTS.md、目录索引.md、migration/执行进度.md 文首，再读计划 §1（已核实事实）和 §12（已知坑）。
  - 计划与本提示词冲突时，以本提示词为准；两者都没写到的，按 AGENTS.md 处理。
- 凭据只从 superset-访问信息.md 和部署计划第 2 节读取，经环境变量注入（JB_*、TGT_*、ACC_ADMIN、ACC_GUEST），不得写进任何脚本和文档。Git Bash 下调用 remote_exec.py 前先 export MSYS_NO_PATHCONV=1。

二、铁律
1. 严禁 superset init；不碰宿主 nginx/PostgreSQL 和 ai-hms、data-asset 容器。
2. 只改本批对象：看板 72/73/74、图表 id>354、本批新建数据集 id>372。
   - 严禁修改或删除现有数据集 1–372、图表 1–354、看板 1–70 及保护对象。
   - 不改任何现有数据集的 SQL 和列名，不改 RLS、角色成员、角色权限。
3. 元数据库直写必须持锁 /tmp/user_sync.lock；Redis 只清 db0、db1，严禁 db2/db3/db4。
4. 新图表不得出现患者级字段。
5. 74 绑定 Gamma 后，003158 若仍取不到数，停下报告，不得靠改角色权限补救。
6. 不要用 Stop-Process -Name chrome 这类全杀命令（会关掉用户自己的浏览器）。不要重跑 create_bi.py。

三、执行顺序（T0→T6，细节见计划对应章节）
T0 只读核对
- 启动端口转发。
- 在服务器跑 snapshot_bi.sh，再用 compare_snapshot.py 对比，结果必须 PASS。
- 线上前端四件 SHA 必须等于计划 F13。不一致就先停下报告。

T1 止损快修
① 看板 74：PUT /api/v1/dashboard/74 {"roles":[4]}，再用 003158 会话核验 74 的图表取数返回 200。
② 375/376/377/383/384/387/389/390 的顶层 viz_type 改为 table：
   - 用 PUT 带 viz_type；不生效就用 psql 持锁 UPDATE，限定 id>354。
   - 核对 viz_type 列与 params 一致，然后清 db0、db1。
③ 前端修复：先把线上四件备份到 before-fix/，再改：
   - home-ui：目录 34 的 ensureBiShowcase 改用 list.parentNode.insertBefore 插入，放到 ensureDirectorySearch 之后，加幂等判断和 try/catch；补齐入口条和侧栏 BI 分区的样式。
   - report-dates：73 的契约改为 {gran:'sameday',quick:'day'}。
   - report-ui：DASHBOARD_ALIASES 补三个 slug（bi-overview=72、bi-outpatient-flow=73、bi-surgery-quality=74）。
   - 三件都过 node --check，原位上传，浏览器核验。

T2 口径与配置（必做，计划 §6）
- 时间列：72、74 的图表设 granularity_sqla=STAT_BEGIN；73 的图表设 granularity_sqla=STAT_DATE。改完实测 73 选单日查询后，SQL 含所选日期。
- 合计行：378/387/390/391 排除合计、总计行，条件写进 params.adhoc_filters。
- 看板 73：
  - 四张 KPI 改取 DTIME='17:00' 那一桶，名称改为「截至17:00××人次」；
  - 381 换成超声（ds326），并同步筛选 targets。
- 看板 74：
  - 386 改为住院手术台数，只取合计行；
  - 新增门诊手术台数（BRANCH_NAME IN ['门诊'] + 合计行），正确加入看板 74（position_json 和 dashboard_slices 都要有）；
  - 387 改为住院手术科室 TOP15。
- 377 只保留治愈、好转、未愈、死亡、其他 5 项。
- 看板说明区、首页入口文案、图表名都要与最终实现一致。
- 按计划 §6.7 的数字逐项对账：72 九月门诊 54,619；74 默认窗住院 507、门诊 129；73 在 2026-11-06 挂号 1,852。

T3 可视化增强（计划 §7，试点制；每项最多尝试两次，失败就保留表格并在报告写明）
- 先用 375 试点 echarts_timeseries_bar（非时间 x 轴、降序前 15），成功再推广到 376/387/390。
- 383/384 改为累计折线。
- 饼图（377 转归、389 门诊与住院）需要新建只读长表数据集；冷查预检小于 10 秒并对账通过后才上线。

T4 台账与回退
- 从生产重建 bi_created_ledger.json：含 uuid，含新建的图表和数据集，另列中途已删除的 355–370、388、看板 71。
- rollback_bi.py 增加删除数据集和 --dry-run；dry-run 清单必须与 ledger 一致。不真删。

T5 双浏览器验收
- 矩阵：Chrome 156 + Chromium 87 × 1920×1080、1366×768 × admin、003158，共 4 轮。
- 003158 也必须打开三个看板，逐图 rendered。
- 联动按数值断言，三个看板都测。
- 记录冷启动和热启动的首屏耗时，按冷启动小于 10 秒判定。
- 核对目录 34 的搜索框和入口条、首页侧栏、slug 访问。
- BI 看板截图不隐藏表体，文件名 bi-dashboard-{1,2,3}-{chrome|c87}-{1920x1080|1366x768}.png。

T6 落账
- 跑 snapshot_bi.sh，再用 compare_snapshot.py 对比，必须 RESULT PASS。
- 写最终报告.md，偏差必须写明：
  - BI-3 没有抗菌药物图，因为 ds365 聚合要 48.4 秒；
  - 取药换成超声，因为 ds323 冷查 17.6–18.6 秒；
  - dist_bar 不可用，以及柱图、饼图的实际落地情况。
- 冻结 migration/冻结快照/20261107-BI-DASHBOARDS-SHA256.json。
- 更新 migration/执行进度.md 和 目录索引.md。

四、完成判定与输出
- 以计划 §14 的 J1–J10 为准，在最终报告里逐条对照。任何 FAIL 都要写根因和终判，不得隐瞒，也不得改写判定口径。
- 结束时输出：
  - 变更对象清单（看板、图表、数据集的 id 和改动）；
  - 对账结果；
  - 前端四件 SHA256；
  - 验收汇总与截图路径；
  - 快照对比结论；
  - 未完成项。
