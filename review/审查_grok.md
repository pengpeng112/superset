先按只读约束核对需求原文、方案和仓库内参考材料，再独立评估覆盖度与缺口。这是方案对需求的只读核查，不是 git 代码审查。接下来会读 reviewer 原则、方案、需求原文和同目录参考材料。先定位原始需求文件，并并行核验方案里的关键论断与候选工具。接下来核验 REST API、嵌入、RLS、Grafana/DataEase 排除理由，以及是否还有更合适的开源替代。**独立结论：维持 Apache Superset 作为主推方向，但本方案不能按现稿直接授权实施。** R1–R6 的硬组合（外部 AI 经 API 建报表 + Oracle 直连 + 无收费墙 + 行级权限 + 嵌入 + Excel）目前没有更稳妥的开源替代能全占；方案对这条主线的判断方向对。同时，§1 把本轮对 AI 的操作指令写成产品需求 R7，§3 有多条论断过时或过满，双轨导出在医院场景有治理缺口，1–2 人运维负担被低估。应先修正事实与风险处置，再做试点，不要按 §4 直接部署。

依据：方案原文、同目录 `参考_需求与论断清单.md`、Apache/Grafana/DataEase/Metabase/Wren 官方文档与 GitHub（2026-10 检索）。

---

## 一、需求覆盖与忠实度

用户原话（方案 §1）是两层：历史六轮功能需求，加上本轮「对文件内需求进行分析，看看 GitHub 或还有没有更合适的；我还希望你能够在我本地进行修改等」。参考清单只列 R1–R6。方案把本轮后半句升格为 R7「AI 持有本地执行通道」。

| 需求 | 方案落点 | 判断 |
|---|---|---|
| R1 开源、直连 Oracle/MySQL、AI 参与、功能丰富 | §3 论断 1/2/3/14，轨道一 | **覆盖，偏乐观。** 「功能丰富」落在看板/SQL Lab，医院常见的交叉表、多级表头、套打、填报没有落点。 |
| R2 无收费墙 + 导出 Excel | 论断 1、5 | **意图覆盖。** DataEase 排除正确。Excel 一键导出真实存在，但默认同步上限、图表类型、存储后端都有条件，方案写成「原生一键」过满。 |
| R3 外部 AI 经 API 把报表写进 BI + 人工 GUI | 论断 3 + 原生 Explore | **方向覆盖，成熟度未证。** REST 能建 dataset/chart/dashboard 和 YAML/ZIP 导入。图表 `viz_type`/`params`/`position_json` 复杂，公开的「AI 全自动建看板」案例少，风险 2 写了，§4 仍按可实施步骤排。 |
| R4 上百万条查询与导出 Excel/CSV | 论断 6/7 + 轨道二 | **导出半覆盖，查询未覆盖。** 网页端百万行浏览会卡死浏览器；轨道二只解决导出，不解决「在系统里查询百万行」。xlsx 单表 1,048,576 行是格式上限。 |
| R5 角色 + 科室/人员行级不一致 | 论断 8/9/10 | **能力覆盖，运维低估。** RLS 是开源内置；科室规则要按数据集配，30 个科室 × 多数据集要模板化。AD 组映射在医院经常对不齐「科室」。 |
| R6 嵌入 OA/门户/HIS | 论断 11/12 | **能力覆盖，包名过时。** Guest Token + `rls` 条款可用。论断 12 让开源部署改用 `@preset-sdk/embedded`，与 Apache 官方 `@superset-ui/embedded-sdk` 不符。 |
| R7「在我本地进行修改」 | §3「ZCode CLI 即本地通道」 | **忠实度错误。** 这是用户对本轮 AI 的操作请求，不是 BI 产品功能。参考清单无 R7。本轮约束是只读，R7 既改写了意图，也无法在本轮兑现。 |

