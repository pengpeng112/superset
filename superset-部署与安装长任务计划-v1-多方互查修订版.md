# Superset 部署与安装长任务计划 v1（多方互查修订版）

> 2026-10-04。本文件是 `review/round-3/方案.md`（送审稿）经三方 AI 互查（GLM 起草+初审 / Codex 50 条 / Grok 全文审查；**Kimi 缺席：403 周额度耗尽**）→ 分歧表（2 条证据终审 + 38 条让步修正 + 3 条升级人工）后的修订落地版，是供**另一个 AI 执行**的权威部署计划。
> 证据链：`review/round-3/`（方案.md、审查_zcode.md、检查_codex.md、审查_grok、分歧表.md、核查证据、哈希记录、最终报告.md、人工终审决策记录.md）。
> 事实基线：`superset-选型复核清单-v2-多方互查修订版.md`（15 条论断、12 条风险）；round-3 对其论断 2 补注 SQLAlchemy 1.4 兼容条件（见 D7）。
>
> **v1.1 修订（2026-10-04 晚，人工终审 H1/H2/H3 落地）**：
> ① **H1 定案**：认证=**双通道**——本地密码（**默认 <REDACTED-DEFAULT-EMPLOYEE-PW>，用户可自行修改**）+ 医院单点登录平台；sys_employee 仅作**用户目录同步**（源=ODS `DATA_CENTER` 库镜像，字段映射见 D8，不直连 HIS）；原"方案 B 直连 HIS 认证"删除；停点 3 解除；
> ② **H2**：明细查询服务/门户集成两个后续系统**暂不启动**（2026-10-04 用户决定）；
> ③ **H3 完成**：10.10.8.73 经跳板机（10.10.8.53:40022）核查完毕——openEuler 22.03/16C30G/**Docker 24.0.9+Compose v5.5.0 已装**/无外网/宿主 nginx 已占 80/宿主 PostgreSQL 14 占 5432/firewalld 开启——数据目录改 **/home/superset**、对外端口改 **8180**、新增共享服务器资源隔离要求（见第 3 节核查表与 P3）。
>
> **2026-10-12 运行修复**：附录里 Celery `beat_schedule.schedule` 不能写字符串 `"* * * * *"`。Celery 5 会在 `maybe_schedule` 抛出 `AttributeError: 'str' object has no attribute 'app'`，beat 容器因此循环重启。应使用 `crontab(minute="*", hour="*")`。生产配置已按此改正，只重建了 `superset-beat`。

## 0. 用户原始需求（逐字引述，2026-10-04 /multi-review 参数 + 人工终审补充）

> 请各个ai结合我的要求做几个系统部署及安装长任务计划，我让别的ai执行，其中服务器地址为：10.10.8.73  用户名 root  密码 <REDACTED-JUMPBOX-SERVER-PW>      同时 [$sjzc](C:\Users\Administrator\.zcode\skills\sjzc\SKILL.md) 是可以链接到各个系统数据库，可以查询。 计划一定要详细，可以登录服务器进行核查，可以现在本地开发然后再部署到服务器同时能够连接到各个业务系统，其中系统的登录用户 我希望使用his系统的  sys_employee ，服务器连接信息授权你记录下来，如果需要要部署数据库可以使用   数据中心的 10.10.8.216:1521/orcl	ods/<REDACTED-ODS-PW>  进行记录单独创建表即可

人工终审补充（2026-10-04，逐字）：
> H1 登录语义：… 需要支持 单点登录平台和密码两种方式，其中 密码 默认为 <REDACTED-DEFAULT-EMPLOYEE-PW>,可以自行修改，sys_employee 只作为用户同步即可，而且可以使用ods库，也有这个表，不要用his的了。
> H2：… 暂时不用
> H3：… 10.10.8.73 需要使用如下ip地址访问，请你登录下在确定下 用途 跳板机(BI) 地址 10.10.8.53:40022 root/<REDACTED-JUMPBOX-SERVER-PW>

**需求要素分解**：

| # | 要素 | 落点 |
|---|---|---|
| U1 | 若干部署安装长任务计划，由另一 AI 执行 | P1~P5 五个计划 + 附录全文件 |
| U2 | 服务器 10.10.8.73（root，经跳板机访问） | 第 2 节凭据；P3 部署目标 |
| U3 | $sjzc 可连各系统库查询 | P4-S1（系统枚举）、ODS 表结构核实（已完成，见 D8） |
| U4 | 计划详细到可执行 | 步骤命令级 + 附录 A~F 全文件 |
| U5 | 可登录服务器核查 | 已完成（2026-10-04 经跳板机，第 3 节）；执行者到达时复核 |
| U6 | 先本地开发→部署→连各业务系统 | P1→P2→P3→P4，本地成果 export/import 迁移（P1-S7/P4-S6） |
| U7 | 登录用户用 sys_employee | **已定案（H1）**：目录同步（源=ODS 镜像）+ 双通道认证（密码默认 <REDACTED-DEFAULT-EMPLOYEE-PW> 可自改 / 单点登录平台 SSO） |
| U8 | 连接信息授权记录 | 第 2 节（含跳板机） |
| U9 | 部署库用数据中心 Oracle（ods/<REDACTED-ODS-PW>），单独建表 | D2/D8：仅自建对象（独立 schema SUPSET），不作元数据库 |

## 1. 目标与边界

**目标**：把 v2 定案的选型（Superset 6.1.x + 双轨架构）落成可由另一 AI 逐项执行的部署安装计划：本地开发 → 离线介质 → 服务器生产栈 → 业务数据源只读接入 → ODS 用户目录同步与科室行级权限 + 双通道认证。

**边界（本计划不交付，另行立项，完成后不得声称已交付对应需求）**：
- **轨道二"科室自助明细查询入口"**（v2 R4）：属应用开发；**用户 2026-10-04 决定暂不启动**（H2），本计划只打通其依赖基座。**R4 需求未由本计划交付。**
- **门户嵌入集成**（v2 R6）：仅就位配置开关与可选 SDK 介质；**暂不启动**（H2）。SSO 对接属本计划 P5（用户 H1 明确要求）。
- **中式复杂报表**（v2 风险 10）：试点期决策，不在本计划。
- 本计划不执行部署本身；起草阶段对数据库仅做平台元数据查询（免 live），服务器只读核查。

## 2. 授权与凭据记录（用户 2026-10-04 明示授权）

授权原话："服务器连接信息授权你记录下来……"及 H3 补充（跳板机信息）。

