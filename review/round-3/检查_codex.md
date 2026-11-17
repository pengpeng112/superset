**这份方案尚不具备直接移交执行的完整性，也不能据其验收表认定已完整满足需求。** 主要问题是：部分命令和配置错误、HIS 身份认证尚未落定、百万行明细轨道没有交付计划，以及生产恢复能力缺失。

审查对象为 [review/round-3/方案.md](/F:/python/superset/review/round-3/方案.md)。以下“出处”均指该方案；另行引用的官方资料用于核实技术事实。核查口径为 **2026-10-04、Superset 6.1.0 正式版及对应标签源码**。本次只读取文档和脚本、查阅公开资料，没有修改文件、登录服务器、连接数据库或运行核查脚本。

“❌”表示可确定的错误或缺项；“存疑”表示现有材料不足以确定。

1. **❌ “全部步骤命令级”的交付声明不成立。**  
   **出处：§0 U4、P2-S4、P3-S3、P5-S1。** Compose 只有要点，用户同步只有逻辑描述，备份只有一句命令概要。文档称“完整文件已在介质 compose 内”，但本次只读检索未发现对应 Compose、配置、同步或备份文件。执行者仍需补做大量设计，不能将这些文件标为“已备齐”。

2. **❌ 生产配置代码块不能直接作为 Python 文件使用。**  
   **出处：P3-S4。** `CACHE_CONFIG = {...redis...}、DATA_CACHE_CONFIG…`、`CELERY_CONFIG = broker_url=…`、中文 SMTP 说明以及用 `/` 串联的行数配置均是提纲或无效语法。应给出完整可加载配置，并明确哪些占位符必须替换、替换后如何检查。