背景里的 SQL Server、Vastbase、内网、本地 LLM、1–2 人信息科，方案 §2 写了，论断和步骤没有同等权重：SQL Server 驱动未进 14 条；内网离线拉镜像/Playwright/Chromium 未写；官方 compose 当生产路径不合适。

---

## 二、14 条论断独立核查（2026-10）

| # | 方案表述 | 核查 | 风险 |
|---|---|---|---|
| 1 | Apache 2.0，无企业版无付费墙 | **成立。** 软件本身无功能收费墙。Preset 是托管商业服务，不构成开源版付费墙。EMBEDDED_SUPERSET、ALERT_REPORTS、ALLOW_FULL_CSV_EXPORT 等默认关闭，是配置开关。 | 把「免费」理解成「开箱即用」会在部署时撞墙。 |
| 2 | oracledb 直连 Oracle | **基本成立。** 当前官方页写 `oracledb`、连接串 `oracle+oracledb://`。旧 6.0 文档仍写 `cx_Oracle`；社区仍有 `ModuleNotFoundError: cx_Oracle`，需别名。Oracle 引擎能力分 48/201，低于常见数仓。 | 院内 Oracle 常用 SID/Service Name/Instant Client，thin 模式不够时要 thick，内网装客户端麻烦。 |
| 3 | 全套 REST + YAML/ZIP + JWT | **成立。** 官方 API：dataset/chart/dashboard CRUD，import/export，JWT login，另有 RLS 8 个端点。 | POST 建 chart 要拼复杂 JSON；导入是 multipart ZIP。AI 更稳的路径是 YAML 包导入，方案步骤 3 把 API 直建写得过顺。部分写操作还要 CSRF。 |
| 4 | 社区 Superset MCP Server | **过时/偏低。** 已有 SIP-187，Preset 把 MCP 贡献进开源。R3 要的是 REST 建报表，MCP 是加分项。 | 把 MCP 当 R3 证据会偏题；院内部署 MCP 还要再开一个进程和鉴权面。 |
| 5 | 仪表板原生一键导出 xlsx，每图一工作表 | **功能存在，条件被省略。** 官方 *Exporting Dashboard Data to Excel*：每图一 sheet、跟当前筛选、需 `can_export`。默认同步合计行数不超过 `EXCEL_EXPORT_SYNC_MAX_ROWS`（默认 10 万）；无 query context 的图会被跳过；大导出要 `EXPORT_STORAGE` + worker，历史上还绑过 S3。 | 「一键」在默认配置下扛不住百万行；医院内网往往没有 S3。 |
| 6 | 行数无硬编码，ROW_LIMIT/SQL_MAX_ROW 可调到百万；issue #35139 官方确认 | **过满。** 两参数可调。图表自己的 `row_limit`、`TABLE_VIZ_MAX_ROW_SERVER`（默认 50 万）、`ALLOW_FULL_CSV_EXPORT`、worker/浏览器内存都是额外上限。#35139 是工单，Dosu 机器人 + 维护者评论，不是规范承诺。 | 只改两个配置，导出仍可能停在 5 万或 50 万。 |
| 7 | 百万行须异步；xlsx 单 sheet 1,048,576 | **成立。** Excel 格式上限属实。大导出必须异步，否则超时/OOM。 | 轨道二因此有必要；方案没写轨道二如何套用同一套科室 RLS。 |
| 8 | RLS 开源内置，Jinja `current_username()` | **成立。** Security → Row Level Security；Guest Token 的 `rls` 条款可按人过滤。Jinja 常要 `ENABLE_TEMPLATE_PROCESSING`。Guest token 里 `username` 为空时 RLS 会被跳过（讨论 #36494）。 | 嵌入门户时宿主发错/漏用户名会漏数。RLS 是行级，列级要拆数据集。 |
| 9 | RBAC：Admin/Alpha/Gamma/Public + 自定义 | **成立。** | `superset init` 会重置内置角色权限，手工改内置角色升级后会被盖掉。 |
| 10 | LDAP/AD + OAuth2，`AUTH_ROLES_MAPPING` | **能力成立，落地难。** Flask-AppBuilder 支持。LDAP 组映射现场经常失败（#32165 等）。`AUTH_ROLES_SYNC_AT_LOGIN=True` 会冲掉手工角色。 | 医院 AD 里「科室」往往不是现成组，R5 不能只靠这一条配置。 |
| 11 | Guest Token 原生嵌入，token 带 rls_rules | **成立，用词略混。** POST `/api/v1/security/guest_token/` 请求体字段是 `rls`，JWT 内存成 `rls_rules`。须 `EMBEDDED_SUPERSET=True`、改掉默认 `GUEST_TOKEN_JWT_SECRET`、配 CORS/frame-ancestors。5.0 后该开关默认 False，关着则嵌入 RLS 不生效。 | 宿主必须写发牌接口；密钥默认值不改等于谁都能伪造访客。 |
| 12 | 嵌入导出须用新版 `@preset-sdk/embedded`，旧 `@superset-ui/embedded-sdk` 有 bug（#21829） | **对开源部署不成立。** Apache 仓库官方包仍是 `@superset-ui/embedded-sdk`（约 0.4.0），可用 `iframeSandboxExtras`。#21829 是 2022 年 npm 未跟上仓库的问题。2026-06 的 #40933：嵌入态、guest token、超过约 10 万行的流式 CSV 会 401。 | 按方案去装 Preset 商业包，供应链和许可证都不清；百万行嵌入导出仍可能失败。 |
| 13 | Alerts & Reports 开源免费内置 | **功能免费，默认不可用。** 须 `ALERT_REPORTS=True`、Celery beat/worker、SMTP。7.0.0 文档：截图只走 Playwright + 无头 Chromium，Selenium/Firefox 不再支持。 | 内网 worker 镜像要预装浏览器；医院 SMTP 和截图链路是运维大头。 |
| 14 | 有简体中文语言包 | **有包，默认不全。** locale 是 `zh`。`LANGUAGES` 默认为空则无语言选择；部分 Docker 5.0+ 要 `BUILD_TRANSLATIONS=true` 才带翻译；覆盖不完整，界面会中英混杂。 | 科室用户会觉得「没中文」。 |

