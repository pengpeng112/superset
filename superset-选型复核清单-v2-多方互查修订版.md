# 开源 BI 选型清单 v2（多方互查修订版）

> 本文件是 `superset-选型复核-需求与论断清单.md`（v1）经四方 AI 互查（GLM 起草+初审 / Kimi / Grok / Codex 独立审查→对辩→证据终审）后的修订落地版，2026-10-04。
> 证据链：`review/round-2/`（方案.md、审查_zcode.md、审查_kimi.md、审查_grok.md、检查_codex.md、分歧表.md、对辩.md）。
> **总判定：维持 Apache Superset 主推（三方独立同判），v1 的 14 条论断中 11 条成立/基本成立、3 条已修正，排除表 3 处理由修正、4 个候选补评；R4 验收口径升级；新增 6 条风险。**
> **round-3 补注（2026-10-04，部署计划互查）：论断 2 加注 SQLAlchemy 1.4 兼容条件（证据终审，见 `review/round-3/分歧表.md` A1）；部署实施细节以 `superset-部署与安装长任务计划-v1-多方互查修订版.md` 为准。**

## 1. 使用方背景（不变）

山东某三甲耳鼻喉专科医院信息科 1~2 人；数据资产平台接入约 20 系统（Oracle+Vastbase+SQLServer+MySQL），受控限量只读；全院内网；LLM 本地私有化；报表连 ODS 只读账号。

## 2. 需求清单（修订：R7 剔除，R4 口径升级）

| # | 需求 | 修订说明 |
|---|---|---|
| R1 | 开源、直连 Oracle/MySQL 等、AI 参与生成报表、功能丰富 | 不变（"功能丰富"注脚：中式复杂报表/套打不在其内，见风险 R-新4） |
| R2 | 无核心功能收费墙 + 导出 Excel | 不变 |
| R3 | 外部 AI（GLM/ZCode 经数据平台查数）把报表写进 BI + 支持人工 GUI 制作 | 措辞放宽：写入通道=REST API **或可编程报表定义文件**（YAML/ZIP/XML 等）均可 |
| R4 | 上百万条数据的**查询**与导出（Excel/CSV） | **验收口径升级**：网页百万行整表浏览不作要求；必须提供**科室自助明细查询入口**——中文固定模板筛选→命中明细翻页/核对样本→按同一条件异步导出→任务状态与取件；验收=科室账号自助完成全流程 |
| R5 | 角色/权限 + 科室/人员行级数据隔离 | 不变（补充：定时邮件报表按执行用户视角生成，不按收件人重滤——见风险 R-新5） |
| R6 | 嵌入其他系统（OA/门户/HIS） | 不变（SDK 与安全细节修正，见论断 12/风险） |
| ~~R7~~ | ~~AI 本地修改~~ | **剔除**：三方一致判定为"对复核 AI 的工作方式指令"非产品需求，不作为选型条件 |

## 3. 论断表（修订版，基于 Superset 正式版 6.1.0，2026-10）

