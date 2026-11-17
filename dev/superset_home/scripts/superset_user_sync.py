# -*- coding: utf-8 -*-
"""ODS HIS.SYS_EMPLOYEE -> Superset 用户/角色/RLS 同步脚本（P5-S1 定案实现）。

运行环境：superset-worker 容器内（镜像含 oracledb + requests）：
  docker compose -p superset-prod exec -T superset-worker \
      /app/.venv/bin/python /app/superset_home/scripts/superset_user_sync.py [--dry-run] [--pilot DEPT]
  只把已有科室角色改成中文名、不动用户：追加 --rename-roles

环境变量（必填，不硬编码）：
  SYNC_ORA_DSN   如 10.10.8.216:1521/orcl
  SYNC_ORA_USER / SYNC_ORA_PWD   ODS 账号
  SUP_BASE       如 http://superset-web:8088
  SUP_ADMIN / SUP_ADMIN_PWD      Superset 管理账号
可选：
  INIT_PASSWORD  新用户初始密码（默认 <REDACTED-DEFAULT-EMPLOYEE-PW>，H1 定案；用户可自行修改，upsert 不覆盖）
  RLS_TABLE_ID   >0 时为各科室角色在该数据集上 ensure RLS 常量规则（DEPT_CODE='<码>'）；
                 目标必须存在且未退役，否则明确报错退出（2026-10-14）；0=不建 RLS
  SYNC_MIN_ACTIVE           在职集合熔断下限（默认 100；pilot 模式不校验）
  SYNC_MAX_DEACTIVATE_ABS   单次停用数量绝对上限（默认 50，超出即熔断且不执行任何停用）
  SYNC_MAX_DEACTIVATE_RATIO 单次停用占在职数比例上限（默认 0.10）

值域依据（2026-10-04 经平台 live 聚合核实，防猜测）：
  在职 = VALIDSTATE='1' AND ISDELETED=0（实测 2382 人）
日志只含工号/科室码（无员工姓名）；幂等键=username；退出码 0=全部成功 1=存在失败。

科室角色展示名（2026-10-08）：`科室_<科室中文名>（<DEPT_CODE>）`，同一角色 id 原地改名。
ab_role.name 上限 64。日报表授权角色用 `报表授权_<中文名>`，不要用 `role_` / `科室_` 开头，
否则次日同步会把它当成科室角色换掉。

身份生命周期（2026-10-12 B2）：
- **人工冻结**：管理员把角色 `人工冻结`（无需同步创建，手工建一次即可）挂到某用户，
  即表示冻结该账号——同步不复活、不停用、不改其角色/姓名，统计进 manual_frozen。
  冻结中的离职人员同样不动，由管理员自行处理。
- **离职停用**（reason=departed）：用户名仍在 ODS SYS_EMPLOYEE 全集、但不在在职集合 → active=false。
- **工号物理消失**（reason=vanished）：用户名为纯数字工号、但已不在 ODS 全集（行被物理删除）
  → active=false。非数字用户名（MZ101/W00001/task 等接口账号，2026-10-12 实测 82 个）
  不在本路径内，物理消失也不触碰，留管理员处理。
- **熔断**：在职集合为空 / ODS 全集为空 / 科室字典为空 / 在职数低于 SYNC_MIN_ACTIVE /
  拟停用数超过 SYNC_MAX_DEACTIVATE_ABS 或占在职比超过 SYNC_MAX_DEACTIVATE_RATIO，
  任一触发即整体退出（退出码 1），不做任何写入。
"""
import fcntl
import json
import os
import re
import sys
import time
import urllib.parse

import oracledb
import requests

# 数据中心 Oracle 11.2.0.4 → Thick 模式（Instant Client 已在镜像内）
if oracledb.is_thin_mode():
    try:
        oracledb.init_oracle_client(lib_dir="/opt/oracle/instantclient")
    except Exception:  # noqa: BLE001 - 已初始化时忽略（幂等）
        pass

INIT_PWD = os.environ.get("INIT_PASSWORD", "<REDACTED-DEFAULT-EMPLOYEE-PW>")
DRY = "--dry-run" in sys.argv
PILOT = None
if "--pilot" in sys.argv:
    PILOT = sys.argv[sys.argv.index("--pilot") + 1]

RENAME_ONLY = "--rename-roles" in sys.argv
ROLE_NAME_MAX = 64  # ab_role.name varchar(64)，按字符计
DEPT_ROLE_PREFIX = "科室_"