| 用途 | 地址/账号 | 凭据 | 授权范围 |
|---|---|---|---|
| **跳板机(BI)** | 10.10.8.53:40022 | root / <REDACTED-JUMPBOX-SERVER-PW> | 经 direct-tcpip 转发访问 10.10.8.73:22（10.10.8.73 从办公网直连不可达，**必须经此跳板**） |
| 部署目标服务器 | 10.10.8.73:22（经跳板） | root / <REDACTED-JUMPBOX-SERVER-PW> | 登录、只读核查、部署 Superset 生产栈 |
| 数据中心 Oracle（ODS） | 10.10.8.216:1521/orcl | ods / <REDACTED-ODS-PW> | ① 只读：`DATA_CENTER` 各 schema（含 HIS.SYS_EMPLOYEE 镜像）② **仅自建对象**：独立 schema `SUPSET` 内建 `SUP_` 前缀表（D8） |
| 各业务系统库 | 经 $sjzc 技能受控只读 | 平台解析，不落盘 | 只读 SELECT（受控限量、大表门禁） |

**执行红线**：
1. 业务库仅 SELECT；**同步与查询一律用 ODS 镜像（DATA_CENTER），不直连生产 HIS 源库（10.10.10.15）**（H1 定案）；
2. 数据中心 Oracle：`SUPSET` schema 内可建/写/删自建对象，其余对象只读；
3. 服务器写操作仅限 `/home/superset/`（见 D11）、Docker 资源（独立 project/容器名前缀 `superset-`）、本计划列入的 systemd/cron/firewalld 端口项；**宿主既有服务（nginx/PostgreSQL 14/ai-hms-*/data-asset-api）一律不触碰**；
4. 凭据仅记录于本文档与服务器 `/home/superset/secrets/`（600）；**任何脚本/代码/compose 不硬编码凭据**（环境变量注入）；
5. 患者敏感信息（身份证/电话/姓名/患者明细）不进入任何文档、日志与导出样例（sjzc 硬红线）；员工个人敏感字段（MOBILE/EMAIL/IDENNO/CERTIFICATECODE）不同步（D8）。

## 3. 服务器环境核查结果（2026-10-04 经跳板机实测，只读）

证据：`review/round-3/核查_服务器_跳板.out`（脚本 `核查_服务器_跳板.py`，凭据环境变量传入）。

| 核查项 | 实测结果 | 对计划的影响 |
|---|---|---|
| 操作系统 | **openEuler 22.03 LTS-SP2**，x86_64，内核 5.10 | Docker 路线无碍（容器内 debian 基）；不再需要 OS 问询 |
| 资源 | **16 核 / 30GB 内存 / 15GB swap** | 充足；按共享服务器设资源限额（D11） |
| 磁盘 | / 69G（可用 32G）；**/home 898G（可用 723G）** | **数据目录定 /home/superset**（/data 挂在 / 分区，仅 32G） |
| Docker | **24.0.9 + Docker Compose v5.5.0 已装**，运行中 | **docker 离线包介质取消**；P2 介质简化 |
| 外网 | **无外网**（EGRESS_FAIL） | 离线介质路线必须（P2 不变） |
| 端口占用 | 宿主 nginx **:80**；宿主 PostgreSQL 14 **:5432**；uvicorn :8000（本地）；docker-proxy :8900；sshd :22 | **Superset 栈对外端口用 8180**；PG16 容器不映射宿主端口（容器网络内通信） |
| firewalld | **active**（SELinux Disabled） | P3 需放行 8180/tcp |
| 既有容器 | ai-hms-* 模型服务 7 个 + data-asset-api（数据资产平台）等 | **共享服务器**：容器名前缀隔离、资源限额、部署/回退不得影响既有容器（D11） |
| 宿主 PostgreSQL 14 | systemd 服务，监听 0.0.0.0:5432 | 疑似数据资产平台等在用——**禁止触碰**；Superset 元数据库用容器 PG16（隔离） |
| 到 ODS 连通 | 10.10.8.216:1521 可达 | P4 数据源路径就绪 |
| 时区 | Asia/Shanghai ✓ | 无需调整 |
| 既有 superset | 无（无容器/无目录） | 全新部署 |
| 跳板机 | 10.10.8.53:40022 可达，可达 73:22 与 216:1521 | 执行者 SSH 路径=经跳板（附录 F 脚本） |

## 4. 关键决策（D1~D11）

**D1 部署形态：自写生产版 Docker Compose（非官方测试 compose）**
依据 v2 风险 3。生产栈 6 常驻服务（postgres/redis/web/worker/beat/nginx）+1 one-shot（init）。**服务器 Docker 已装（实测），无需备选路线**；P2-S6（pip venv+systemd 备选）保留为极端回退参考，默认不走。

**D2 元数据库：服务器本地 PostgreSQL 16 容器**
Superset 元数据库官方支持仅 PostgreSQL/MySQL；Oracle 不支持。与宿主 PG14 通过容器网络+不映射端口实现隔离。

**D3 认证与用户体系（H1 定案，2026-10-04）**
- **通道一（本地密码）**：Flask-AppBuilder AUTH_DB；同步建用户时初始密码 **<REDACTED-DEFAULT-EMPLOYEE-PW>**；用户可在个人设置（/userinfo）**自行修改密码**。
- **通道二（单点登录平台）**：对接医院单点登录平台（**协议与对接参数待信息科提供**——CAS / OAuth2 / OIDC / SAML / 自定义 token API 均可能；线索：ODS 已有 `PORTAL_USER` schema（PORTAL_USERS/PORTAL_ROLE_USER_BIND 等），提示院内存在门户统一用户体系）。实现路径二选一（执行者按 6.1.0 所带 FAB 版本文档验证后选定）：a) FAB 多认证配置（若支持 AUTH_MULTI）；b) 自定义 SecurityManager 双视图（/login/db 与 /login/sso 并存，社区通用做法）。
- **关键安全设置**：`AUTH_USER_REGISTRATION = False`——SSO 仅认证不注册，**只有经 ODS 同步过的工号能登录**（用户目录以 ODS 为准）。
- **风险注记（记录在案，不阻塞）**：统一默认密码 <REDACTED-DEFAULT-EMPLOYEE-PW> 可推测且 Superset 无强制首登改密；缓解=上线通知全院改密+信息科定期弱口令审计；如需强制首登改密，后续可加自定义视图跳转（可选项）。
- ~~方案 B（直连 HIS 认证 sys_employee 哈希）~~：**H1 定案后取消**。

**D4 离线介质：外网机器构建自建镜像 + docker save**
介质清单：自建 superset 镜像、postgres:16、redis:7、nginx:1.27-alpine、部署件（compose/config/脚本/校验和）。~~docker-ce 离线包~~（服务器已装，取消）。Playwright Chromium 随镜像分发。

**D5 版本锁定表（执行时填写实际 pin 值，全链一致）**

| 组件 | 锁定策略 |
|---|---|
| apache/superset 基镜像 | 6.1.x 当期最新补丁 tag（起草时 6.1.0），pin 精确 tag |
| playwright | `>=1.37,<2` 区间内锁一版 |
| oracledb / pymssql / PyMySQL / psycopg2-binary | 各锁精确版本 |
| postgres/redis/nginx | 精确 tag + digest 记录 |
| 自建镜像 | `hospital-superset:6.1.0-p1`（p 序号随重建递增） |