| # | 论断 | 状态 | 修订内容 |
|---|---|---|---|
| 1 | Apache 2.0 无付费墙 | ✅ | 不变（注意：EMBEDDED_SUPERSET/ALERT_REPORTS 等默认关闭是配置开关，非收费） |
| 2 | Oracle 直连 | ✅+条件 | oracledb Thin 模式要求 Oracle ≥12.1；旧库需 Thick+Instant Client（内网安装成本）；~~连接串 `oracle+oracledb://`~~ **round-3 加注：Superset 6.1.0 依赖 `sqlalchemy>=1.4,<2`，SA 1.4 下 oracledb 须 module mapping（`sys.modules["cx_Oracle"]=oracledb`）+ 连接串 `oracle://`；`oracle+oracledb://` 仅适用 SA 2（python-oracledb 官方 appendix_d）** |
| 3 | 全套 REST API + YAML/ZIP 导入导出 + JWT | ✅ | 补：建 chart 的 JSON 复杂（vizType/params），**AI 建报表优先走 YAML 包导入**；部分写操作需 CSRF |
| 4 | MCP | ✅**升级** | **6.1.0 官方内置 mcp_service**（创建虚拟数据集/图表/仪表盘），不再是"社区方案"；官方 AI 使用指南已发布 |
| 5 | Excel 导出 | ⚠️**修正** | 图表级 CSV/XLSX=正式版可用；**仪表盘级整盘 xlsx=Next（未发布版）功能**，同步上限 EXCEL_EXPORT_SYNC_MAX_ROWS=10 万行，更大需 S3/GCS+Celery+SMTP——内网无对象存储时不可用；版本计划须写明 |
| 6 | 行数上限可调 | ⚠️**修正** | 非仅两个参数：ROW_LIMIT（5万）/SQL_MAX_ROW（10万）/**TABLE_VIZ_MAX_ROW_SERVER（50万）**/DEFAULT_SQLLAB_LIMIT（1000）/DISPLAY_MAX_ROW（1万）/图表自身 row_limit 分层生效；#35139 为社区工单非官方承诺 |
| 7 | 百万行导出机制 | ⚠️**修正** | CSV 有同步流式导出（stream_results+fetchmany）；XLSX 构建/超大数据集仍需后台任务+内存回收；xlsx 单 sheet 硬上限 1,048,576 行（含表头则数据 1,048,575） |
| 8 | RLS 行级权限 | ✅+条件 | Jinja 动态变量需开 **ENABLE_TEMPLATE_PROCESSING**；Guest Token 的 `username` 为空时 RLS 被跳过（#36494）；RLS_IN_SQLLAB 默认关闭 |
| 9 | RBAC | ✅+条件 | 仪表盘级角色绑定需 DASHBOARD_RBAC（默认关）；`superset init` 会重置内置角色权限——自定义角色不要基于内置角色改 |
| 10 | LDAP/AD+OAuth2 | ✅+落地难 | AUTH_ROLES_SYNC_AT_LOGIN 会冲掉手工角色；医院 AD"科室"往往不是现成组，映射需设计 |
| 11 | Guest Token 嵌入 | ✅ | 请求体字段是 `rls`（JWT 内部才是 rls_rules）；须 EMBEDDED_SUPERSET=True（5.0 后默认 False）+强制换 GUEST_TOKEN_JWT_SECRET+CORS/frame-ancestors |
| 12 | 嵌入 SDK | ⚠️**修正** | **用官方 `@superset-ui/embedded-sdk`**（6.1.0 README 推荐）；v1 的"@preset-sdk/embedded"作废（#21829 为 2022 旧案例）；跟踪 #40933（嵌入态流式 CSV 401，大导出嵌入场景） |
| 13 | Alerts & Reports 定时邮件 | ✅+条件 | 需 ALERT_REPORTS=True+celery beat/worker+**Playwright 无头 Chromium**（Selenium/Firefox 已不支持）+SMTP；**按执行用户视角截图，不按收件人重滤** |
| 14 | 中文语言包 | ✅+注脚 | zh 语言包存在但覆盖不全、部分版本需 BUILD_TRANSLATIONS=true，界面中英混杂，科室预期要管理 |
| **15（新增）** | **版本与安全基线** | ✅新增 | **部署 ≥6.1.x**（CVE-2026-23980 SQL 注入、CVE-2026-23982 越权改数据集均影响 <6.0.0；CVE-2023-27524 默认 SECRET_KEY 教训）——强制换 SECRET_KEY、关调试、建立补丁节奏 |

## 4. 排除表（修订：3 处理由修正 + 4 个补评候选）

**维持排除（理由修正）**：
| 工具 | 修正后理由 |
|---|---|
| Metabase | ~~Oracle 驱动付费~~ → **开源版可连 Oracle**（ojdbc8.jar 自放 plugins/）；真正排除原因：行/列权限、SAML/JWT SSO、交互式/整应用嵌入均在 Pro 付费版（R5+R6 不满足） |
| Wren AI | ~~无 Oracle connector~~ → 0.23.0（2025-06）已支持 Oracle；真正排除原因：定位 ChatBI/语义层，无报表门户与程序化建报表，不符 R3 |
| Datart | "2022 后停更"改为"维护不足"（2023 有修复、2025 有文档提交，但无实质演进） |
| AJ-Report | CVE-2024-7314（2024 公开）+维护放缓；是否排除看目标版本修复情况，但原则上不进生产 |

**维持原判**：DataEase（X-Pack 收费墙+用户否定）、Grafana（Oracle 插件与定时 Reporting 均 Enterprise）、SQLBot（BI 内置问答不符 R3，降为可选）、JimuReport（免费版 10 万行限制；**恢复为"中式复杂报表补丁"候选**）。

**新增补评候选（本轮互查发现，结论前不并行铺开）**：
| 候选 | 来源 | 要点 | 处置 |
|---|---|---|---|
| Helical Insight | Grok | AGPL-3.0、宣称社区版含像素级分页报表+RLS+嵌入+SSO+REST+Oracle+BYO-LLM，正打"中式报表+无收费墙"；社区小一个量级、REST 建 API 能力未核实 | **必须补评**（许可证/中文/Oracle 实测/外部 AI 建报表可行性） |
| Seal Report | Codex | **MIT**、Oracle/MySQL、人工设计+XML 报表定义+Web API+Excel/CSV+调度+按登录用户/组过滤，贴近"AI 直接编辑报表定义文件"路线；设计器是 Windows 桌面程序 | 值得对比试点（百万行性能/中文/权限闭环未证） |
| DataGear | Codex（理由修正） | ~~无 API~~ → 有 saveAdd 系列 REST 接口+DG_USER/DG_ROLE_NAMES 参数化按用户过滤+SXSSF 自动分 sheet 导出；LGPL、轻量、中文 | 恢复为轻量候选（接口稳定性/权限闭环待验证） |
| Knowage | Kimi | AGPL、JDBC 直连 Oracle+REST+行为模型近似 RLS+嵌入+Excel；但 Java 全家桶部署更重、中文生态近零 | 排除理由记录在案（1~2 人团队不选），不试点 |
| Redash | Kimi/Grok | 官方仓库已标注 unmaintained 归档；无 RLS | 排除（记录在案） |