# ---- 身份生命周期（2026-10-12 B2）----
FREEZE_ROLE_NAME = "人工冻结"  # 挂到用户=冻结：同步不复活、不停用、不改角色
MIN_ACTIVE = int(os.environ.get("SYNC_MIN_ACTIVE", "100"))  # 在职集合熔断下限（pilot 不校验）
MAX_DEACTIVATE_ABS = int(os.environ.get("SYNC_MAX_DEACTIVATE_ABS", "50"))
MAX_DEACTIVATE_RATIO = float(os.environ.get("SYNC_MAX_DEACTIVATE_RATIO", "0.10"))

stats = {
    "fetch": 0,
    "created": 0,
    "updated": 0,
    "unchanged": 0,
    "deactivated": 0,
    "deactivated_departed": 0,
    "deactivated_vanished": 0,
    "manual_frozen": 0,
    "rls_created": 0,
    "renamed": 0,
    "failed": 0,
}


def log(msg: str) -> None:
    print(f"[sync] {msg}", flush=True)


def die(msg: str) -> None:
    log(f"FATAL: {msg}")
    print(json.dumps(stats, ensure_ascii=False))
    sys.exit(1)


def retry(fn, n=3):
    last = None
    for i in range(n):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2**i)
    raise last


class SupersetAPI:
    def __init__(self, base: str, admin: str, pwd: str):
        self.base = base.rstrip("/")
        r = retry(
            lambda: requests.post(
                f"{self.base}/api/v1/security/login",
                json={"username": admin, "password": pwd, "provider": "db", "refresh": True},
                timeout=30,
            )
        )
        if r.status_code != 200:
            die(f"admin login failed: {r.status_code} {r.text[:200]}")
        self.token = r.json()["access_token"]
        self.s = requests.Session()
        self.s.headers.update(self._auth())
        c = retry(lambda: self.s.get(f"{self.base}/api/v1/security/csrf_token/", timeout=30))
        self.csrf = c.json()["result"]
        self.s.headers.update(self._auth())

    def _auth(self):
        return {"Authorization": f"Bearer {self.token}", "X-CSRFToken": getattr(self, "csrf", "")}

    def get(self, path, params=None):
        r = retry(lambda: self.s.get(f"{self.base}{path}", params=params, timeout=60))
        r.raise_for_status()
        return r.json()

    def post(self, path, payload):
        return retry(lambda: self.s.post(f"{self.base}{path}", json=payload, timeout=60))

    def put(self, path, payload):
        return retry(lambda: self.s.put(f"{self.base}{path}", json=payload, timeout=60))


def fetch_source():
    """(在职员工行, ODS 全体工号集, 科室字典)。"""
    conn = oracledb.connect(
        user=os.environ["SYNC_ORA_USER"], password=os.environ["SYNC_ORA_PWD"], dsn=os.environ["SYNC_ORA_DSN"]
    )
    cur = conn.cursor()
    where = "VALIDSTATE = '1' AND ISDELETED = 0"
    if PILOT:
        where += f" AND DEPTCODE = '{PILOT}'"
    cur.execute(f"SELECT EMPLCODE, EMPLNAME, DEPTCODE FROM HIS.SYS_EMPLOYEE WHERE {where} ORDER BY EMPLCODE")
    active = cur.fetchall()
    cur.execute("SELECT EMPLCODE FROM HIS.SYS_EMPLOYEE")
    all_codes = {r[0] for r in cur.fetchall()}
    cur.execute("SELECT DEPT_CODE, DEPT_NAME FROM HIS.DEPT_DICT")
    dept_names = {(c or "").strip(): (n or "") for c, n in cur.fetchall() if (c or "").strip()}
    cur.close()
    conn.close()
    return active, all_codes, dept_names


def write_mapping(rows):
    """SUP_USER_DEPT 映射表 MERGE（自建表，授权范围内）。"""
    conn = oracledb.connect(
        user=os.environ["SYNC_ORA_USER"], password=os.environ["SYNC_ORA_PWD"], dsn=os.environ["SYNC_ORA_DSN"]
    )
    cur = conn.cursor()
    cur.executemany(
        """
        BEGIN
          MERGE INTO SUP_USER_DEPT T
          USING (SELECT :1 AS EC, :2 AS DC FROM DUAL) S
          ON (T.EMPCODE = S.EC)
          WHEN MATCHED THEN UPDATE SET T.DEPTCODE = S.DC, T.SYNCED_AT = SYSDATE
          WHEN NOT MATCHED THEN INSERT (EMPCODE, DEPTCODE, SYNCED_AT) VALUES (S.EC, S.DC, SYSDATE);
        END;
        """,
        [(e, d) for e, d in rows],
    )
    conn.commit()
    cur.close()
    conn.close()