---

## 三、排除名单：对的、错的、漏的

**排除理由成立**

- **DataEase**：专业版 X-Pack 锁行列权限、定时报告、开放 API、嵌入（约 6 万/套）。用户用过并否定。排除正确。
- **Grafana**：官方写明 Oracle 插件是 Enterprise；定时 PDF Reporting 也是企业功能。排除正确。
- **SQLBot**：内置问答，与 R3「外部 AI 当报表开发员」不符。降级正确。
- **AJ-Report / Datart / JimuReport 免费版行数墙**：安全或停更或行数限制，作主 BI 排除合理。Jimu 仍适合作为「中国式报表」补丁，方案完全丢掉了这条互补。

**排除理由写错，结论仍可维持**

- **Metabase**：「Oracle 驱动仅付费版」不成立。开源版官方支持 Oracle，因 Oracle JDBC 许可不能随包分发，自行把 `ojdbc8.jar` 放进 `plugins/` 即可（与任何 Java 工具相同）。真正的墙是：行/列权限、SAML/JWT SSO、交互式/整应用嵌入在 Pro。按 R2+R5+R6 仍应排除，理由必须改。

**排除/观察已过时**

- **Wren AI**：方案写 issue #710 仍开放、无 Oracle。#710 页面仍 Open，但 0.23.0（2025-06）已加 Oracle，官方有 *Connect Oracle* 文档。Wren 仍是 ChatBI/语义层，不是带门户嵌入和程序化建看板的报表系统，不宜主推，Oracle 这条理由要改。

**方案未评估、值得写进开放问题的候选**