## 5. 双轨架构（修订版）

- **轨道一（Superset）**：常规报表+看板+权限分发+图表级 Excel/CSV 导出+定时邮件；GLM 经 REST/YAML/官方 MCP 建报表，人工 GUI 精修
- **轨道二（百万行明细）**：**必须封装成"科室自助明细查询入口"**（中文固定模板：时间段/科室/就诊号/项目 → 命中明细翻页核对 → 按同一条件异步导出 CSV/分 sheet xlsx → 任务状态与取件），而非"信息科代跑脚本放共享目录"；实现载体可为 Superset 异步导出或脚本封装，底层无所谓
- **轨道二治理红线（三方一致）**：导出路径必须复用同一套科室数据过滤+审计留痕（谁导/导了什么/文件 ACL/留存期限/过期删除），否则不得用于收费/检验等敏感明细——这是等保与病案追责的硬要求

## 6. 风险清单（原 6 条全部保留 + 新增 6 条，共 12 条）

| # | 风险 | 处置 |
|---|---|---|
| 1 | Vastbase 兼容未实测 | 缓解：测试机实测（不只测连接——元数据读取/日期函数/分页/中文/大结果导出全链路） |
| 2 | AI 全自动建报表无广泛案例 | **降级**（官方 MCP 已内置，风险变为"需试点验证"） |
| 3 | 部署组件多，1~2 人运维负担 | 缓解：官方 compose 仅测试用；生产需 web+celery×2+Redis+**PG/MySQL 元数据库（不能用 SQLite）**+Playwright Chromium+SMTP+反代+备份；锁版本策略 |
| 4 | 数据平台凭据/旁路问题 | **升级为实施前置条件**：Superset 持独立只读凭据=平台限流/审计对 BI 失效，须信息科书面确认 |
| 5 | RLS 行级非列级 | 缓解：敏感列拆数据集 |
| 6 | 中文覆盖不全/学习曲线 | 接受+预期管理 |
| **7（新）** | **离线部署**（内网第一拦路虎） | 缓解：实施第 0 步=离线介质制备（镜像/wheel/chromium/npm 包内网制品库） |
| **8（新）** | **导出数据治理**（轨道二绕过 RLS/审计） | 缓解：见第 5 节治理红线 |
| **9（新）** | **版本与安全基线**（CVE-2026-23980/23982） | 缓解：论断 15，≥6.1.x+SECRET_KEY+补丁节奏 |
| **10（新）** | **中国式复杂报表缺口** | 处置三选一：接受（只做看板）/轨道二格式化输出/外挂 JimuReport 或 Helical Insight；须在试点期决定，勿等推广期 |
| **11（新）** | **定时邮件不按收件人重滤** | 缓解：敏感报表的 Report 由该科室权限账号创建，或只发链接不发数据 |
| **12（新）** | **Jinja 模板攻击面**（AI 生成内容接入 SQL 模板） | 缓解：AI 服务账号最小权限；模板规则人工审核；开启前读当期安全公告 |

## 7. 修订后实施步骤（选型通过后，另行授权）

0. **离线介质制备**（镜像/wheel/chromium/SDK 包）；**补评 Helical Insight 与 Seal Report**（各半天，许可证/中文/Oracle 连通/外部 AI 建报表可行性）
1. 测试机 Docker 部署 Superset **6.1.x**（官方 compose 仅测试）；元数据库用 PG/MySQL；SECRET_KEY/GUEST_TOKEN 强制换新
2. oracledb 连 Oracle 只读账号（确认 Oracle 版本≥12.1 否则 Thick 模式）；Vastbase 全链路实测；SQL Server 一并验证
3. 建 AI 服务账号（最小权限+JWT）；**端到端试点**（收窄为）：1 个 Oracle 数据集+1 张看板+1 条科室 RLS（含 ENABLE_TEMPLATE_PROCESSING）+一次**万级**（非百万级）Excel 导出+一次门户 Guest Token 嵌入；AI 建报表优先 YAML 包导入路径
4. **科室自助明细查询入口**试点（轨道二封装：模板筛选→翻页→异步导出→取件），验收=科室账号自助全流程
5. SMTP+Playwright 定时邮件（注意风险 11）；AD 域对接（科室组映射设计，先小范围）
6. 风险 10（中式报表）决策点：试点期完成三选一处置
7. 全部通过后再谈推广；每步有失败回滚

## 8. 验收标准（修订版）

- R1~R6 逐条落点（R7 已剔除）
- 论断以本 v2 表为准（15 条）；补评候选结论出来前不并行铺开
- R4 验收=科室账号自助"筛选-查看-导出"全流程（非"文件存在"）
- 越权测试：直登链接/API/嵌入态/导出文件四个面都验（不只验"菜单看不到"）
- 12 条风险各有"接受/缓解/放弃"处置