def load_paged(api: SupersetAPI, path: str, page_size: int = 100):
    """翻完列表接口。FAB 单页最多 100 条，只取第一页会漏掉后面的记录。"""
    rows, page = [], 0
    while True:
        j = api.get(path, params={"q": f"(page_size:{page_size},page:{page},order_by:id)"})
        batch = j.get("result") or []
        rows.extend(batch)
        page += 1
        total = int(j.get("count") or 0)
        if not batch or page * page_size >= total:
            break
    return rows


def load_roles(api: SupersetAPI):
    roles = {}
    for r in load_paged(api, "/api/v1/security/roles/"):
        roles[r["name"]] = r["id"]
    return roles


def sanitize_dept_label(name: str) -> str:
    """科室中文名压成可放进角色名的一段。全角括号留给编码后缀。"""
    text = (name or "").strip()
    text = re.sub(r"[\r\n\t]+", "", text)
    text = re.sub(r"\s+", "", text)
    text = text.replace("（", "(").replace("）", ")")
    text = text.replace("_", "－")
    return text


def dept_role_name(code: str, dept_names: dict) -> str:
    """发布下拉里可辨认的科室角色名。编码放在全角括号里，避免 role_01 撞上 role_0101。"""
    code = (code or "").strip()
    label = sanitize_dept_label(dept_names.get(code) or "") or "未对照"
    prefix = DEPT_ROLE_PREFIX
    suffix = f"（{code}）"
    room = ROLE_NAME_MAX - len(prefix) - len(suffix)
    if room < 1:
        return f"role_{code}"[:ROLE_NAME_MAX]
    if len(label) > room:
        label = label[:room]
    return f"{prefix}{label}{suffix}"


def is_dept_role_name(name: str) -> bool:
    return bool(name) and (name.startswith("role_") or name.startswith(DEPT_ROLE_PREFIX))


def dept_code_from_role_name(name: str):
    if name.startswith("role_"):
        code = name[len("role_") :]
        if code.isalnum():
            return code
        return None
    if name.startswith(DEPT_ROLE_PREFIX) and name.endswith("）") and "（" in name:
        code = name[name.rfind("（") + 1 : -1]
        if code.isalnum():
            return code
    return None


def find_dept_role(roles: dict, code: str):
    """按科室编码找角色，只做整段匹配。role_01 不会命中 role_0101。"""
    code = (code or "").strip()
    legacy = f"role_{code}"
    if legacy in roles:
        return legacy, roles[legacy]
    marker = f"（{code}）"
    hits = [(n, i) for n, i in roles.items() if n.startswith(DEPT_ROLE_PREFIX) and n.endswith(marker)]
    if not hits:
        return None, None
    if len(hits) > 1:
        log(f"WARN multiple roles for dept {code}: {[n for n, _ in hits]}")
    return hits[0]


def ensure_role(api: SupersetAPI, roles, name):
    if name not in roles:
        r = api.post("/api/v1/security/roles/", {"name": name})
        if r.status_code in (201, 200):
            roles[name] = r.json().get("id") or r.json().get("result", {}).get("id")
            log(f"role created: {name}")
        else:
            die(f"role create failed {name}: {r.status_code} {r.text[:200]}")
    return roles[name]


def ensure_dept_role(api: SupersetAPI, roles, code: str, dept_names: dict):
    """按科室编码找到角色并改成中文名；没有则新建。角色 id 不变，权限和看板绑定留在原 id 上。"""
    code = (code or "").strip()
    target = dept_role_name(code, dept_names)
    if len(target) > ROLE_NAME_MAX:
        die(f"role name too long for {code}: {len(target)}")
    current, rid = find_dept_role(roles, code)
    if rid is None:
        if DRY:
            log(f"dry-run would create role {target}")
            return None
        return ensure_role(api, roles, target)
    if current == target:
        return rid
    if target in roles and roles[target] != rid:
        die(f"role name taken {target} id {roles[target]} vs {rid}")
    if DRY:
        log(f"dry-run rename {current} -> {target}")
    else:
        r = api.put(f"/api/v1/security/roles/{rid}", {"name": target})
        if r.status_code not in (200, 201):
            die(f"role rename failed {current} -> {target}: {r.status_code} {r.text[:300]}")
        log(f"role rename {current} -> {target}")
    stats["renamed"] += 1
    roles.pop(current, None)
    roles[target] = rid
    return rid


