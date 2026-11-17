# 开源 BI 选型复核：需求清单与事实论断（Apache Superset）

> 用途：交由另一个 AI 独立复核。调研时间 2026-10-03 ~ 10-04，信息来自 GitHub/官方文档/网络检索。
> 请复核方重点核实第 4 节每条论断是否成立、第 5 节排除理由是否有遗漏的更优替代、第 7 节风险是否可控。

## 1. 使用方背景

- 山东省某三甲耳鼻喉专科医院信息科，IT 人员 1~2 人，非全职开发团队
- 已有自建"数据资产平台"：统一接入约 20 个业务系统（HIS、LIS、PACS、电子病历、HRP、OA、体检、病理等），库型为 **Oracle + Vastbase（openGauss 系）+ SQL Server + MySQL**，平台提供受控的限量只读 SELECT
- 已有 AI 工作流：GLM 大模型 Agent（ZCode CLI）可通过上述数据资产平台执行只读查询（内部称 $sjzc 技能）
- 环境约束：全院内网、无外网；大模型必须本地私有化（DeepSeek/Qwen，OpenAI 兼容接口）；患者数据不出院
- 数据访问原则：报表系统用只读账号连 ODS/数据中心，不直连生产 HIS

## 2. 完整需求清单（按用户提问顺序，R6 条件均必须满足）

- **R1 基础需求**：开源报表查询系统；适合 AI 参与；承担医疗信息报表的统计与查询；**直连 Oracle、MySQL 等各类数据库**；AI 能生成报表给院内各人员使用；功能尽量丰富
- **R2 反馈一**：曾用 DataEase，X-Pack 收费功能多 → **排除一切"核心功能锁付费墙"的工具**；必须支持**导出 Excel**
- **R3 关键澄清（工作流核心）**：不是要"BI 内置 AI 问答"（SQLBot 式对话问数不需要）。要的是：**GLM/ZCode 这类外部 AI 通过数据资产平台查好数后，以"报表开发员"身份直接把报表写进 BI 工具**（即 BI 必须开放完善的 REST API 或可编程的报表定义格式）；同时 BI 必须支持**人工在图形界面制作报表**
- **R4 大数据量**：支持上百万条数据的查询，并导出为 **Excel 或 CSV**
- **R5 权限**：有角色/权限体系；**科室、人员不同层级登录后看到的同一报表数据不一致**（行级权限）
- **R6 嵌入**：支持把报表**嵌入到其他系统**（院内 OA/门户/HIS 门户）

## 3. 当前选型结论

**主推：Apache Superset（单一主推）**，配套双轨架构：

- 轨道一（常规报表）：Superset 承担看板/报表/权限分发/Excel 导出/定时邮件；GLM 通过 REST API 建报表，人工可在 GUI 精修
- 轨道二（超大明细）：百万行级明细流水（收费明细、检验结果等）不走 BI，由 GLM+数据平台只读查询后用 Python 分批流式写 CSV（或分 sheet 的 xlsx）到共享目录

**备选**：SuperSonic（腾讯音乐，Apache 2.0，ChatBI+语义层一体化，但 Oracle 支持未官方确认，需实测）；DB-GPT（Apache 2.0，适合深度定制，无现成报表门户）。

## 4. 关于 Superset 的事实性论断（请逐条核实，标注 ✅/❌/存疑）

| # | 论断 | 主要依据 |
|---|------|---------|
| 1 | Apache 2.0 协议，ASF 顶级项目，**无企业版、无任何功能付费墙** | superset.apache.org |
| 2 | Oracle 可直连：安装 python-oracledb 驱动 + SQLAlchemy 连接串即可 | 官方 Installing Database Drivers 文档 |
| 3 | **全套公开 REST API（OpenAPI 规范）**：POST /api/v1/dataset、/chart、/dashboard 增删改查；支持 assets 打包为 YAML/ZIP 导入导出（/api/v1/dashboard/import 等），JWT 认证 | superset.apache.org/docs/api |
| 4 | 已存在社区的 Superset MCP Server（可供 Agent 调用） | MCP 目录站收录 |
| 5 | 仪表板**原生一键导出 Excel（.xlsx，每个图表数据一个工作表）**；图表可导出 CSV/XLSX | 官方 user-docs: Exporting Dashboard Data to Excel |
| 6 | 行数上限可配置、无硬编码：图表导出走 ROW_LIMIT（默认 5 万）、SQL Lab 走 SQL_MAX_ROW（默认 10 万），均可调至百万级 | GitHub issue #35139 官方确认 |
| 7 | 百万行导出必须走异步（Celery + 结果后端），否则同步导出会超时/worker OOM；xlsx 单工作表格式硬上限 1,048,576 行 | 官方 Miscellaneous 文档 + Excel 格式限制 |
| 8 | **RLS 行级权限为开源版内置**（Security→Row Level Security）：数据集+角色绑定 SQL 过滤子句，支持 {{ current_username() }} 等 Jinja 动态变量；可实现科室/人员层级看不同数据 | 官方 Security 文档 |
| 9 | RBAC 角色体系内置（Admin/Alpha/Gamma/Public + 自定义角色），数据集/图表/仪表板可按角色授权 | 官方文档 |
| 10 | 支持 LDAP/AD 域、OAuth2 单点登录，域组→角色自动映射（AUTH_ROLES_MAPPING + AUTH_ROLES_SYNC_AT_LOGIN） | 官方配置文档 |
| 11 | **原生嵌入**：EMBEDDED_SUPERSET 特性开关 + Guest Token（/api/v1/security/guest_token/，token 可携带 rls_rules 实现嵌入态按人过滤）；前端 iframe 或官方 Embedded SDK；宿主认证后用户免二次登录 | 官方 Security/Embedding 文档 + Preset 文档 |
| 12 | 嵌入态可交互筛选并导出 CSV，但需用新版 @preset-sdk/embedded（旧 @superset-ui/embedded-sdk 有导出 bug，issue #21829） | GitHub issue #21829 |
| 13 | **Alerts & Reports（定时报表截图/邮件推送）内置于开源版免费**（需 celery beat/worker + chromium + SMTP） | 官方文档/UPDATING |
| 14 | 有简体中文语言包 | 官方 i18n |