- **Helical Insight**（GitHub `helicalinsight/helicalinsight`，AGPL-3.0，约 1.1k star）：厂商 2026-08 起宣传社区版含像素级分页报表、RLS、嵌入、SSO、REST、Oracle、BYO-LLM。这正打在医院「中国式报表 + 无收费墙」上。社区比 Superset 小一个数量级，许可证从 Apache 迁到 AGPL，导出带品牌，REST 能否像 Superset 一样让外部 AI 创建报表未核实。**不能据此换主推**，属于方案对开放问题 1 的遗漏，应列为「核实后再决定是否并行试点」。
- **Redash**：Oracle + 完整 REST，RLS 弱、项目经历过易主，不适合医院主系统。
- **Lightdash**：偏 dbt/数仓，院内 ODS+Oracle 现状不匹配。

没有发现能同时稳占 R1–R6 的第二个开源主产品。开放问题 1 的答案：**目前没有更合适的单一替代；有一个必须补评的 Helical Insight，以及作为报表形态补丁的 Jimu/脚本。**

---

## 四、自发问题（按严重度）

### 1. R7 改写了用户原话（忠实度，§1）

「我还希望你能够在我本地进行修改等」是对本轮执行 AI 的请求。参考清单只有 R1–R6。方案把它写成 BI 能力，再用「ZCode CLI 已覆盖」自证，循环论证。本轮唯一约束是只读，R7 在本审查里既不该成为选型条件，也无法交付本地修改。

风险：验收 §5「R1–R7 逐条有落点」会让后续执行人去造一个不存在的产品需求。

### 2. 双轨导出绕开 BI 治理（开放问题 2，实质是 P0）

轨道二：GLM 经 `$sjzc` 查数后 Python 写共享目录。百万行明细（收费、检验）恰是高敏感数据。脚本侧若未复用同一套科室 RLS、审计、水印、留存周期，等于在 BI 外面开了一条特权出数通道。方案风险 4 只问「BI 能否持有 ODS 只读账号」，没问「脚本出数谁审批、文件落在哪、如何按人过滤」。

风险：等保/病案管理追责时，BI 有 RLS、共享盘没有。

### 3. 「百万行查询」被换成「百万行导出」（R4）

用户原话：「类似 excel 表格的上百万条数据的查询和导出」。方案用「看聚合、导明细」规避网页查询。对科室人员，这是换需求。SQL Lab 把 `SQL_MAX_ROW` 调到百万会拖垮浏览器和 Oracle。

风险：试点通过导出验收，上线后用户说「查不了」。

### 4. 1–2 人运维 vs 组件清单（风险 3，§4 步骤 1）

生产最低：Web、Celery worker、beat、Redis、元数据库（须 PostgreSQL/MySQL，不能用默认 SQLite）、Playwright Chromium、SMTP、反向代理、备份。官方 compose 是开发用。内网还要镜像仓库、Python 包、Oracle 客户端。信息科 1–2 人同时管 HIS/ODS，这套是专职岗位。

风险：能装起来，不能持续升级。Superset 2→3→4→5→6 有破坏性变更。§4 未锁版本、未写元数据库、未写备份。

### 5. 中国式报表缺口未进方案风险节

`审查_zcode.md` 已自承：交叉表、套打、填报弱。方案 §3/§7 没写。医院质控、财务、上报经常要格子报表。Superset Table 做看板可以，做「一张 Excel 式报表」弱。

风险：科室要的是 Jimu/帆软形态，上线后被判「不好用」。应用轨道二脚本或并行像素级工具补，须写进方案。

### 6. 数据资产平台与 BI 直连冲突（风险 4）

背景：平台「受控限量只读 SELECT」，报表「只读账号连 ODS」。Superset 必须自己持有连接串，查询量和平台限流不是同一套闸。AI 建数据集时 SQL 指向 Oracle，等于把平台旁路掉。