def rename_dept_roles(api: SupersetAPI, roles, dept_names: dict) -> None:
    """把已有 role_<编码> / 旧中文名收成当前科室字典里的展示名。"""
    planned = []
    seen_target = {}
    missing_codes = []
    for name, rid in list(roles.items()):
        code = dept_code_from_role_name(name)
        if not code:
            continue
        if code not in dept_names:
            missing_codes.append(code)
        target = dept_role_name(code, dept_names)
        other = seen_target.get(target)
        if other is not None and other != rid:
            die(f"duplicate display name {target}")
        seen_target[target] = rid
        if name != target:
            planned.append(code)
    if missing_codes:
        log("dept code not in DEPT_DICT: " + ",".join(sorted(set(missing_codes))))
    log(f"dept roles to rename: {len(planned)}")
    for code in planned:
        ensure_dept_role(api, roles, code, dept_names)


def load_users_index(api: SupersetAPI):
    """全量分页拉用户建 username->user 索引（6.1 users 端点不支持列过滤）。"""
    idx, page = {}, 0
    while True:
        j = api.get("/api/v1/security/users/", params={"q": f"(page_size:100,page:{page},order_by:id)"})
        for u in j["result"]:
            if u.get("username"):
                idx[u["username"]] = u
        page += 1
        if page * 100 >= j["count"]:
            break
    return idx


def user_role_ids(u):
    out = []
    for entry in u.get("roles", []):
        if isinstance(entry, dict):
            out.append((entry.get("id"), entry.get("name", "")))
        else:
            out.append((entry, ""))
    return out


def is_frozen(u) -> bool:
    """人工冻结（B2）：用户挂有 `人工冻结` 角色。users 端点返回的 roles 含 name。"""
    for entry in u.get("roles", []):
        name = entry.get("name") if isinstance(entry, dict) else None
        if name == FREEZE_ROLE_NAME:
            return True
    return False


def sync_users(api: SupersetAPI, active, roles, users_index, dept_names):
    gamma_id = roles.get("Gamma") or die("Gamma role missing")
    depts_seen = set()
    for emplcode, emplname, deptcode in active:
        deptcode = (deptcode or "").strip()
        if deptcode:
            depts_seen.add(deptcode)
            target_roles = [gamma_id, ensure_dept_role(api, roles, deptcode, dept_names)]
        else:
            target_roles = [gamma_id]
        try:
            u = users_index.get(emplcode)
            if u is not None and is_frozen(u):
                # 人工冻结（B2）：不复活、不改名、不改角色，交管理员处置
                stats["manual_frozen"] += 1
                log(f"manual frozen, skip {emplcode}")
                continue
            if u is None:
                if DRY:
                    log(f"dry-run would create user {emplcode}")
                    stats["created"] += 1
                    continue
                r = api.post(
                    "/api/v1/security/users/",
                    {
                        "username": emplcode,
                        "first_name": emplname or "",
                        "last_name": "",
                        "email": f"{emplcode}@superset.local",
                        "password": INIT_PWD,  # 仅创建时设，不覆盖已改密码
                        "active": True,
                        "roles": target_roles,
                    },
                )
                if r.status_code not in (201, 200):
                    raise RuntimeError(f"create {r.status_code} {r.text[:200]}")
                stats["created"] += 1
                users_index[emplcode] = {"id": r.json().get("id"), "username": emplcode}
            else:
                cur = user_role_ids(u)
                non_dept_ids = sorted({rid for rid, rname in cur if rid and not is_dept_role_name(rname)})
                merged = sorted(set(non_dept_ids) | set(target_roles))
                cur_ids = sorted({rid for rid, _ in cur})
                changed = (
                    merged != cur_ids
                    or not u.get("active")
                    or (u.get("first_name") or "") != (emplname or "")
                )
                if changed:
                    if DRY:
                        log(f"dry-run would update user {emplcode}")
                    else:
                        r = api.put(f"/api/v1/security/users/{u['id']}", {"first_name": emplname or "", "active": True, "roles": merged})
                        if r.status_code not in (200, 201):
                            raise RuntimeError(f"update {r.status_code} {r.text[:200]}")
                    stats["updated"] += 1
                else:
                    stats["unchanged"] += 1
        except Exception as exc:  # noqa: BLE001
            stats["failed"] += 1
            log(f"FAILED user {emplcode}: {exc}")
    return sorted(depts_seen)