## 5. 被排除的候选及理由（请挑战是否有误判）

| 工具 | 排除理由 |
|------|---------|
| DataEase | X-Pack 收费墙多（定时报表/水印/行级权限等），用户实际用过并否定；开放 API 不完整 |
| Metabase | Oracle 驱动仅付费版提供 |
| Grafana | Oracle 数据源插件是 Enterprise 收费；定时 PDF 报表（Reporting）也是 Enterprise 功能；AGPL |
| Wren AI | Oracle connector 至今未落地（GitHub issue #710 仍开放） |
| SQLBot（飞致云） | 定位是"BI 内置 AI 问答"，与 R3 要求的外部 AI 建报表路线不符；降为可选非必需 |
| JimuReport | 免费但非纯开源（核心以 jar 发布），v1.7.0 起免费版限 10 万行等；无程序化建报表 API |
| SuperSonic | 理念契合（语义层管理指标口径）但官方数据源列表无 Oracle，Excel 导出未确认 → 列为试点观察 |
| DataGear | LGPL 社区版可用、支持 Oracle/达梦，但无 AI、无程序化建报表 API |
| AJ-Report | 2025 年曝出 RCE 漏洞且仓库更新放缓，不进医院生产网 |
| Datart | 2022 年后基本停更 |
| DB-GPT | 保留为深度定制备选（框架无现成报表门户） |

## 6. 目标工作流（选型通过后实施）

```
用户（自然语言提需求）→ GLM Agent(ZCode)
  1. 经数据资产平台查表结构、跑只读 SELECT 确定统计口径与 SQL
  2. 调 Superset REST API：建数据集(SQL 指向 Oracle 连接)→图表→仪表盘
  3. 配角色授权 + RLS 规则（或生成 YAML 包导入）
  4. 发链接 / 配置 Alerts & Reports 定时邮件；如需嵌入，宿主系统接 Guest Token
科室人员：浏览器看报表（或 OA 门户嵌入页）/ 一键导出 Excel / 可在 GUI 微调
```

## 7. 待验证风险（请复核方重点评估可行性）

1. **Vastbase 兼容性**：不在 Superset 官方数据源列表，理论上走 PG/openGauss 兼容接入，未实测
2. **AI 建报表工作流成熟度**：Superset API 建报表是标准用法，但"AI 全自动生成报表"无广泛公开案例，需先端到端试点 1~2 张真实报表验证
3. **部署复杂度**：组件较多（web + celery worker + beat + Redis + 结果后端 + chromium 截图 + 元数据库 + SMTP），对 1~2 人 IT 团队的运维负担需评估
4. **数据平台凭据问题**：数据资产平台是"受控限量"查询通道；Superset 需要自己的 Oracle 只读账号直连 ODS —— 需确认资产平台侧允许 BI 工具持有独立只读凭据（不绕过平台管控的前提下）
5. **RLS 行级非列级**：敏感列需拆数据集+授权变通
6. **中文与易用性**：有中文包但配置偏工程化，信息科与科室用户有学习曲线

## 8. 建议复核方回答的问题

1. 第 4 节论断在 Superset 当前最新版本（2026-10）中是否仍然成立？有无版本变动/废弃？
2. 是否存在更符合 R1~R6 全部条件的其他开源工具被我们遗漏（尤其：开放 API 供外部 AI 程序化建报表 + 直连 Oracle + 无付费墙 + 中文 + 行级权限 + 嵌入 + Excel 导出）？
3. 第 7 节风险中哪几条是致命的、哪几条可接受？
4. 若两条轨道（BI + 脚本导出）不合并，医院实际使用中会有什么治理问题？