风险：信息科若不允许旁路，轨道一无法落地；若允许，平台的审计/限流对 BI 失效。这是实施前置条件，不是上线后验证项。

### 7. 内网与空气间隙未写

全院内网。`docker pull`、`pip install oracledb`、`playwright install chromium`、npm SDK 都要离线。方案步骤 1「官方 compose」默认能上网。

风险：测试机都拉不齐镜像。

### 8. 嵌入安全面

Guest Token 由宿主签发，RLS 条款是字符串拼进 SQL。宿主 bug = 全表泄露。下载链接在部分版本「故意不登录、凭 job_id」，job_id 泄漏即可取走 Excel。Guest 与管理员同浏览器会串会话，导出可能丢掉 RLS（讨论 #30283）。

风险：门户嵌入是 PHI 出口，方案写成「开发量小但非零」偏轻。

### 9. 论断 12 与 2026 年真实嵌入导出问题

应按官方 `@superset-ui/embedded-sdk` + `iframeSandboxExtras`。须跟踪 #40933（嵌入流式 CSV 401）。百万行嵌入导出不能当作已满足。

### 10. 实施步骤把试点当生产清单（§4）

缺：版本钉死、元数据库、SECRET_KEY/GUEST_TOKEN 轮换、FEATURE_FLAGS 清单、AD 字段映射设计、RLS 模板、轨道二权限模型、离线制品、等保日志、患者数据脱敏。步骤 6「推广科室报表」放在嵌入试点之后，没有失败回滚。

---

## 五、对方案开放问题的直接回答

1. **有没有全占 R1–R7 的开源替代？** R7 不应作为产品条件。R1–R6：没有第二个工具能同样稳地同时提供「外部 AI 程序化建报表 + Oracle 开源直连 + 无功能墙 + RLS + 嵌入」。Helical Insight 必须补评（像素级报表更贴医院），通过前维持 Superset。Jimu 只作格子报表补丁。
2. **双轨有没有治理隐患？** 有，而且是医院场景的主隐患：第二条出数路径的 RLS/审计/留存必须与 BI 对齐，否则不能用于收费/检验等明细。
3. **14 条在 2026-10 是否仍成立？** 1、3、8、9、11、13 核心仍成立。2 成立但有驱动别名坑。5、6 过满。4、12 过时。7 的格式上限成立。10 能力成立、现场易失败。14 有包、默认体验差。Wren 的 Oracle 排除理由过时。
4. **R7 与 R3？** R7 不是 BI 能力。R3 靠 REST/YAML。ZCode 调 API 属于实施手段。本轮只读，不能在本地改环境。

---

## 六、总判与修订优先级（仍只读，不改文件）

**选型方向：继续主推 Apache Superset，不切换。**  
**方案状态：退回修订后再授权试点。** 现在按 §4 执行，会在 Oracle 驱动、Excel 上限、嵌入 SDK、中文、AD 映射、双轨泄数上分别踩坑。

修订应先做这些（给下一稿，不是本轮改文件）：

1. 删除或降级 R7，验收回到 R1–R6。
2. 改写论断 5/6/12、Metabase 排除理由、Wren Oracle 理由；官方 SDK 改为 `@superset-ui/embedded-sdk`。
3. 把双轨治理、中国式报表、内网离线、元数据库、版本锁定、FEATURE_FLAGS 清单写入风险并给出接受/缓解。
4. 轨道二必须复用科室过滤与审计，或明确禁止出敏感明细。
5. 补评 Helical Insight（许可证、API 建报表、社区、中文、Oracle 实测），结论出来前不并行铺开。
6. 试点范围收成：1 个 Oracle 数据集 + 1 张看板 + 1 条科室 RLS + 一次万级（不是百万级）Excel 导出 + 一次门户 Guest Token。百万行只做脚本轨道的受控试验。

我未改任何文件。未能在医院内网实连 Oracle/Vastbase，论断 2 与风险 1 仍须你们在测试机上跑通后再锁方案。