**D6 导出能力口径**
- 正式版 6.1.0：图表级 CSV/XLSX 导出可用，受行上限约束；CSV 大结果同步流式；
- 不存在"超 10 万行自动异步导出到服务器目录"的产品路径（Next 参数不混入）；
- 百万行明细=轨道二（H2：暂不启动）。

**D7 SQLAlchemy 1.4 兼容（证据终审）**
Superset 6.1.0 依赖 `sqlalchemy>=1.4,<2`。oracledb 在 SA 1.4 下必须 module mapping + `oracle://` 连接串。落地：`superset_config.py` 顶部三行映射（附录 B 已含）。

**D8 用户目录同步数据源与字段映射（H1 定案 + sjzc 元数据实测 2026-10-04）**
同步源：**ODS `DATA_CENTER`（ods_8_216 = 10.10.8.216:1521/orcl）`HIS.SYS_EMPLOYEE`**（用户确认存在；sjzc 实测 37 字段）+ `HIS.DEPT_DICT`（科室字典，46 字段）。

| ODS 字段 | 类型 | 用途 |
|---|---|---|
| EMPCODE | NVARCHAR2(100) 非空 | **username（工号）** |
| EMPLNAME | NVARCHAR2(100) | first_name（姓名，仅系统内展示） |
| DEPTCODE | NVARCHAR2(100) | 科室角色键 `role_<DEPTCODE>`（科室名经 DEPT_DICT 映射，仅用于命名） |
| VALIDSTATE | NVARCHAR2(2) 非空 | 在职判定 |
| ISDELETED | NUMBER 非空 | 删除/离职判定 |
| MOBILE / EMAIL / IDENNO / CERTIFICATECODE | — | **敏感字段，不同步** |

**值域防猜测（sjzc 红线）**：VALIDSTATE/ISDELETED 的具体值域（如"1=有效"）**不凭字段名猜**——执行者经平台 `GET /api/v1/ai/system-context` 或字典表核实后写入同步脚本的 WHERE 条件；核实结论记入执行进度.md。
同步映射表 `SUPSET.SUP_USER_DEPT`（工号/科室码/状态/同步时间，不含姓名与敏感字段）。

**D9 sjzc 能力边界**
systems 输出系统/表数/字段数——不输出连接串；凭据走信息科申请；live 受授权/审批/时间窗约束；大表门禁（LAB_RESULT 需 TEST_NO 限定等）。表结构（tables/columns）查平台元数据免 live 授权（D8 即此通道）。

**D10 本地开发主路线：Docker 容器（Windows 原生 venv 降为备选）**
本地复用生产镜像形态，保证"本地验证过的=生产在跑的"。

**D11 共享服务器隔离（本轮核查新增）**
10.10.8.73 与 ai-hms-*/data-asset-api 共存：① compose project=`superset-prod`、容器名前缀 `superset-`；② 资源限额（mem_limit：web 6g/worker 6g（Chromium 截图）/pg 4g/redis 1g/nginx 256m，合计 ≤24g，留余量给既有服务）；③ 独立 bridge 网络不动既有网段；④ 部署/回退命令逐条确认作用对象（`docker compose -p superset-prod ...`），**严禁裸 `docker rm/prune` 类全局操作**。

## 5. 计划总览

```
P1 本地开发（Docker 主路线）      AI 工时 0.5~1 天
P2 离线介质制备与传输             AI 工时 1~2 天（docker 离线包已取消）
P3 服务器部署 10.10.8.73          AI 工时 1 天（H3 已核查完毕，执行者复核增量即可）
P4 数据源接入                    AI 工时 1~2 天 + 人工等待：只读凭据书面确认（停点 2）
P5 用户/权限/双通道认证           AI 工时 2~3 天 + 人工等待：SSO 协议与对接参数（信息科）
   （P5-S1 可与 P4 并行；P5-S2 RLS 依赖 P4-S3 数据集就绪）
```

**断点续作**：执行者维护 `review/round-3/执行进度.md`（时间/计划/步骤/结果/证据文件）。**幂等性按步骤注记**：凡标注"存在性检查"的步骤，重跑前先查已存在则跳过（建库/密钥/create-admin/建表均非幂等）。
**通用失败处理**：单命令 10 分钟无响应→中止诊断→保留现场→按该步回退处理，不暴力重试不跳步。
**SSH 访问路径**：10.10.8.73 一律经跳板机 10.10.8.53:40022（附录 F 脚本；paramiko direct-tcpip 或 `ssh -J root@10.10.8.53 -p 40022 root@10.10.8.73`）。

## 6. P1 本地开发环境（Windows 本机，Docker 主路线）

**目标**：本地建立与生产同形态的开发栈，连真实 Oracle（ODS）完成连通与导出冒烟，产出可迁移成果与验证过的配置。

**前置**：Docker Desktop 运行中；磁盘 ≥15GB。

### P1-S1 工具核验（PowerShell）
```powershell
python --version        # 3.10+，仅跑辅助脚本
docker --version
docker compose version
```

### P1-S2 本地开发栈目录与配置
```
F:\python\superset\dev\
  docker-compose.dev.yml   # 附录 A 去掉 worker/beat/nginx，web 用 dev server
  superset_config.py       # 附录 B 模板，本地值：TALISMAN_ENABLED=False、EMBEDDED_SUPERSET=False
  superset_home\           # 挂载为 /app/superset_home
```
dev compose：`command: ["superset","run","--host","0.0.0.0","--port","8088","--with-threads","--debug"]`；postgres/redis/web 三服务；8088:8088 映射本机。**SQLite 仅允许临时冒烟，不得用于任何后续步骤**（v2 风险 3）。

### P1-S3 初始化（create-admin 仅首次）
```powershell
$env:FLASK_APP="superset"
cd F:\python\superset\dev
docker compose -f docker-compose.dev.yml up -d postgres redis
docker compose -f docker-compose.dev.yml run --rm superset-init
docker compose -f docker-compose.dev.yml up -d
```
检查点：http://127.0.0.1:8088 可登录 admin；重跑时 create-admin 报"已存在"属预期。

### P1-S4 连接真实 Oracle（ODS 只读冒烟；D7 映射已在附录 B）
1. URI：`oracle://ods:***@10.10.8.216:1521/?service_name=orcl`（服务名/SID 以实测为准）；
2. Advanced：不勾任何 DML/DDL、Expose in SQL Lab=是；
3. SQL Lab：`SELECT 1 AS ok FROM DUAL`。
检查点：ok=1。**ods 账号仅做连通验证**（本步与冒烟查询 `SELECT 1` 级别），不做业务数据检索。

### P1-S5 冒烟数据集与导出
用信息科提供的数据源只读账号（未到位则挂起，不阻塞其余验收）：建 1 个小表数据集 → 1 张表格图 → 导出 CSV 与 XLSX 各一次。