def deactivate_departed(api: SupersetAPI, all_codes, active_codes):
    """停用路径（B2 重写，两阶段）。

    候选判定（只对 active=true 用户）：
      departed = 用户名在 ODS 全集但不在在职集合（原行为保留）；
      vanished = 用户名为纯数字工号且已不在 ODS 全集（行被物理删除，B2 新增）。
    非数字用户名（MZ101/W00001/task 等接口账号）不在 vanished 路径内，物理消失也不触碰。
    admin 永不触碰；挂 `人工冻结` 角色的用户永不触碰（计入 manual_frozen）。

    熔断（执行前整体判定，触发即 die，一个停用都不执行）：
      拟停用总数 > SYNC_MAX_DEACTIVATE_ABS，或 > SYNC_MAX_DEACTIVATE_RATIO × 在职数。
    pilot 模式跳过停用（原行为）。
    """
    if PILOT:
        log("pilot mode: skip deactivation")
        return
    active_set = set(active_codes)
    departed, vanished = [], []
    page = 0
    while True:
        j = api.get("/api/v1/security/users/", params={"q": f"(page_size:100,page:{page},order_by:id)"})
        for u in j["result"]:
            un = u.get("username", "")
            if un in ("admin",) or not un or not u.get("active"):
                continue
            if is_frozen(u):
                stats["manual_frozen"] += 1
                log(f"manual frozen, keep {un}")
                continue
            if un in all_codes and un not in active_set:
                departed.append(u)
            elif un not in all_codes and re.fullmatch(r"\d+", un):
                vanished.append(u)
        page += 1
        if page * 100 >= j["count"]:
            break
    n = len(departed) + len(vanished)
    ratio_limit = max(1, int(MAX_DEACTIVATE_RATIO * max(len(active_set), 1)))
    if n > MAX_DEACTIVATE_ABS or n > ratio_limit:
        die(
            f"停用规模熔断：拟停用 {n}（departed={len(departed)}, vanished={len(vanished)}）"
            f"超过上限 abs={MAX_DEACTIVATE_ABS} / ratio_limit={ratio_limit}；未执行任何停用，请人工核查源表"
        )
    if n == 0:
        log("no deactivation candidates")
        return
    for reason, group in (("departed", departed), ("vanished", vanished)):
        for u in group:
            un = u["username"]
            if DRY:
                stats["deactivated"] += 1
                stats[f"deactivated_{reason}"] += 1
                log(f"dry-run would deactivate ({reason}) {un}")
                continue
            r = api.put(f"/api/v1/security/users/{u['id']}", {"active": False})
            if r.status_code in (200, 201):
                stats["deactivated"] += 1
                stats[f"deactivated_{reason}"] += 1
                log(f"deactivated ({reason}) {un}")
            else:
                stats["failed"] += 1
                log(f"deactivate failed {un}: {r.status_code} {r.text[:180]}")


def ensure_rls(api: SupersetAPI, table_id, dept_codes, roles):
    """每科室角色一条 Regular 常量规则 DEPT_CODE='<码>'；已存在则确保角色绑定。

    必须翻完整列表。接口单页上限 100，只看第一页时后 200 多条已有规则会被再次 POST，
    撞上 uq_rls_name，当天日志仍显示 failed=0。
    """
    existing = {}
    for row in load_paged(api, "/api/v1/rowlevelsecurity/"):
        if row.get("name"):
            existing[row["name"]] = row
    log(f"rls listed={len(existing)}")
    for code in dept_codes:
        role_name, rid = find_dept_role(roles, code)
        if not rid:
            continue
        name = f"rls_{table_id}_{code}"
        have = existing.get(name)
        have_role_ids = (
            [rr["id"] for rr in have.get("roles", []) if isinstance(rr, dict)]
            if have
            else []
        )
        if have is None:
            if DRY:
                log(f"dry-run would create rls {name}")
                continue
            r = api.post(
                "/api/v1/rowlevelsecurity/",
                {
                    "name": name,
                    "description": f"auto: dept {code} row filter (sync)",
                    "filter_type": "Regular",
                    "group_key": None,
                    "tables": [table_id],
                    "clause": f"DEPT_CODE = '{code}'",
                    "roles": [rid],
                },
            )
            log(f"rls create {name}: {r.status_code}")
            if r.status_code in (201, 200):
                stats["rls_created"] += 1
            else:
                stats["failed"] += 1
                log(f"rls create failed {name}: {r.status_code} {r.text[:180]}")
        elif rid not in have_role_ids:
            if DRY:
                log(f"dry-run would bind rls {name}")
                continue
            r = api.put(
                f"/api/v1/rowlevelsecurity/{have['id']}",
                {"roles": sorted(set(have_role_ids + [rid]))},
            )
            log(f"rls bind {role_name}: {r.status_code}")
            if r.status_code not in (200, 201):
                stats["failed"] += 1
                log(f"rls bind failed {name}: {r.status_code} {r.text[:180]}")