3. **❌ 三个关键功能开关写错位置。**  
   **出处：P1-S4、P3-S4。** `ENABLE_TEMPLATE_PROCESSING`、`EMBEDDED_SUPERSET`、`ALERT_REPORTS` 应放在 `FEATURE_FLAGS` 字典中。直接写成同名顶层变量，不会按方案意图启用功能；后续 RLS、嵌入和报告验收因此失去前提。[6.1.0 功能开关文档](https://superset.apache.org/admin-docs/6.1.0/configuration/feature-flags/)

4. **❌ Oracle 接入方案遗漏 SQLAlchemy 版本兼容，是主线阻断问题。**  
   **出处：D4、P1-S2/S6、P2-S2、P4-S2。** 6.1.0 依赖限定 `sqlalchemy>=1.4,<2`；方案直接使用 `oracle+oracledb://`，却没有方言注册或兼容映射。Oracle 官方说明 SQLAlchemy 1.4 使用 `oracle://` 并需要模块映射，SQLAlchemy 2 才直接使用 `oracle+oracledb://`。仅安装 `oracledb` 不足以完成所写步骤，也不能直接升级 SQLAlchemy 2 来规避 Superset 的依赖约束。[6.1.0 依赖定义](https://github.com/apache/superset/blob/6.1.0/pyproject.toml)、[Oracle 官方兼容说明](https://python-oracledb.readthedocs.io/en/latest/user_guide/appendix_d.html#connecting-with-sqlalchemy)

5. **❌ Gunicorn 启动命令含无效参数，并缺应用入口。**  
   **出处：P3-S3。** 6.1.0 锁定的 Gunicorn 23 没有 `--limit-concurrency`；所列命令也未指定 WSGI 应用。`gthread` 的线程数应通过 `--threads` 配置。按现稿执行会在启动阶段失败。[Gunicorn 23 配置定义](https://github.com/benoitc/gunicorn/blob/23.0.0/gunicorn/config.py)、[Superset 6.1.0 官方启动脚本](https://github.com/apache/superset/blob/6.1.0/docker/entrypoints/run-server.sh)

6. **❌ Windows 本地主线的运行环境和命令不一致。**  
   **出处：P1-S1～S5、P2-S0/S6。** 原生 Windows 安装不是官方支持的主线；当前工作区使用 PowerShell，方案却混用 CMD 的 `set`、续行符 `^` 等写法，还遗漏初始化所需的 `FLASK_APP`。已有 Docker Desktop，却没有提供与生产镜像一致的 Linux 容器本地路线。[6.1.0 安装说明](https://superset.apache.org/admin-docs/6.1.0/installation/docker-compose/)、[PyPI 初始化要求](https://superset.apache.org/admin-docs/6.1.0/installation/pypi/)

7. **❌ RLS 示例同时存在变量错误和业务含义错误。**  
   **出处：P5-S2：`dept_code = '{{ current_user.username }}'`。** 官方提供的是 `current_username()` 宏；即使修正变量，前面规定 username 为工号，表达式仍是在比较“科室码＝工号”，没有实现所声称的用户到科室映射。[6.1.0 SQL 模板文档](https://superset.apache.org/admin-docs/6.1.0/configuration/sql-templating/)

8. **❌ 用户映射表如何参与各数据库的 RLS 没有设计。**  
   **出处：D2、P5-S1/S2。** `SUP_USER_DEPT` 放在数据中心 Oracle，不意味着 SQL Server、MySQL、Vastbase 上执行的查询能访问它。“复杂映射用 Jinja 子查询模板”没有说明查询在哪个数据库执行、如何取得映射、失败时如何拒绝访问。可以采用科室角色对应固定过滤条件等方式，但必须选定并落实。

9. **❌ 自定义认证类的继承方式会被 Superset 拒绝。**  
   **出处：P5-S3：“继承 FAB SecurityManager”。** 6.1.0 初始化代码明确要求继承 `SupersetSecurityManager`，否则抛异常。所写“覆写 auth_db 视图”也未说明认证方法、浏览器登录和 JWT 登录如何统一处理。[6.1.0 初始化源码](https://github.com/apache/superset/blob/6.1.0/superset/initialization/__init__.py)

10. **❌ 密码决策矩阵把“不能还原密码”误判为“不能验证密码”。**  
    **出处：D3、P5-S0：“加盐/不可逆（bcrypt 等）……不可行，只能 A”。** bcrypt 本来就支持用输入密码验证已保存哈希，不需要还原明文。认证可行性取决于算法、参数、盐、额外密钥或 HIS 认证接口是否可用，不能以“不可逆”排除。[bcrypt 项目验证示例](https://github.com/pyca/bcrypt#usage)

11. **存疑：默认方案 A 是否忠实满足“登录用户使用 sys_employee”。**  
    **出处：§0 U7、D3、P5 目标、P5-S0/S1。** 复制员工账号并另设密码，只能证明用户目录来自 HIS，不能证明使用 HIS 密码登录，更不能证明单点登录。用户原话没有明确这三种含义；方案却默认采用独立密码，并直接写“Superset 登录用户＝HIS”。应把这一关键语义列为待定决策及对应验收。

12. **❌ 初始密码方案存在明显弱点，强制修改没有实现。**  
    **出处：P5-S0：“初始密码＝工号后 6 位，通知首登修改”。** 可推测的工号不能作为全院默认密码；“通知修改”也不等于系统强制修改。缺少一次性密码、有效期、首次登录约束和重置流程。明文密码分支也应明确经认证框架哈希后保存，不能直接复制到密码字段。

13. **❌ 给 Guest Token 填真实 username，不会自动继承该员工的科室角色。**  
    **出处：P5-S2、P5-S5 嵌入用例。** Guest 用户具有独立角色和 Token 中的 RLS 规则；同名 username 并不把它变成已有员工账号。应由可信后端验证门户用户，再生成限定仪表盘资源及数据范围的 Token，不能仅靠前端提交 username。[6.1.0 Guest 用户实现](https://github.com/apache/superset/blob/6.1.0/superset/security/guest_token.py)、[RLS 实现](https://github.com/apache/superset/blob/6.1.0/superset/security/manager.py)

14. **❌ 缺少权限映射异常时的默认拒绝策略。**  
    **出处：P5-S1/S2。** 未定义员工无科室、多个科室、调科、角色缺失、同步中断时的行为。仅为已有科室角色绑定 regular RLS，不能证明未匹配角色的用户仍受限制。必须验证异常状态不会扩大数据范围，以及多科室规则按预期组合。

15. **❌ 创建科室角色不等于完成可用权限配置。**  
    **出处：P5-S1：“自定义角色，不继承内置角色”、P5-S2。** 新角色需要实际权限；文档没有给出基础浏览权限、数据集访问权限及科室范围的组合。v2 要求不要修改内置角色，并不意味着员工不能同时拥有 Gamma 和科室自定义角色。仪表盘按角色授权的实施方式也没有落定。[6.1.0 角色说明](https://superset.apache.org/admin-docs/6.1.0/security/)

16. **❌ AI 账号使用 Alpha 与“最小权限”不一致。**  
    **出处：P4-S5：“仅 Alpha 级”、D5、§12。** Alpha 可以访问全部数据源，并可新增或修改数据源，不能据此称为最小权限。应按指定数据集、报表导入和制作操作配置专用权限，并验证访问其他数据源被拒绝。[官方 Alpha 权限说明](https://superset.apache.org/admin-docs/6.1.0/security/)

17. **❌ 用户同步缺少关键执行契约。**  
    **出处：P5-S1。** 缺少 API 请求字段、分页查找、Token 刷新、必要的 CSRF 处理、角色替换策略、错误重试、任务互斥及部分失败恢复。“以 his_code 为键 upsert”没有说明 Oracle 映射与 Superset 更新如何保持一致。现有骨架不足以支持幂等执行。

18. **❌ 每日同步不能自动保证停用和调科后的权限及时生效。**  
    **出处：P5-S1：每日 06:00、离职置 inactive。** 没有规定 ODS 同步延迟、源数据缺失的判断方式、紧急停用渠道，以及已登录会话、JWT 和嵌入 Token 的失效行为。这些应纳入权限验收，不能只测试“新员工可登录”。

19. **❌ P5 回退顺序可能先撤掉隔离，再停用用户。**  
    **出处：P5 回退：“删除自定义角色与 RLS 规则→用户置 inactive”。** 用户仍可访问时先删过滤规则，可能短暂扩大可见范围。应先关闭相关访问或停用用户并处理存量会话，再恢复权限配置；清理范围应限定本轮创建的对象。

20. **❌ Oracle 的读写约束相互矛盾。**  
    **出处：§2 红线、P5-S1、P5 回退、§13。** 前文称“仅建表，不修改/删除”，后文又要求 upsert 和 DROP；§13 则改为“仅建/删表”，仍没有描述写入新表的权限。应明确“业务对象只读，自建辅助表允许哪些操作”，并区分读取账号与辅助表写入账号。这里的问题是约束不一致，不能简单认定用户已经禁止写入自建表。

21. **❌ HIS 员工表被直接假定存在于数据中心，来源未确定。**  
    **出处：P5-S0 查 HIS；P5-S1 连接数据中心读 `sys_employee`。** HIS 源库与 ODS 镜像不是同一物理来源；尚未核实 schema、员工停用字段、科室关联、更新频率及认证字段是否复制。应先形成来源契约，不能无条件切换到 ODS，更不能为此擅自改为生产 HIS 直连。

22. **❌ 员工“五行样例”的落档要求缺少脱敏边界。**  
    **出处：P5-S0。** 要求核实密码字段和哈希格式，又要求产出结构文档，但未规定样例脱敏。应只记录字段结构、算法判断和必要的掩码证据，避免员工姓名、完整密码哈希或明文密码进入审查文档与日志。这也符合所引用 sjzc 技能的输出限制。

23. **❌ 双轨架构的第二轨被排除，无法满足现有定案需求。**  
    **出处：§1 边界、§11 总体验收；v2 §2 R4、§5、§8。** v2 明确要求科室自助完成“筛选→翻页核对→异步导出→查看任务→取件”。方案排除了入口开发，且未安排另一个计划、责任人或交付时间。可以分期实施，但本计划集完成后不能声称已交付双轨架构。

24. **❌ 把 Next 的 Excel 参数混入 6.1.0，并误认为它会自动产生本地异步导出。**  
    **出处：D6、P3-S4。** `EXCEL_EXPORT_SYNC_MAX_ROWS` 不在 6.1.0 标签配置中。即便某版本支持异步导出，仅设置阈值也不会自动建立“超过十万行→Celery→服务器目录→取件”的业务流程。应分别说明正式版图表导出能力和自建明细导出服务。[6.1.0 配置源码](https://github.com/apache/superset/blob/6.1.0/superset/config.py)、[Next 导出文档](https://superset.apache.org/user-docs/using-superset/exporting-dashboard-data/)

25. **❌ 导出治理只有表名，没有实现计划。**  
    **出处：D2、P5-S5 导出验收、§12“SUP_EXPORT_AUDIT，后续应用接入”。** 没有审计表 DDL、导出事件写入点、条件记录、行数、文件归属、下载鉴权、留存期限和过期删除。验收却要求“审计表留痕”，与“后续接入”矛盾。建一张表不会自动审计 Superset 导出。

26. **❌ 小规模导出验收不足以验证百万行需求。**  
    **出处：P1-S7、P4-S4、§11。** 一次图表导出、万级 CSV 不能验证百万行文件的完整性、分 sheet、内存占用、任务恢复和取件权限。现有行数限制还可能导致结果截断。需要指定数据规模，核对筛选条件、实际总行数及文件行数，并验证失败和取消流程。

27. **❌ 门户嵌入只列了验收，没有部署计划。**  
    **出处：D5、P3-S4、P5-S5。** 缺少官方 SDK 离线介质、门户前后端改造、Token 签发接口、仪表盘嵌入设置、允许域名、Token 续期及门户身份映射步骤。不能只开启一个开关、设置 `frame-ancestors` 就进入 OA 嵌入验收。[6.1.0 嵌入说明](https://superset.apache.org/user-docs/6.1.0/using-superset/embedding/)

28. **❌ “Selenium/Firefox 已不支持”不符合 6.1.0。**  
    **出处：D1、P2-S2 注释。** 正式版源码仍包含 Selenium 和 Firefox 路线，`PLAYWRIGHT_REPORTS_AND_THUMBNAILS` 默认关闭。选择 Playwright 可以，但方案应显式启用相应开关，不能把安装 Chromium 当作自动切换成功。[6.1.0 浏览器实现](https://github.com/apache/superset/blob/6.1.0/superset/utils/webdriver.py)、[正式版功能开关](https://superset.apache.org/admin-docs/6.1.0/configuration/feature-flags/)

29. **❌ 定时报告缺少调度和截图访问配置。**  
    **出处：P3-S4、P5-S4。** 没有 `reports.scheduler` 的 `beat_schedule`，没有 worker 能访问的 `WEBDRIVER_BASEURL`，也没有截图及邮件端到端验收。仅启动 beat/worker 并安装浏览器不能证明报告会运行。[6.1.0 报告配置要求](https://superset.apache.org/admin-docs/6.1.0/configuration/alerts-reports/)

30. **❌ 报告“创建者”与实际执行身份没有核对。**  
    **出处：P5-S4：“由该科室权限账号创建”。** 6.1.0 默认执行者配置为 OWNER，不能只检查创建者。需要核实所有者及实际执行身份的科室范围，避免跨科室所有者影响结果。SMTP 配置更改后也不能只重启 beat；实际发送任务的 worker 必须加载新配置。[6.1.0 执行者配置](https://github.com/apache/superset/blob/6.1.0/superset/config.py)

31. **❌ sjzc 不能按所写方式直接提供完整接库清单。**  
    **出处：§2“见技能内配置”、P4-S1。** 只读查看该技能及脚本可知，`systems` 输出系统名、表数、字段数和连接数，不输出库型、地址和账号密码；凭据由平台受控解析。应另行安排取得连接描述与独立只读凭据的步骤，不能让执行者期待 `/sjzc` 输出可复制进 Superset 的连接串。

32. **❌ “另一个 AI”执行所需的工具依赖不完整。**  
    **出处：P4-S1、P5-S0、P5-S1。** 计划把执行者限定为“本机 ZCode”，却未给出其他 AI 如何调用 sjzc、所需 SSH key、规则文件和运行环境。用户同步又在 Linux 宿主 cron 执行，但驱动只安排安装在 Windows venv 和 Superset 镜像中；宿主 Python、依赖及启动方式均缺失。

33. **❌ “接入各业务系统”与“只连 ODS”的关系没有解释清楚。**  
    **出处：§2 红线、P4 目标、P4-S2/S3、P4 验收。** 一处要求各系统逐库接入，一处要求只连 ODS；验收又缩为“每个已获凭据的库”。应列明约 20 个系统分别通过源库、ODS 镜像还是其他路径供数，以及未接入系统的状态，否则局部连接成功也可能被记为完成 U6。

34. **❌ 界面禁 DML 不能替代数据库只读权限；“设列权限”也缺少实现。**  
    **出处：P1-S6、P4-S2/S3。** 应以实际数据库授权保证只读，界面限制只能辅助。“敏感列拆数据集或设列权限”给出了未落地的替代项：本方案没有实现列级授权，应具体采用只读视图或移除敏感列，并验证其他入口不能绕过。[Superset 安全边界说明](https://superset.apache.org/admin-docs/6.1.0/security/)

35. **❌ 核验 SQL 没有继承平台的大表门禁。**  
    **出处：P4-S3：“每个数据集一条校验 SQL，行数量级与 sjzc 直查一致”。** 未限定患者/就诊键、时间窗、超时和查询规模，可能被执行者写成全表 `COUNT(*)` 或扫描。sjzc 明确有大表门禁和限量要求；数量核验应采用受控窗口或已有统计，而不是笼统“直查一致”。

36. **❌ 自建镜像可能把驱动装到错误的 Python 环境。**  
    **出处：P2-S2。** 6.1.0 官方镜像使用 `/app/.venv`；方案直接执行 `pip install`，没有明确目标解释器。官方示例使用激活虚拟环境后的 `uv pip install`。`pip list` 也不能证明应用解释器能导入驱动，应检查应用实际运行环境。[6.1.0 镜像扩展说明](https://superset.apache.org/admin-docs/6.1.0/installation/docker-builds/)

37. **❌ mysqlclient 构建依赖没有备齐。**  
    **出处：P2-S2 风险注记：“镜像内已含 build 工具”。** lean 镜像不能这样假定；官方构建过程会清理临时编译工具，mysqlclient 还需要客户端开发库和 `pkg-config`。改用 PyMySQL 也应同步修改安装清单和 URI。[官方镜像安装脚本](https://github.com/apache/superset/blob/6.1.0/docker/pip-install.sh)、[mysqlclient 构建要求](https://github.com/PyMySQL/mysqlclient#linux)

38. **❌ 两处连接串模板需要修正。**  
    **出处：P4-S2、P1-S6。** mysqlclient 对应的 SQLAlchemy 驱动名是 `mysqldb`，应使用 `mysql+mysqldb://`，不是 `mysql+mysqlclient://`。Oracle 的 SID 也不能将 `?sid=orcl` 当作无需验证的通用替换；应按已选方言使用 SID 路径或明确 DSN。[MySQL 官方方言文档](https://docs.sqlalchemy.org/en/20/dialects/mysql.html#module-sqlalchemy.dialects.mysql.mysqldb)、[Oracle 连接规则](https://docs.sqlalchemy.org/en/20/dialects/oracle.html#connecting)

39. **❌ 离线介质尚不完整，备用路线尤其不足。**  
    **出处：P2-S3/S6、P3-S0。** 主线没有 Docker Engine、containerd、Compose 插件及匹配系统的依赖包。备用路线只有 wheels 下载命令，缺 Python、Redis、系统库、Chromium 本体和依赖、完整 systemd 服务及安装步骤。Playwright wheel 不等于浏览器离线介质。

40. **❌ 版本、平台和校验清单未形成可复现契约。**  
    **出处：D5、P2-S2/S3/S4/S6。** 一处要求最新 6.1 补丁版，全部命令却写死 6.1.0；驱动未锁版本，配套镜像使用浮动标签；目标系统未核查就固定 x86_64 wheels。应锁定版本、架构和镜像 digest。`certutil` 输出也不能直接当成 `sha256sum -c` 所需的清单格式。

41. **❌ “本地开发→服务器部署”缺少成果迁移步骤。**  
    **出处：§0 U6、P1-S7、P2-S4、P3。** 没有安排本地数据集、图表、仪表盘和定制代码如何导出、打包、导入及校验。`pip freeze` 只记录依赖，不能迁移本地已做出的报表成果。

42. **❌ 生产初始化、就绪检查和服务计数不一致。**  
    **出处：P3-S3/S5、P3 验收、§11。** PostgreSQL 要点未给出与 URI 中 `superset` 用户匹配的用户及密码配置；缺少数据库就绪等待和初始化成功依赖。实际列出六个常驻服务加一个 init，验收却要求“五服务全部健康”；init 正常状态应是成功退出，不能要求所有服务都 Up。

43. **❌ 重启验收没有证明自动恢复。**  
    **出处：P3 验收：“宿主重启后 docker compose up -d 全栈自恢复”。** 重启后人工执行 `up -d` 是手动恢复。应在不执行启动命令的情况下验证 Docker 服务自启、容器恢复、健康状态及任务调度恢复，并单独处理一次性 init。

44. **❌ 生产安全配置仍未闭合。**  
    **出处：D5、P3-S3/S4、P3 验收。** HTTP 登录、`SESSION_COOKIE_SECURE=False` 被允许一直延后，验收没有要求 HTTPS；反代配置、可信转发头、端口暴露范围没有给出。CSP 又用简化字典替换默认配置，并另设同名响应头，需要核验界面、图表和嵌入是否被阻断或覆盖。本地 debug 服务也绑定所有网卡而非环回地址。[6.1.0 反代配置说明](https://superset.apache.org/admin-docs/6.1.0/configuration/configuring-superset/)

45. **❌ 凭据实际落点与方案自身守则不一致。**  
    **出处：P3-S1/S2/S4、§13 第5条；[核查脚本第8行](/F:/python/superset/review/round-3/核查_服务器.py:8)。** 目录创建命令漏了 `secrets`；生成命令没有写文件或设置权限；配置要求把密钥直接粘入 Python；核查脚本又硬编码 SSH 密码。用户授权记录连接信息是明确的，但不等于必须硬编码到代码，方案自身也写了“不进代码”。

46. **❌ 备份验收与灾难恢复方案不足。**  
    **出处：P3-S6、P3 验收、§12。** dump 大于 1KB 不能证明能恢复。缺少恢复命令和演练、原 `SECRET_KEY` 的安全备份、配置及辅助表恢复、备份失败告警和异机副本。镜像重导只能恢复程序，不能恢复用户、报表和数据源配置；缺失原密钥还可能无法解密保存的连接凭据。[元数据库内容与备份要求](https://superset.apache.org/admin-docs/6.1.0/installation/docker-compose/)

47. **❌ P3“回退”实际是卸载，且与断点续作声明不一致。**  
    **出处：P3 回退、§5、§13。** 删除镜像并 `rm -rf /data/superset` 会删除部署状态，不能等同版本回退。还没有清理 cron、systemd 等步骤，却称“无其他残留”。`CREATE DATABASE`、创建 admin 等步骤也未给出存在性检查；进度文件不能独自保证失败重做幂等。

48. **存疑：服务器核查记录的结论超过现有证据。**  
    **出处：§3、P3-S0；[核查脚本](/F:/python/superset/review/round-3/核查_服务器.py)。** 少数端口超时不能证明“整机不可达”，1521 开放也不能证明 Oracle 认证及 Thin 连接可用。脚本还存在目标主机前多余空格的外网探测、自动接受 SSH 主机密钥、未记录远端命令退出码等问题，可能在检查失败后仍输出 DONE。现稿没有附原始结果，本次未复测这些记录。

49. **存疑：工期和资源估算缺少支撑。**  
    **出处：§5、P3-S0、附审查关注点4/6。** 信息科“1～2人”是运维人员规模，不是并发用户规模。4C8G、四个 web worker、两个任务进程及每库连接池，需要结合报表刷新、截图、查询和导出并发验证。认证算法未确定、离线包未齐备时，P3一天、P5两三天应标为条件性估算。

50. **存疑：“几个系统”被解释为一个系统的五个阶段。**  
    **出处：用户原话、§0 U1、§1。** 结合工作区已经主推 Superset，这个解释有依据；但 P1～P5 都围绕同一系统，不能仅凭“五个计划”证明满足“几个系统”的原意。若用户指 Superset、明细查询服务、门户集成等几个交付系统，后两者目前没有完整计划。

有两项判断可以保留：**✅ PostgreSQL 作为 Superset 元数据库的选择合理**，用户说“可以使用数据中心”并不是强制要求 Oracle 作元数据库；**✅ D5 对两项 CVE 影响 `<6.0.0` 的描述得到官方记录支持**。但新增 Oracle 辅助表是否必要、如何读写和恢复仍需补齐，而且 U1～U9 对照不能替代 v2 的 R1～R6 产品验收。[官方元数据库支持范围](https://superset.apache.org/admin-docs/6.1.0/configuration/configuring-superset/)、[23980 官方记录](https://github.com/CVEProject/cvelistV5/blob/main/cves/2026/23xxx/CVE-2026-23980.json)、[23982 官方记录](https://github.com/CVEProject/cvelistV5/blob/main/cves/2026/23xxx/CVE-2026-23982.json)
