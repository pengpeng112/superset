• 我先读取需求清单、方案和相关参考文件。

• 核查完毕。以下是我的独立复核报告（只读，未改动任何文件）。

  ---

  # 独立复核报告：医院开源 BI 选型方案（2026-10-04）

  ## 一、总体结论

  **维持"Apache Superset 单一主推"的结论，我认为成立。** R1~R6 的硬组合（开源无收费墙 + 外部 AI 经 API 程序化建报表 + Oracle 直连 + 行级权限 + 嵌入 + Excel 导出）在开源世界里 Superset 仍是无对手的正解，方案的技术路线（双轨、Guest Token 嵌入、RLS+RBAC）方向正确。

  但方案有 **3 处事实性论断需要修正**（论断 4 偏弱、论断 5 过度简化、版本底线缺失），**1 处需求忠实度问题**（R7 属误读/加戏），以及 **4 个方案完全未覆盖的实务风险**，其中"离线部署"和"导出数据治理"两条对这家医院的落地影响不低于已列的 6 条风险。逐条如下。

  ---

  ## 二、需求覆盖度与忠实度（对方案第 1、3 节）

  | 需求 | 我的判定 | 理由 |
  |---|---|---|
  | R1 开源+直连 Oracle/MySQL+AI 参与+功能丰富 | **覆盖，有一处保留** | 论断 1/2 成立（见第三节）。"功能丰富"维度我与初审 B1 一致：Superset 弱于中国式复杂报表/套打/上报表（财务、病案、卫统上报常见形态），方案正文及参考清单第 7 节均未列此缺口——这是**起草遗漏**，初审已补记，我附议并升级为正式风险（见第五节第 6 条）。 |
  | R2 无收费墙 + 导出 Excel | 覆盖 | Apache 2.0 无企业版属实；但论断 5 的"原生一键导出"需加前置条件，见第三节论断 5。 |
  | R3 外部 AI 经 API 建报表 + 人工 GUI | 覆盖，且比我预期更稳 | 论断 3 成立；且 2026 年 Superset 主仓库已合入**官方 MCP 服务**（见论断 4），"AI 当报表开发员"从"社区野路子"升级为官方支持路径，方案风险 2 的措辞可以调低。 |
  | R4 百万行查询与导出 | 覆盖 | 论断 6 默认值核实无误（ROW_LIMIT=50,000 等四档配置，[Dosu 对 config.py 的梳理](https://app.dosu.dev/a28d3c7e-a9d3-459e-9fb6-3a6f9ff4f357/documents/81918a10-0419-4856-9c87-88b7a2b29e29)）。"看聚合、导明细"双轨合理。 |
  | R5 角色 + 科室/人员行级隔离 | 覆盖 | 论断 8/9/10 成立。注意 RLS 的 Jinja 动态变量需显式开 `ENABLE_TEMPLATE_PROCESSING`，方案未写，见第五节第 4 条。 |
  | R6 嵌入其他系统 | 覆盖 | 论断 11/12 成立；宿主侧要写换 Guest Token 的小接口，初审已如实标注开发量非零，无夸大。 |
  | **R7 "AI 本地修改"** | **判定：误读，属加戏** | 用户原话"我还希望你能够在我本地进行修改等"出现在本轮复核指令里，结合上下文（`请你汇总下我提问的要求，我让别的ai复核`的多方互查流程），它是对**复核 AI 的工作方式要求**（允许直接改本地文件，而非只出报告），不是对 BI 产品的需求。方案第 1 节把它编码为 R7 产品需求、第 3 节又以"ZCode CLI 本身即本地执行通道"宣布"已满足"，这是自问自答——本轮我的约束恰恰是"只读、禁止修改任何文件"，反证该句是会话级指令而非稳定需求。**建议：从需求清单中删除 R7，或在清单中标注其性质为"本轮工作方式要求"，避免后续选型打分被一个伪需求污染。** |

  **遗漏检查**：用户历轮原话中除 R1~R6 外无其他被漏掉的功能性要求；"功能要尽快（尽量）丰富些"被如实转写。无其他偏离。

  ---

  ## 三、14 条论断独立核实（对参考清单第 4 节/方案第 3 节）

  | # | 判定 | 核实结果与修正 |
  |---|---|---|
  | 1 | ✅ | Apache 2.0、ASF 顶级项目、无企业版，属实（Preset 是独立公司的托管 SaaS，不影响协议结论）。 |
  | 2 | ✅ | python-oracledb + SQLAlchemy 连接串直连 Oracle，官方驱动文档支持；thin 模式免装 Oracle Client，对内网部署友好。 |
  | 3 | ✅ | 全套 REST API（OpenAPI）+ assets YAML/ZIP 导入导出 + JWT 登录，属实。这是 R3 的基石，也是 Superset 相对 Metabase/Redash 的决定性优势。 |
  | 4 | ✅（且可升级表述） | 不仅"社区 MCP Server 存在"（aptro/superset-mcp、bintocher/mcp-superset 等），**Superset 官方仓库 master 已内置 MCP 服务**（[apache/superset/superset/mcp_service](https://github.com/apache/superset/blob/master/superset/mcp_service/README.md)），Preset 亦发布跨 CLI 的 [agent-skills](https://github.com/preset-io/agent-skills)。论断从"把握中"升为"把握高"，方案风险 2 应相应调低。 |
  | 5 | **⚠️ 部分成立，需修正** | 仪表板级"Export Data to Excel"是**2026 年 7 月才落地的新功能**（[Preset 7 月 recap，#41133](https://preset.io/blog/apache-superset-repo-recap-july-2026/)），且：① **默认关闭**，未配置存储时端点返回 501；② 初版强制要求 **Celery worker + S3 对象存储**（`EXCEL_EXPORT_S3_BUCKET`），产物以**邮件预签名链接**下发（[UPDATING.md](https://gitee.com/mirrors/Superset/blob/master/UPDATING.md?skip_mobile=true)）；③ 最新版才改为无存储时同步直出（[apache.googlesource.com UPDATING](https://apache.googlesource.com/superset/+/HEAD/UPDATING.md)）。图表级 CSV/XLSX 导出无此问题。**风险**：方案按"原生一键"描述会让实施者踩空——院内无对象存储、依赖版本较旧时该按钮直接不可用；实施步骤第 1 步必须写明版本底线与 `EXPORT_STORAGE` 配置。 |
  | 6 | ✅ | 默认值 ROW_LIMIT=5 万、SQL_MAX_ROW=10 万等四档可调，与官方 config 一致。 |
  | 7 | ⚠️ 方向对、措辞过满 | "百万行导出必须走异步"作为工程建议成立，但需注意：图表 CSV/XLSX 下载走同步 HTTP（`/api/v1/chart/data`），异步主要覆盖 SQL Lab（GLOBAL_ASYNC_QUERIES）和新的仪表板 Excel 导出；xlsx 单 sheet 1,048,576 行硬上限属实。**风险**：低，实测确认即可。 |
  | 8 | ✅ | RLS 开源内置、数据集+角色绑定 SQL 子句、`{{ current_username() }}` 等 Jinja 变量属实。**补充**：Jinja 模板需开 `ENABLE_TEMPLATE_PROCESSING`（方案未写）。 |
  | 9 | ✅ | RBAC 内置角色+自定义，属实。 |
  | 10 | ✅ | FAB 体系 LDAP/OAuth2 + AUTH_ROLES_MAPPING/SYNC_AT_LOGIN，属实。 |
  | 11 | ✅ | EMBEDDED_SUPERSET + Guest Token 携带 rls_rules，官方文档支持，属实。 |
  | 12 | ✅（附议初审 B6） | @preset-sdk/embedded 确为 Preset 公司包而非 ASF 官方制品，供应链轻微顾虑如实标注即可；官方 @superset-ui/embedded-sdk 仍在维护。 |
  | 13 | ✅ | Alerts & Reports 开源免费，需 celery beat/worker + headless chromium + SMTP，属实。**对内网环境的连带问题见第五节第 1 条**。 |
  | 14 | ⚠️ 基本成立 | 有 zh_CN 语言包，但社区翻译覆盖率不完整，部分界面仍是英文/机翻质量。方案措辞"有简体中文语言包"不错但宜加"覆盖不全"的注脚，否则科室用户预期会错位。 |

  **新增论断（方案缺失，必须补）**：截至 2026 年，Superset 稳定线已到 **6.1.x**（2026-05 发布 6.1.0，[hakky 2026 对比文](https://book.st-hakky.com/en/data-analysis/metabase-redash-superset-comparison-2026)）；**CVE-2026-23980**（认证用户 SQL 注入，[advisory](https://advisories.gitlab.com/pkg/pypi/apache-superset/CVE-2026-23980/)）与 **CVE-2026-23982**（低权限用户改写数据集 SQL 绕过访问控制，[advisory](https://advisories.gitlab.com/pypi/apache-superset/CVE-2026-23982/)）均影响 **6.0.0 之前版本**。方案全文无版本底线要求——**部署必须 ≥6.0.0（建议 ≥6.1.x），且要建立补丁节奏**。这应成为第 15 条论断。

  ---

  ## 四、排除清单挑战（对参考清单第 5 节/方案第 6 节开放问题 1）

  我把"GitHub 全域是否还有更合适的"当成主问题查了一遍，结论：**没有能整体替换 Superset 的遗漏者**，但排除表有 3 个值得一提的空白：

  1. **Redash——排除表最不该漏的名字**。它是最经典的"SQL+API 友好"开源 BI，直连 Oracle、有 REST API，乍看契合 R1/R3。但 **getredash/redash 官方仓库已标注 unmaintained 并归档**（[仓库页](https://github.com/getredash/redash)），社区仅靠 fork 续命；且无行级权限、嵌入能力弱。**应补入排除表**：理由=项目停维+R5 不满足。它的存在也反向印证 Superset 选型。
  2. **Knowage（意大利 Engineering Group，AGPL）**：全套开源 BI 套件，JDBC 直连 Oracle、REST API、行为模型（profile 驱动的数据过滤，近似 RLS）、嵌入与 Excel 导出都有。没被评估过。但它 Java 全家桶、部署运维比 Superset 更重、AGPL、中文生态近乎为零，对 1~2 人团队明显更差。**不推翻结论，但"被排除候选"里应有它一行**，否则"全域无遗漏"的论证不完整。
  3. **Seal Report（.NET，Apache 2.0）/JasperReports Server CE**：前者轻量、Oracle 直连、有执行 API，但报表设计器是 Windows 桌面程序、行级权限弱；后者 REST API 完整但 visualize.js 嵌入是商业版功能。均不满足 R5/R6 组合，一句话可带过。

  另外对排除表的既有条目抽查：Metabase（Oracle 驱动仅 Pro/Enterprise）、Grafana（Oracle 插件与 Reporting 均 Enterprise）、Wren AI（Oracle connector 未落地）、SuperSonic（官方数据源为 MySQL/PG/ClickHouse/Doris 等，**Oracle 不在列**，[多篇技术分析一致](https://www.cnblogs.com/tgzhu/p/17911526.html)，且它本质是 ChatBI 内置问答，与 R3 路线不符）——**排除理由全部核实成立，无误判**。

  ---

  ## 五、自发发现的问题（按严重度）

  1. **【高·方案完全未提】离线部署。** 背景写明"全院内网、无外网"，而方案第 4 节第 1 步是"官方 Docker compose"——docker pull 镜像、pip 装 oracledb、下载 chromium 截图依赖，全都需要外网。落地时必须离线搬运镜像/wheel/chromium 二进制并内网建制品缓存，这是这家医院部署的**第一只拦路虎**，难度不亚于风险 3 的组件数量。建议实施步骤第 0 步即"离线介质准备"，并把论断 13 的 chromium 依赖标注离线安装成本。
  2. **【高】导出数据的合规治理（回答方案开放问题 2）。** 轨道二把百万行患者明细写成共享目录 CSV，等于**绕过了 BI 的 RLS/审计体系**：谁导的、导了什么、文件何时删，全无留痕；与"患者数据不出院"和等保审计要求直接冲突。讽刺的是，用户在 DataEase 嫌贵的"水印/导出管控"正是管这件事的。建议：轨道二产物至少加命名规范+目录 ACL+留存期限+导出登记，或改为由 Superset 异步导出（留审计日志）承担，轨道二仅作兜底。
  3. **【高·新增】版本与安全基线缺失。** 见第三节末：必须 ≥6.0.0（两个 2026 年 CVE 均为"认证用户越权/注入"，医院多科室多账号场景正中靶心）；另有历史教训 CVE-2023-27524（默认 SECRET_KEY 可伪造会话）——生产部署必须强制换 SECRET_KEY、关调试。方案风险节完全无"安全补丁节奏"条目，1~2 人团队更需要写明"谁盯版本、多久升一次"。
  4. **【中】RLS 的 Jinja 依赖与攻击面。** 论断 8 的动态变量要开 `ENABLE_TEMPLATE_PROCESSING`；模板处理历史上有过沙箱逃逸类 CVE。R3 让 AI 程序化写数据集 SQL/模板，等于把"AI 生成内容"接进了这个攻击面。缓解：AI 服务账号最小权限、模板只由人工审过的规则承载、开启前读当期 UPDATING/安全公告。方案未提，应补。
  5. **【中】论断 5 的落地前提**（见第三节）：仪表板 Excel 导出默认关、需 Celery、历史版本强依赖 S3、邮件发链接——内网无对象存储+SMTP 未通时体验会断。实施步骤需写明版本与 `EXPORT_STORAGE` 配置验证。
  6. **【中】中国式复杂报表缺口**（附议初审 B1，升级为正式风险）：若科室要的是单元格级网格报表/套打/上报表，Superset 的 Table 图表不够用。处置选项：接受（只做看板）、轨道二脚本生成格式化 xlsx、或外挂 UReport2（Apache 2.0 中式报表引擎，但需 Java 开发集成，对 1~2 人团队偏重）。方案应写明取舍，别等推广期再发现。
  7. **【低】附议初审 B2/B3/B4/B7**：ODS 同步导致报表天然 T+1（写明预期）、元数据库必须换 PG/MySQL 而非默认 SQLite、大版本升级有破坏性变更史需锁版本策略、GLM 脚本持有的 Oracle 凭据存放位置需约定。这四条初审已发现，我核实后全部成立，方案正文应吸收（初审"不回改方案"的纪律导致它们只在初审文件里，下一轮应合并进风险节）。
  8. **【低】附议初审对 SuperSonic 的异议但更保守**：SuperSonic 语义层对"指标口径统一"确有价值，但 Oracle 缺席是硬伤（已核实），在 Vastbase 兼容性都未实测的情况下并行试点会摊薄 1~2 人团队。维持"试点观察"定位即可，不必升级为并行试点。
  9. **【附记】多方互查机制本身**：`检查_codex.md` 为空、`检查_codex.err` 显示 codex 因 "Not inside a trusted directory" 未运行——本轮"多方互查"实际只有两方出具意见，方案第 5 节验收标准"14 条论断经外部 AI 独立核查"中 codex 一票是缺席的。不影响我的结论，但送审状态应如实标注。

  ---

  ## 六、对方案第 6 节四个开放问题的直接回答

  1. **有无全占 R1~R7 的遗漏者？** 无。最近的是 Knowage（更重、AGPL）与已停维的 Redash（无 RLS）；SuperSonic/Wren AI 均卡在 Oracle。维持 Superset。R7 本身应从需求清单剔除（见第二节）。
  2. **双轨治理隐患？** 有，且是真问题：轨道二产物绕过权限与审计（第五节第 2 条），必须配文件治理规则或收敛回 BI 内导出。
  3. **14 条论断在最新版是否成立？** 13 条成立或基本成立，1 条（论断 5）需加前提修正；另须新增版本底线论断（≥6.0.0，建议 6.1.x）。
  4. **R7 与 R3 关系？** R7 非产品需求，无需 BI 侧能力；R3 已由 REST API+官方 MCP 服务充分覆盖，无需额外动作。

  **最终立场：选型结论通过；方案需在落地前补四处——离线部署预案、版本与安全基线、导出数据治理、中国式报表取舍——以上四处补上后，方案可进入实施授权阶段。**

  主要核查来源：[Preset 2026-07 recap（仪表板 Excel 导出）](https://preset.io/blog/apache-superset-repo-recap-july-2026/)、[Superset UPDATING.md](https://apache.googlesource.com/superset/+/HEAD/UPDATING.md)、[apache/superset 官方 MCP 服务](https://github.com/apache/superset/blob/master/superset/mcp_service/README.md)、[CVE-2026-23980](https://advisories.gitlab.com/pkg/pypi/apache-superset/CVE-2026-23980/)、[CVE-2026-23982](https://advisories.gitlab.com/pypi/apache-superset/CVE-2026-23982/)、[getredash/redash（停维）](https://github.com/getredash/redash)、[SuperSonic 数据源分析](https://www.cnblogs.com/tgzhu/p/17911526.html)、[2026 版 Superset/Metabase/Redash 对比（版本现状）](https://book.st-hakky.com/en/data-analysis/metabase-redash-superset-comparison-2026)。