def acquire_sync_lock(timeout_s=1800):
    """P0-S3：与迁移写互斥。同一容器同一路径 /tmp/user_sync.lock，独占、有界阻塞等待。

    迁移持锁时同步等待（默认至多 1800s，SYNC_LOCK_TIMEOUT 可调）；
    超时 exit 3——宁可失败告警，绝不无锁并发写。
    """
    lock = open("/tmp/user_sync.lock", "w")
    deadline = time.time() + int(os.environ.get("SYNC_LOCK_TIMEOUT", str(timeout_s)))
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return lock
        except BlockingIOError:
            if time.time() >= deadline:
                sys.stderr.write("user_sync: /tmp/user_sync.lock busy, timeout reached, abort\n")
                sys.exit(3)
            time.sleep(5)


def main():
    lock = acquire_sync_lock()
    mode = f"PILOT={PILOT}" if PILOT else "FULL"
    if RENAME_ONLY:
        mode = "RENAME"
    log(f"start mode={mode} dry={DRY}")
    active, all_codes, dept_names = fetch_source()
    stats["fetch"] = len(active)
    log(f"source active={len(active)} universe={len(all_codes)} depts={len(dept_names)}")
    # 源侧熔断（B2）：任一触发即退出，不登录 API、不做任何写入。
    if len(all_codes) == 0:
        die("ODS 工号全集为空：源表/查询异常，熔断退出")
    if not dept_names:
        die("科室字典为空：否则全部科室角色会被改名为「未对照」，熔断退出")
    if len(active) == 0:
        die("在职集合为空：源表/查询异常，熔断退出（避免全量误停用）")
    if not PILOT and len(active) < MIN_ACTIVE:
        die(f"在职集合 {len(active)} < SYNC_MIN_ACTIVE={MIN_ACTIVE}：疑似源表截断/口径变化，熔断退出")
    api = SupersetAPI(os.environ["SUP_BASE"], os.environ["SUP_ADMIN"], os.environ["SUP_ADMIN_PWD"])
    roles = load_roles(api)
    rename_dept_roles(api, roles, dept_names)
    if RENAME_ONLY:
        log(f"done {json.dumps(stats, ensure_ascii=False)}")
        print(json.dumps(stats, ensure_ascii=False))
        sys.exit(0 if stats["failed"] == 0 else 1)
    users_index = load_users_index(api)
    log(f"users index size={len(users_index)}")
    dept_list = sync_users(api, active, roles, users_index, dept_names)
    deactivate_departed(api, all_codes, {r[0] for r in active})
    if not DRY:
        write_mapping([(e, (d or "").strip()) for e, _, d in active])
        log("mapping table merged")
    table_id = int(os.environ.get("RLS_TABLE_ID", "0") or 0)
    if table_id > 0:
        # 2026-10-14 NAVCLEAN：RLS 目标存在/有效性检查。正数目标必须存在且未退役，
        # 否则明确报错退出——不为失效/退役目标反复创建规则。0=本批关闭 RLS 目标。
        try:
            ds = api.get(f"/api/v1/dataset/{table_id}")
        except requests.exceptions.HTTPError as exc:
            die(f"RLS_TABLE_ID={table_id} 数据集不可达/不存在（{exc}）：拒绝创建 RLS；如无需 RLS 请设 RLS_TABLE_ID=0")
        ds_title = ((ds or {}).get("result") or {}).get("table_name") or ""
        if str(ds_title).startswith("[已退役"):
            die(f"RLS_TABLE_ID={table_id} 指向已退役数据集「{ds_title}」：拒绝创建 RLS；请改指有效数据集或设 RLS_TABLE_ID=0")
        ensure_rls(api, table_id, dept_list, roles)
    log(f"done {json.dumps(stats, ensure_ascii=False)}")
    print(json.dumps(stats, ensure_ascii=False))
    sys.exit(0 if stats["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
