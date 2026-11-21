# 医院 Apache Superset 选型、部署、报表迁移与运维工作区

山东某三甲耳鼻喉专科医院数据资产平台统一接入项目：Apache Superset 6.1.0 选型复核、内网离线生产部署（`10.10.8.73:8180` 六容器栈）、老 HIS 报表补迁、企业化前端与千人千面 RBAC 权限治理、每日缓存预热与一键体检。

## 目录结构

| 路径 | 用途 |
|---|---|
| [AGENTS.md](AGENTS.md) | **跨 AI 唯一权威规范与红线**（`CLAUDE.md`、`GEMINI.md`、`.opencode/memory/project.md` 均指向本文件） |
| [目录索引.md](目录索引.md) | 全工作区 30 秒权威入口与文件导航 |
| [迁移完成情况与待办说明.md](迁移完成情况与待办说明.md) | 面向信息科的当前生产交付现状、11 角色矩阵与运维速查 |
| [docs/系统升级演进史.md](docs/系统升级演进史.md) | 全周期历史升级需求归纳（历史归档位于 `docs/archive/`） |
| `superset-*-多方互查修订版.md` | 选型（v2）、部署（v1.1）、补迁（v2）三份顶层权威总纲 |
| `migration/` | 执行日志（`执行进度.md`）、下阶段计划（`plans-20261120/`）、各批证据（`sources/`）、冻结快照、远程与验收工具 |
| `offline-bundle/` | 与生产 `10.10.8.73` SHA256 对齐的离线配置、定制前端 JS、nginx、运维与 RBAC 脚本（`PRODUCTION-MANIFEST-20261121.json`） |
| `review/` | 多方 AI 互查证据链（round-2 ~ round-14，**只读禁动**） |
| `dev/` / `tools/` | 本机开发栈（`pgdata/` 不入库不动）/ Windows Oracle Instant Client 19.25 |

## ⚠ 脱敏声明（极重要）

本仓库**不含任何真实口令**。通过 git clean 过滤器（`.gitsanit/redact.sed` + `.gitattributes`）在提交时自动将真实口令替换为 `<REDACTED-*>` 占位符，覆盖跳板机/服务器口令、Superset 管理员口令、员工初始密码与 ODS/HIS 数据库口令。

- **本机工作区文件未被改动**：授权的内部运维连接与口令仅存于本地 `superset-访问信息.md`，git 历史中只有占位符。
- ⚠ **严禁在仓库内执行 `git checkout -- .`、`git reset --hard`、`git stash pop`**——那会把本地文件覆写为脱敏占位符，导致原始口令记录丢失。
- 脚本、代码与 compose 严禁硬编码凭据，统一经环境变量或服务器 `.env` 注入。

## 生产环境速览（截至 2026-11-19）

- **服务栈**：Superset 6.1.0 + PostgreSQL + Redis + Celery + Nginx（六容器 `superset-prod`，对外 `:8180`，nginx 挂载 inode `47580611`）
- **报表与驾驶舱**：93 图表 / 78 数据集 / 53 看板（52 已发布），含 72–75 四大可视化 BI 驾驶舱、27 张主报表查询页、抗菌办 10 张查询页与病案专项明细
- **权限与用户**：2,383 名员工每日 06:00 与 HIS 同步；11 个 `报表授权_*` 角色矩阵 + 66 对 `datasource_access` 管辖全站，前端千人千面裁剪
- **运维自动化**：02:00 原子备份（SHA256）、06:00 用户同步、06:15 缓存预热（47 条全命中）、`superset_health_check.sh` 18 项一键体检