### P1-S6 成果导出（供 P4-S6 生产导入）
Settings → Export 勾选数据集/图表/仪表盘 → YAML/ZIP 存 `F:\python\superset\dev\export\`。

**P1 验收**：dev 栈三容器健康可登录；ODS `SELECT 1 FROM DUAL` 成功；数据集/图表/导出各 1 次（账号未到位标注"待 P4"）；export 包落盘。
**P1 回退**：`docker compose -f docker-compose.dev.yml down -v` + 删除 dev 目录。

## 7. P2 离线介质制备与传输（本地→服务器）

**目标**：制备全套离线介质（服务器无外网，实测 EGRESS_FAIL）。

**前置**：外网机器；磁盘 ≥20GB。

### P2-S0 外网验证
```powershell
curl.exe -I https://pypi.org/simple/          # 200/301 即通
docker pull hello-world; docker rmi hello-world
```
（服务器 OS 已知 openEuler 22.03 x86_64——本轮核查定案，无需再问询。）

### P2-S1 介质目录
`F:\python\superset\offline-bundle\`：`images\`、`compose\`、`config\`、`secrets\`(空)、`scripts\`、`docs\`。

### P2-S2 构建自建镜像（Dockerfile=附录 D；版本 pin 按 D5）
```powershell
docker build -t hospital-superset:6.1.0-p1 images\
docker run --rm hospital-superset:6.1.0-p1 /app/.venv/bin/python -c "import oracledb,pymssql,pymysql,psycopg2;print('drivers-ok')"
```
检查点：`drivers-ok`（应用解释器验证）。

### P2-S3 拉取配套镜像
```powershell
docker pull postgres:16; docker pull redis:7; docker pull nginx:1.27-alpine
docker image save -o images\superset-bundle.tar hospital-superset:6.1.0-p1 postgres:16 redis:7 nginx:1.27-alpine
```
（~~docker 离线包~~：服务器 Docker 24.0.9+Compose v5.5.0 已装，取消。）

### P2-S4 部署件（全文备齐随介质移交）
`compose\docker-compose.yml`（附录 A）、`config\superset_config.py`（附录 B 模板）、`scripts\superset_user_sync.py`（附录 C）、`scripts\pg_backup.sh`（附录 E）、`review/round-3/核查_服务器_跳板.py`（SSH 路径脚本）、`docs\CHECKLIST-P2.md`（清单+sha256，`Get-FileHash` 生成，格式差异注明）。

### P2-S5 传输（经跳板机）
网络路径已通（跳板机→73）。用 paramiko/plink 经跳板转发 scp，或 U 盘/内网中转。检查点：两端 sha256 一致。
（跳板传输示例：`scp -o ProxyJump=root@10.10.8.53:40022 superset-bundle.tar root@10.10.8.73:/home/`——凭据由 ssh agent/交互输入，不写脚本。）

**P2 验收**：bundle tar 本机 `docker load` 可导入；部署件 6 类齐备+sha256；传输后校验一致。
**P2 回退**：介质目录可整删重建，无服务器影响。

## 8. P3 服务器生产部署（10.10.8.73，经跳板机）

**目标**：Docker Compose 生产栈上线（6 常驻+init），与既有服务（ai-hms-*/data-asset-api）隔离共存。

### P3-S0 环境复核（核查已完成 2026-10-04，此处为执行时增量复核）
SSH 经跳板机（附录 F）。复核项（与第 3 节表对照）：`docker ps` 既有容器清单是否变化、`ss -tlnp` 端口占用是否新增、`df -h /home` 余量 ≥100G。任何与第 3 节不符的增量记录到执行进度.md 并评估端口/资源影响后再继续。

### P3-S1 目录与介质（幂等：先查后建）
```bash
ls /home/superset 2>/dev/null || mkdir -p /home/superset/{pgdata,redis,superset_home,backup,certs,media,logs,secrets,scripts}
chmod 700 /home/superset/secrets
docker load -i /home/superset-bundle.tar && docker images | grep -E 'hospital-superset|postgres|redis|nginx'
```

### P3-S2 密钥生成（幂等：已存在跳过）
```bash
test -s /home/superset/secrets/SECRET_KEY || openssl rand -base64 42 > /home/superset/secrets/SECRET_KEY
test -s /home/superset/secrets/GUEST_TOKEN_JWT_SECRET || openssl rand -base64 42 > /home/superset/secrets/GUEST_TOKEN_JWT_SECRET
test -s /home/superset/secrets/POSTGRES_PASSWORD || openssl rand -base64 24 > /home/superset/secrets/POSTGRES_PASSWORD
chmod 600 /home/superset/secrets/*
```

### P3-S3/S4 部署 compose 与配置
`/home/superset/docker-compose.yml`=附录 A；`superset_config.py`=附录 B（填真值）。`.env`（600）注入密钥。**compose 使用 `-p superset-prod` 与容器名前缀，严守 D11 隔离**。

### P3-S5 启动与健康检查（幂等：create-admin 已存在属预期）
```bash
cd /home/superset
docker compose -p superset-prod up -d postgres redis && docker compose -p superset-prod up superset-init
docker compose -p superset-prod up -d
docker compose -p superset-prod ps   # 六服务 Up（healthy），init Exited(0)
docker compose -p superset-prod exec superset-web curl -s http://127.0.0.1:8088/health   # OK
```

### P3-S6 防火墙与访问放行（firewalld active，实测）
```bash
firewall-cmd --add-port=8180/tcp --permanent && firewall-cmd --reload
firewall-cmd --list-ports
```
检查点：内网浏览器 http://10.10.8.73:8180 登录 admin 成功（80 端口已被宿主 nginx 占用，**不得动宿主 nginx**；如后续需 80 域名访问，经信息科评估在宿主 nginx 加反代 server 块——可选项，不在默认路径）。

### P3-S7 备份与恢复
- 每日 02:00 cron 执行附录 E 备份脚本（`docker exec` 方式），保留 14 天+异机拷贝；
- **恢复演练（验收必做）**：临时库 pg_restore 成功；
- secrets（含 SECRET_KEY，**丢失无法解密已存连接凭据**）随备份异地保存。

### P3-S8 自恢复验收
`systemctl enable docker` 已装则确认；全服务 `restart: unless-stopped`；`reboot` 后仅观察 `docker compose ps` 六服务自行恢复（无人工 up -d），且**既有 ai-hms-*/data-asset 容器同样恢复**。

**P3 验收**：六服务健康+/health OK；8180 可访问登录；备份恢复演练通过；重启自恢复（含既有容器不受影响）。
**P3 回退（分级）**：服务级=`docker compose -p superset-prod down`（保留数据）；版本级=换镜像 tag 重导；完全卸载=down+删四镜像+备份拷出后 `rm -rf /home/superset`+清 cron/firewalld 8180（破坏性操作须用户确认；**不得波及既有容器与宿主服务**）。

## 9. P4 业务数据源接入（约 20 系统）

**目标**：各业务系统数据以只读方式接入 Superset，形成数据集层；四库型实测。

**前置（人工停点 2，v2 风险 4）**：信息科书面确认 Superset 独立只读凭据（平台限流/审计口径），确认件存 `review/round-3/凭据确认.md`。未确认前仅接 ODS 测试。

