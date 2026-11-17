# 医院 Apache Superset 选型、部署与报表迁移工作区

山东某三甲耳鼻喉专科医院的数据资产平台统一接入项目：Apache Superset 6.1.0 选型复核、生产部署（10.10.8.73 双容器栈）、老 HIS 报表补迁、前端企业化改造与运维自动化（每日缓存预热、一键巡检）。

## 目录结构

| 路径 | 内容 |
|---|---|
| `目录索引.md` | 全工作区权威入口（先读这个） |
| `AGENTS.md` | 工作区约定与红线 |
| `superset-选型复核清单-v2-多方互查修订版.md` | 选型权威 |
| `superset-部署与安装长任务计划-v1-多方互查修订版.md` | 部署权威 |
| `superset-报表补迁与一致性验收及人员赋权长任务计划-v2-多方互查修订版.md` | 补迁总计划 |
| `migration/` | 执行活动：进度、批次证据（sources/）、冻结快照、迁移工具 |
| `review/` | 多方 AI 互查证据链（round-2 至 round-10+） |
| `offline-bundle/` | 生产离线介质：compose、配置、nginx、前端品牌脚本、运维脚本 |
| `dev/` | 本机开发栈（pgdata 不入库） |

## ⚠ 脱敏声明（重要）

本仓库**不含任何真实口令**。通过 git clean 过滤器（`.gitsanit/redact.sed` + `.gitattributes`）在提交时自动将真实口令替换为 `<REDACTED-*>` 占位符，覆盖：跳板机/服务器口令、Superset 管理员口令、员工初始密码、ODS/HIS 数据库口令。

- **本机工作区文件未被改动**：原始口令仅存在于本地工作区文件中（经授权的内部运维记录），仓库与 git 历史中只有占位符。
- ⚠ **不要在仓库内执行 `git checkout -- .`、`git reset --hard`、`git stash pop` 等会用仓库内容覆盖工作区的命令**——那会把本地文件替换为脱敏版本，原始口令记录将丢失。备份工作区后再做任何此类操作。
- 生产凭据的实际管理方式见 `superset-部署与安装长任务计划` 第 2 节（环境变量注入 + 服务器 .env，口令不进脚本）。

## 生产环境速览

- Superset 6.1.0 + PostgreSQL + Redis + Celery，Docker Compose 六容器，nginx 对外 8180
- 数据源：Oracle 11g（HIS 实库，经跳板机隧道只读）、ODS 数据中心、SQL Server、Vastbase
- 用户体系：HIS 员工表每日 06:00 自动同步（约 2400 人），科室角色 + 专项授权角色门禁
- 运维自动化：02:00 数据库备份（SHA256 校验）、06:00 用户同步、06:15 BI 驾驶舱缓存预热、`superset_health_check.sh` 一键巡检