### P4-S1 系统枚举与凭据申请
1. `/sjzc`（无参）→ systems 清单；产出 `review/round-3/数据源接入清单.md`：系统/库型/表数字段数/**供数路径**（ODS 镜像有→经 ODS（D8 已证 DATA_CENTER 含 HIS/HRP/LIS/JHEMR/PORTAL_USER 等 schema）；ODS 无→标"申请源库只读"）/优先级/凭据状态；
2. 生成《只读凭据申请单》交信息科；连接串以信息科回执为准。

### P4-S2 逐库接入（URI 模板）
| 库型 | URI 模板 | 注记 |
|---|---|---|
| Oracle（ODS） | `oracle://ro:***@10.10.8.216:1521/?service_name=orcl` | D7 映射已生效 |
| SQL Server | `mssql+pymssql://ro:***@host:1433/db` | 新版默认 |
| SQL Server 2008 R2（ECG） | 同上+`?tds_version=7.0` | sjzc 证实需 TDS 7.0 |
| MySQL | `mysql+pymysql://ro:***@host:3306/db` | 免编译驱动 |
| Vastbase（openGauss） | psycopg2+postgres 兼容模式 / opengauss 方言 | 以 S4 实测定 |
统一规范：全部只读勾选；Expose in SQL Lab=是；statement timeout+`pool_size=3,max_overflow=5`（全库总连接 ≤160）；数据库层只读授权为主。

### P4-S3 首批数据集（10 个）
仅基于 ODS；敏感列只读视图/剔除；命名 `ODS_<系统>_<主题>`；校验 SQL 走受控窗口/组合键聚合，**禁全表 COUNT(*)**（大表门禁）。

### P4-S4 Vastbase 全链路五项实测（v2 风险 1）
连接→元数据→日期函数→分页中文→万行导出。失败则记录替代方案（数据平台落地 ODS 后由 Oracle 供数）。

### P4-S5 AI 服务账号（最小权限）
`ai_reporter`：自定义角色（指定数据集 can_read+导入权限），非 Alpha；验证越权被拒；AI 建报表优先 YAML/ZIP 导入；模板人工审核（v2 风险 12）。

### P4-S6 本地成果导入生产
P1-S6 export 包经 admin 导入，核对数量一致；连接指向生产后逐一 Test Connection。

**P4 验收**：清单齐备+已获凭据库 Test Connection 通过（未获批标"待凭据"不计失败）；10 数据集可查且量级核对（受控方式）；Vastbase 五项结论；ai_reporter 演练+越权被拒。
**P4 回退**：单库删连接即断；数据集可删。

## 10. P5 用户目录同步、权限与双通道认证（H1 定案版）

**目标**：Superset 用户=ODS `HIS.SYS_EMPLOYEE` 在职员工（目录同步），科室角色+RLS 行级隔离（v2 R5），**双通道登录**（本地密码默认 <REDACTED-DEFAULT-EMPLOYEE-PW> 可自改 + 单点登录平台）。

### P5-S1 用户同步（数据源已定案，见 D8；附录 C 脚本）
- 源：ODS `HIS.SYS_EMPLOYEE` + `HIS.DEPT_DICT`（字段映射=D8 表；VALIDSTATE/ISDELETED 值域先核实再写 WHERE，防猜测）；
- 运行载体：`docker compose -p superset-prod exec -T superset-worker /app/.venv/bin/python /app/superset_home/scripts/superset_user_sync.py`（镜像含 oracledb，宿主零依赖），宿主 cron 每日 06:00；
- 建用户：username=EMPLCODE，first_name=EMPLNAME，**初始密码 <REDACTED-DEFAULT-EMPLOYEE-PW>**（用户可在 /userinfo 自行修改）；敏感字段（MOBILE/EMAIL/IDENNO/CERTIFICATECODE）不同步；
- 离职/删除（VALIDSTATE 无效或 ISDELETED≠0，按核实值域）：置 active=false；
- 映射表 `SUPSET.SUP_USER_DEPT`（工号/科室码/状态/时间）；
- 执行契约：幂等键=username；分页；CSRF+JWT；部分失败不中断；重试 3 次退避；flock 互斥；统计输出+退出码；日志无姓名。

### P5-S2 角色与 RLS（角色常量法；依赖 P4-S3 数据集就绪）
- 角色：员工=Gamma（基础浏览）+ `role_<DEPTCODE>`（同步脚本 ensure，授指定数据集 can_read；不克隆 Admin；v2 论断 9）；
- 仪表板按科室授权：`DASHBOARD_RBAC` feature flag（附录 B）；
- RLS：每科室角色一条 regular 规则，**固定常量**表达式（如 `DEPT_CODE = 'ENT01'`，由同步脚本按 DEPT_DICT 写入）；受控数据集加 base 规则 `1 = 0` **默认拒绝**（白名单命中才可见）；多科室=多角色 OR 组合；
- SQL Lab 权限仅信息科角色（RLS_IN_SQLLAB 默认关）。

### P5-S3 单点登录平台集成（H1 通道二）
**信息依赖（向信息科获取，列《SSO 对接信息单》)**：平台名称/协议（CAS、OAuth2、OIDC、SAML 或自定义 token API）/端点（授权、token、用户信息、登出）/Superset 回调注册方式/账号字段（是否=工号 EMPLCODE）/测试账号。
实现（二选一，按 FAB 版本文档验证）：
- 路径 a：FAB 多认证（AUTH_MULTI，若 6.1.0 所带 FAB 支持）：DB 与 SSO provider 并存；
- 路径 b：自定义 `CustomSecurityManager(SupersetSecurityManager)`：保留 `auth_user_db` + 增加 `/login/sso` 视图（OAuth2/OIDC 走 authlib，CAS 走对应库，自定义 token 走接口校验）。
**关键配置**：`AUTH_USER_REGISTRATION=False`（SSO 只认证不注册——仅 ODS 同步过的工号可登录）；SSO 账号与 username 匹配失败=拒绝并记日志。
验收：同一工号两种方式各登录成功一次；未同步账号 SSO 登录被拒。

### P5-S4 定时邮件报告（v2 风险 11）
SMTP 信息科提供后填附录 B 并重启 beat 与 worker；`ALERT_REPORTS_EXECUTE_AS` 保持 creator 视角；敏感报表由科室权限账号创建并核对 owner；或只发链接。

### P5-S5 越权四面+异常态验收
| 面 | 用例 | 期望 |
|---|---|---|
| 直登 | 科室 A 账号（<REDACTED-DEFAULT-EMPLOYEE-PW> 首登）登录跨科室看板 | 仅本科室行 |
| 密码自改 | A 修改密码后新旧密码各试一次 | 新密码可登录、旧密码拒绝 |
| SSO | A 经单点登录平台跳转登录；未同步账号试 SSO | 成功登录；未同步被拒 |
| API | A 的 JWT 调 chart/data 拉他科数据集 | 403/空 |
| 导出 | A 按条件导出 CSV | 仅本科室行 |
| 异常态 | 无科室用户/双科室用户/同步中断期离职账号 | 默认拒绝/并集/次日停用+紧急手工 inactive（JWT 失效窗口记录） |

（嵌入态 Guest Token 用例留待门户集成立项时补——H2 暂不启动。）

**P5 验收**：同步一轮成功（≥1 科室真实账号、角色/RLS 就位、统计落档）；S5 表全过；`SUPSET` schema 仅 `SUP_` 对象；SSO 双通道验收通过。
**P5 回退（安全序）**：停 cron→停用同步用户（先断访问）→删自定义角色与 RLS→DROP `SUPSET` schema 自建对象；SSO 集成独立回退（还原 config 的 AUTH 段+重启 web）。

## 11. 验收总表

| 计划 | 核心验收 | 证据物 |
|---|---|---|
| P1 | dev 栈登录+ODS SELECT+图表导出+export 包 | 执行进度.md、截图/输出 |
| P2 | 介质可加载+清单 sha256 | CHECKLIST-P2.md |
| P3 | 六服务健康+/health+8180 可访问+恢复演练+重启自恢复（含既有容器不受影响） | compose ps、dump、演练记录 |
| P4 | 清单+连接测试+Vastbase 五项+AI 账号演练+成果导入核对 | 接入清单、实测记录 |
| P5 | 同步跑通+双通道登录+四面+异常态越权测试 | 同步统计、越权记录 |
| **总体** | U1~U9 逐条对账；**R4 轨道二与 R6 嵌入未交付（H2 暂不启动）**；v2 R1~R6 产品验收另行按 v2 §8 | 执行进度.md 汇总 |

## 12. 风险与回退映射

| 风险 | 来源 | 处置落点 |
|---|---|---|
| 服务器无外网 | 本轮实测 | P2 全介质（docker 离线包已因 Docker 在装取消） |
| **共享服务器资源/端口冲突** | 本轮实测（80/5432/8900 已占，ai-hms/data-asset 共存） | 8180 端口+容器网络隔离+mem_limit+`-p superset-prod`（D11）；严禁全局 docker 操作 |
| **统一默认密码 <REDACTED-DEFAULT-EMPLOYEE-PW>** | H1 用户决策 | 记录在案：上线通知改密+定期弱口令审计+可选首登改密增强（D3 注记） |
| SA1.4/Oracle 方言 | 证据终审 | D7 映射三行+`oracle://` |
| 元数据库误用 | 送审稿 | D2 固化 PG16 容器（与宿主 PG14 隔离） |
| 组件多运维重 | v2 风险 3 | compose 固化+备份恢复演练+D5 锁定 |
| 只读凭据合规 | v2 风险 4 | P4 停点 2 书面确认 |
| Vastbase 兼容 | v2 风险 1 | P4-S4 五项实测 |
| 版本/CVE | v2 论断 15 | D5 基线（≥6.1.x、三密钥） |
| 大表拖垮源库 | 审查 | 池上限+timeout+科室角色禁 SQL Lab+门禁校验 SQL |
| 定时邮件隔离 | v2 风险 11 | P5-S4 |
| Jinja 攻击面 | v2 风险 12 | AI 账号白名单+模板审核 |
| 员工敏感信息落档 | 审查 | D8 敏感字段不同步；S0 只记结构 |
| 凭据泄露面 | 审查 | 文档唯一记录点+secrets 600+脚本环境变量+AGENTS 例外 |
| 中式报表缺口 | v2 风险 10 | 试点期决策（第 14 节） |
| VALIDSTATE 值域猜测 | sjzc 红线 | P5-S1 先核实再写条件 |

## 13. 执行者守则

1. **只读红线**：业务库仅 SELECT；不直连生产 HIS；ODS 仅 `SUPSET` schema 自建对象可写；服务器写操作限 `/home/superset/`、superset-prod Docker 资源、列入计划的 cron/firewalld 项；**宿主 nginx/PG14/既有容器零触碰**。
2. **人工停点**：P4 凭据书面确认；P5-S3 SSO 对接信息（信息科）；破坏性操作（完全卸载等）须用户确认。（H1/H3 已定案，不再是停点。）
3. **断点续作**：`review/round-3/执行进度.md` 逐行记录；按幂等注记先查后做。
4. **失败处理**：10 分钟超时→中止诊断→保留现场→按回退条目处理；不暴力重试、不跳步、不伪造结果。
5. **证据与凭据**：验收证据落 `review/round-3/`；凭据只入本文档第 2 节与服务器 secrets（600）；代码/compose/脚本零硬编码；患者敏感信息零落档。
6. **汇报**：每计划完成出简报；全部完成后按第 11 节对账。

## 14. 人工确认记录与后续立项清单

**已决策（2026-10-04）**：
- H1 登录语义：**已定**——目录同步（ODS 源）+双通道认证（密码默认 <REDACTED-DEFAULT-EMPLOYEE-PW> 可自改 / 单点登录平台）；
- H2 后续系统：**暂不启动**（明细查询服务、门户集成）；
- H3 服务器状态：**已核查**（经跳板机 10.10.8.53:40022，环境结论见第 3 节）。

**待信息科提供（不阻塞 P1~P3）**：
- SSO 平台协议与对接参数（P5-S3《SSO 对接信息单》）；
- 各业务系统只读凭据（P4-S1 申请单流程+停点 2 书面确认）；
- 内网 SMTP 服务器（P5-S4，未就绪则定时报告延后）。

**后续立项（用户已决定暂不启动，保留清单）**：
1. 轨道二"科室自助明细查询入口"（R4 验收载体）；
2. 门户嵌入集成（R6：OA 前后端改造+Guest Token 签发服务）；
3. 中式复杂报表三选一（v2 风险 10，试点期决策）。

---

## 附录 A：docker-compose.yml（生产，全文；v1.1 更新路径/端口/限额）

```yaml
name: superset-prod

x-superset-common: &superset-common
  image: hospital-superset:6.1.0-p1
  depends_on:
    postgres: { condition: service_healthy }
    redis: { condition: service_healthy }
  environment: &superset-env
    SUPERSET_CONFIG_PATH: /app/superset_config.py
    FLASK_APP: superset
    SUPERSET_SECRET_KEY: ${SUPERSET_SECRET_KEY}
    GUEST_TOKEN_JWT_SECRET: ${GUEST_TOKEN_JWT_SECRET}
  volumes:
    - /home/superset/superset_config.py:/app/superset_config.py:ro
    - /home/superset/superset_home:/app/superset_home
  restart: unless-stopped

services:
  postgres:
    image: postgres:16
    container_name: superset-postgres
    environment:
      POSTGRES_USER: superset
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: superset
    volumes:
      - /home/superset/pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U superset"]
      interval: 10s
      timeout: 5s
      retries: 5
    mem_limit: 4g
    restart: unless-stopped

  redis:
    image: redis:7
    container_name: superset-redis
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - /home/superset/redis:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    mem_limit: 1g
    restart: unless-stopped

  superset-init:
    <<: *superset-common
    container_name: superset-init
    command: >
      bash -c "superset db upgrade &&
               (superset fab create-admin --username admin --firstname Admin --lastname Hospital
                  --email admin@hospital.local --password ${ADMIN_INIT_PASSWORD} || echo '[init] admin exists') &&
               superset init"
    restart: "no"

  superset-web:
    <<: *superset-common
    container_name: superset-web
    command: >
      gunicorn -w 4 -k gthread --threads 8 -b 0.0.0.0:8088
      --timeout 120 --graceful-timeout 60
      --limit-request-line 0 --limit-request-field-size 0
      superset.app:app
    mem_limit: 6g
    restart: unless-stopped

  superset-worker:
    <<: *superset-common
    container_name: superset-worker
    command: celery --app=superset.tasks.celery_app:app worker -Ofair --concurrency=2
    shm_size: 512m          # Playwright Chromium 截图
    mem_limit: 6g
    restart: unless-stopped

  superset-beat:
    <<: *superset-common
    container_name: superset-beat
    command: celery --app=superset.tasks.celery_app:app beat
    mem_limit: 1g
    restart: unless-stopped

  nginx:
    image: nginx:1.27-alpine
    container_name: superset-nginx
    depends_on: [superset-web]
    ports:
      - "8180:80"           # 宿主 80 已被既有 nginx 占用（实测），避让 80/8000/8900/5432
    volumes:
      - /home/superset/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    mem_limit: 256m
    restart: unless-stopped
```

`nginx.conf`（/home/superset/nginx.conf）要点：`proxy_pass http://superset-web:8088;`、`proxy_read_timeout 300;`、`proxy_set_header Host $host / X-Real-IP / X-Forwarded-For / X-Forwarded-Proto;`、`client_max_body_size 100m;`。仅 8180 对外；PG/Redis 不映射宿主端口（与宿主 PG14 隔离）。

`.env`（/home/superset/.env，600）：`SUPERSET_SECRET_KEY=`、`GUEST_TOKEN_JWT_SECRET=`、`POSTGRES_PASSWORD=`、`ADMIN_INIT_PASSWORD=`。

## 附录 B：superset_config.py（生产，全文模板；v1.1 认证段新增）

```python
# Superset 6.1.x 生产配置模板（占位符 <> 执行时替换；以官方 config.py 为基线 diff）
# D7：SA1.4 下 oracledb 需 module mapping（oracle:// 连接串）
import sys
import oracledb
oracledb.version = "8.3.0"
sys.modules["cx_Oracle"] = oracledb

import os

# --- 基础 ---
SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]
DATA_DIR = "/app/superset_home"
SQLALCHEMY_DATABASE_URI = (
    "postgresql+psycopg2://superset:"
    + os.environ["POSTGRES_PASSWORD"]
    + "@postgres:5432/superset"
)

# --- 认证（H1 定案：通道一 DB 密码 + 通道二 SSO） ---
from flask_appbuilder.security.manager import AUTH_DB   # 执行时按 FAB 版本核对导入路径
AUTH_TYPE = AUTH_DB
AUTH_USER_REGISTRATION = False   # SSO 只认证不注册：仅 ODS 同步过的工号可登录
# 通道二 SSO（P5-S3 信息科提供协议后启用，二选一实现路径）：
#   路径 a（FAB 多认证）：AUTH_MULTI + provider 配置（以 FAB 版本文档为准验证）
#   路径 b（自定义视图）：CUSTOM_SECURITY_MANAGER = CustomSecurityManager
#                        （保留 auth_user_db + /login/sso；见 P5-S3）
# AUTH_ROLES_SYNC_AT_LOGIN = False   # 若走 LDAP/SSO 组同步，防止冲掉手工科室角色（v2 论断 10）

# --- 功能开关（全部入 FEATURE_FLAGS；开关名以当期官方 config.py 为准） ---
FEATURE_FLAGS = {
    "EMBEDDED_SUPERSET": True,             # R6 基座（嵌入集成暂不启动，H2）
    "EMBEDDED_SUPERSET_ONLY": False,
    "ALERT_REPORTS": True,                 # 定时报告（v2 论断 13）
    "ENABLE_TEMPLATE_PROCESSING": True,    # Jinja（v2 论断 8）
    "DASHBOARD_RBAC": True,                # 仪表板按角色授权（P5-S2）
    "PLAYWRIGHT_REPORTS_AND_THUMBNAILS": True,   # Playwright 截图
}

# --- 缓存/会话（Redis） ---
from datetime import timedelta
from celery.schedules import crontab
CACHE_CONFIG = {"CACHE_TYPE": "RedisCache", "CACHE_REDIS_URL": "redis://redis:6379/0", "CACHE_DEFAULT_TIMEOUT": 86400}
DATA_CACHE_CONFIG = {"CACHE_TYPE": "RedisCache", "CACHE_REDIS_URL": "redis://redis:6379/1"}
FILTER_STATE_CACHE_CONFIG = {"CACHE_TYPE": "RedisCache", "CACHE_REDIS_URL": "redis://redis:6379/2",
                             "CACHE_DEFAULT_TIMEOUT": timedelta(days=1).total_seconds()}
EXPLORE_FORM_DATA_CACHE_CONFIG = {"CACHE_TYPE": "RedisCache", "CACHE_REDIS_URL": "redis://redis:6379/2",
                                  "CACHE_DEFAULT_TIMEOUT": timedelta(days=1).total_seconds()}

# --- Celery（含 reports 调度） ---
CELERY_CONFIG = {
    "broker_url": "redis://redis:6379/3",
    "result_backend": "redis://redis:6379/4",
    "imports": ("superset.sql_lab", "superset.tasks.scheduler"),
    "beat_schedule": {
        "reports.scheduler": {
            "task": "reports.scheduler",
            "schedule": crontab(minute="*", hour="*"),
        }
    },
}

# --- 定时报告截图 ---
WEBDRIVER_BASEURL = "http://superset-web:8088/"
WEBDRIVER_BASEURL_USER_FRIENDLY = "http://10.10.8.73:8180/"

# --- 行数分层（v2 论断 6） ---
ROW_LIMIT = 50000
SQL_MAX_ROW = 100000
TABLE_VIZ_MAX_ROW_SERVER = 500000
DISPLAY_MAX_ROW = 10000
DEFAULT_SQLLAB_LIMIT = 1000
SQLLAB_TIMEOUT = 120

# --- 反代（容器 nginx） ---
ENABLE_PROXY_FIX = True
PROXY_FIX_X_FOR = 1
PROXY_FIX_X_PROTO = 1
PROXY_FIX_X_HOST = 1

# --- 安全 ---
TALISMAN_ENABLED = True
# 以官方 config.py 的 TALISMAN_CONFIG 为基线，仅向 frame-ancestors 追加门户来源；
# 勿凭记忆重写（防白屏）；嵌入集成启动前无需追加。
SESSION_COOKIE_SECURE = False   # 试点期 HTTP；HTTPS 里程碑后改 True
WTF_CSRF_ENABLED = True         # 不覆写 WTF_CSRF_EXEMPT_LIST

# --- 嵌入（R6 基座） ---
GUEST_TOKEN_JWT_SECRET = os.environ["GUEST_TOKEN_JWT_SECRET"]
GUEST_TOKEN_JWT_ALGO = "HS256"

# --- 邮件（P5-S4 信息科提供后填；未就绪则 ALERT_REPORTS 交付延后） ---
# SMTP_HOST = "<内网邮件服务器>"
# SMTP_PORT = 25
# SMTP_STARTTLS = False
# SMTP_DEFAULT_FROM = "superset@hospital.local"

SUPERSET_LOG_LEVEL = "INFO"
```

## 附录 C：superset_user_sync.py（全文骨架+执行契约；v1.1 更新源与密码）

```python
# -*- coding: utf-8 -*-
"""ODS HIS.SYS_EMPLOYEE -> Superset 用户/角色 同步脚本（H1 定案版）。
数据源（D8，sjzc 元数据实测 2026-10-04）：
  ODS DATA_CENTER（10.10.8.216:1521/orcl）
  - HIS.SYS_EMPLOYEE：EMPLCODE(工号->username) EMPLNAME(姓名->first_name)
    DEPTCODE(->role_<码>) VALIDSTATE+ISDELETED(在职判定，值域先核实防猜测)
    敏感字段 MOBILE/EMAIL/IDENNO/CERTIFICATECODE 不同步
  - HIS.DEPT_DICT：DEPTCODE->科室名（仅角色命名用）
  注意：SA1.4 环境，本脚本若独立用 SQLAlchemy 连 Oracle，同样需要 D7 的
  module mapping（sys.modules["cx_Oracle"]=oracledb）+ oracle:// 连接串。
执行环境：superset-worker 容器内（镜像含 oracledb）：
  docker compose -p superset-prod exec -T superset-worker /app/.venv/bin/python \
      /app/superset_home/scripts/superset_user_sync.py [--dry-run]
执行契约：
  - 幂等键：username=EMPLCODE；重复执行安全（upsert）。
  - 新用户初始密码：<REDACTED-DEFAULT-EMPLOYEE-PW>（H1 用户定案；用户可在 /userinfo 自行修改）。
    upsert 时不覆盖用户已修改过的密码（仅创建时设初始密码）。
  - 互斥：flock('/tmp/user_sync.lock')。
  - 拉取：分页（rownum 窗口），单页 500；WHERE 条件按核实后的
    VALIDSTATE/ISDELETED 值域写（禁止猜值域，结论记执行进度.md）。
  - Superset API：POST /api/v1/security/login 取 JWT；写操作携带
    CSRF（GET /api/v1/csrf_token/）；失败重试 3 次（指数退避）。
  - 部分失败不中断整批；结束统计（新增/更新/停用/失败）；退出码 0/1。
  - 日志仅含工号与科室码（无姓名）。
  - 映射表 MERGE INTO SUPSET.SUP_USER_DEPT（D8 字段）。
TODO(执行者实现)：
  1) fetch_employees()   2) ensure_dept_role()   3) upsert_user()
  4) deactivate()        5) write_mapping()      6) ensure_rls_rule()
     （RLS=角色常量规则 DEPT_CODE='<码>' + 受控数据集 base 1=0，见 P5-S2）
"""
import argparse
```

（实现后经人工代码走查再纳入介质；走查要点：WHERE 值域依据、密码不覆盖、日志脱敏、退出码。）

## 附录 D：Dockerfile（全文）

```dockerfile
FROM apache/superset:6.1.0        # D5：实际取当期 6.1.x 最新补丁 tag

USER root
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright
ARG PLAYWRIGHT_VERSION=1.49.0     # >=1.37,<2 区间内锁版（D5）

RUN apt-get update && apt-get install -y --no-install-recommends \
        fonts-noto-cjk \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 应用解释器 /app/.venv（官方镜像 uv venv）；MySQL 用 PyMySQL 免编译
RUN /app/.venv/bin/pip install --no-cache-dir \
        oracledb==<pin> \
        pymssql==<pin> \
        PyMySQL==<pin> \
        psycopg2-binary==<pin> \
    && /app/.venv/bin/pip install --no-cache-dir playwright==${PLAYWRIGHT_VERSION} \
    && /app/.venv/bin/playwright install --with-deps chromium \
    && chmod -R a+rX /opt/ms-playwright

USER superset
```

验证：`docker run --rm hospital-superset:6.1.0-p1 /app/.venv/bin/python -c "import oracledb,pymssql,pymysql,psycopg2;print('drivers-ok')"`；`ls /opt/ms-playwright`。
（openEuler 宿主跑 debian 基镜像无兼容问题。）

## 附录 E：pg_backup.sh（全文）

```bash
#!/usr/bin/env bash
# Superset 元数据库每日备份；宿主 cron 02:00 执行；docker exec 方式（宿主无 PG 客户端依赖）
set -euo pipefail
BASE=/home/superset
BACKUP_DIR=$BASE/backup
KEEP_DAYS=14
STAMP=$(date +%F)
mkdir -p "$BACKUP_DIR"
docker compose -f $BASE/docker-compose.yml -p superset-prod exec -T postgres \
    pg_dump -U superset -Fc superset > "$BACKUP_DIR/superset-${STAMP}.dump"
cp -a $BASE/secrets "$BACKUP_DIR/secrets-${STAMP}"   # SECRET_KEY 随备份（丢失不可恢复凭据密文）
find "$BACKUP_DIR" -name 'superset-*.dump' -mtime +${KEEP_DAYS} -delete
find "$BACKUP_DIR" -type d -name 'secrets-*' -mtime +${KEEP_DAYS} -exec rm -rf {} +
# 恢复演练（验收时手动一次）：
#   docker exec -i superset-postgres createdb -U superset superset_restore
#   docker exec -i superset-postgres pg_restore -U superset --clean --if-exists -d superset_restore < dump
```

cron：`0 2 * * * /bin/bash /home/superset/scripts/pg_backup.sh >> /home/superset/logs/backup.log 2>&1`

## 附录 F：核查脚本与证据索引

- `review/round-3/核查_服务器_跳板.py` — **生产用 SSH 路径**（跳板机 10.10.8.53:40022 → direct-tcpip → 10.10.8.73:22；凭据环境变量 JB_*/TGT_*）；等价 `ssh -J root@10.10.8.53 -p 40022 root@10.10.8.73`；
- `review/round-3/核查_服务器_跳板.out` — 2026-10-04 服务器实况证据（第 3 节表来源）；
- `review/round-3/核查_服务器.py` / `核查_网络_本机.out` — 起草阶段直连尝试与网络证据（存档）；
- ODS 表结构证据（sjzc 元数据，2026-10-04）：`HIS.SYS_EMPLOYEE`（37 字段）、`HIS.DEPT_DICT`（46 字段）、`PORTAL_USER.PORTAL_USERS` 等——见 `review/round-3/人工终审决策记录.md` 附录。
