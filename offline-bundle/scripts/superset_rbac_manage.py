#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
superset_rbac_manage.py — 报表授权_ 角色人员赋权管理工具（阶段2）

用途
----
管理 20261120-RBAC-BACKEND 阶段1建立的 11 个「报表授权_」标准角色的人员赋权。
只做人员↔角色绑定（ab_user_role 通道，经 REST /api/v1/security/users/<pk>），
不动角色定义、看板绑定、数据集授权（那些由 apply/rollback_rbac_matrix.py 管理）。

环境变量（一律外部注入，禁止硬编码）
------------------------------------
  SUP_BASE      如 http://superset-web:8088（容器内）或 http://127.0.0.1:8180
  SUP_ADMIN     管理员用户名（admin）
  SUP_ADMIN_PWD 管理员密码
  PGPASSWORD    PG 只读查询用密码
  RBAC_PG_HOST / RBAC_PG_PORT / RBAC_PG_DB / RBAC_PG_USER  默认 postgres:5432/superset/superset

子命令
------
  status                  轻量计数总览 → /tmp/rbac_status.json
  audit                   全量赋权审计（角色→成员、用户→角色、受保护绑定核查）→ /tmp/rbac_audit.json
  grant-user   --username 003158 --role 报表授权_护理部管理 [--dry-run]
  revoke-user  --username 003158 --role 报表授权_护理部管理 [--dry-run]
  grant-dept   --dept-code 0104 --role 报表授权_护理部管理 [--dry-run]
  revoke-dept  --dept-code 0104 --role 报表授权_护理部管理 [--dry-run]
  sync-policy  [--dry-run(default)|--apply]   按 rbac_policy.json 补齐职能科室赋权

行为约定（红线）
--------------
1. 目标角色必须以「报表授权_」开头，否则拒绝执行（保护 Gamma/Admin/科室_/role_ 通道）。
2. 受保护绑定：001283↔报表授权_病案离院明细、001643↔报表授权_抗菌办（人工冻结）。
   任何会导致摘除这两条绑定的操作一律拒绝（revoke 拒绝该用户；sync-policy 只报告）。
3. 写操作前持有 /tmp/user_sync.lock（fcntl.flock），避免与每日 06:00 用户同步互踩。
4. 用户 roles 走 PUT 全量替换：先读现值、合并/排除目标角色、回写，再 DB 回读断言，
   绝不覆盖 Gamma/科室_/role_ 等既有角色。
5. 科室角色命名格式：科室_<名称>（<6位码>）——全角括号，正则 ^科室_(.+)（([0-9]+)）$。
6. sync-policy 的 extra（policy 外已有的报表授权_ 角色）只报告不回收（审慎原则）。
7. 科室成员名单 = 科室_XXX（码） 角色成员（由每日同步维护），仅对 active 用户操作。

退出码：0=成功（或 dry-run 完成）；2=执行期失败/部分失败；3=前置校验拒绝。
"""

import argparse
import fcntl
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone

import psycopg2
import requests

TZ = timezone(timedelta(hours=8))
ROLE_PREFIX = "报表授权_"
DEPT_ROLE_RE = re.compile(r"^科室_(.+)（([0-9]+)）$")
LOCK_PATH = "/tmp/user_sync.lock"
POLICY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rbac_policy.json")

# 受保护绑定（人工冻结，绝不自动摘除）
PROTECTED_BINDINGS = [
    {"username": "001283", "role": ROLE_PREFIX + "病案离院明细",
     "reason": "20261108 人工冻结：病案离院明细专项维护人"},
    {"username": "001643", "role": ROLE_PREFIX + "抗菌办",
     "reason": "20261108 人工冻结：抗菌药物专项维护人"},
]


def now_iso():
    return datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%S%z")


def die(code, msg):
    print("FATAL: %s" % msg, file=sys.stderr)
    sys.exit(code)


def require_role_name(name, action):
    if not (name or "").startswith(ROLE_PREFIX):
        die(3, "拒绝%s：目标角色「%s」不是「%s」前缀。本工具只管理报表授权_ 角色的人员赋权。"
              % (action, name, ROLE_PREFIX))


def is_protected(username, role_name):
    return any(p["username"] == username and p["role"] == role_name for p in PROTECTED_BINDINGS)


class Lock:
    """与 superset_user_sync.py 同一把 /tmp/user_sync.lock，写操作必须持有。"""

    def __init__(self, timeout=120):
        self.timeout = timeout
        self.fd = None

    def __enter__(self):
        self.fd = open(LOCK_PATH, "a+")
        waited = 0
        while True:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                if waited >= self.timeout:
                    self.fd.close()
                    die(2, "获取 %s 超时（%ds），疑似用户同步正在运行，请稍后重试"
                        % (LOCK_PATH, self.timeout))
                time.sleep(2)
                waited += 2

    def __exit__(self, *exc):
        try:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
        finally:
            self.fd.close()
        return False


class Db:
    """只读 PG 连接：全量拉取角色/用户绑定快照。"""

    def __init__(self):
        self.conn = psycopg2.connect(
            host=os.environ.get("RBAC_PG_HOST", "postgres"),
            port=int(os.environ.get("RBAC_PG_PORT", "5432")),
            dbname=os.environ.get("RBAC_PG_DB", "superset"),
            user=os.environ.get("RBAC_PG_USER", "superset"),
            password=os.environ["PGPASSWORD"],
        )
        self.conn.autocommit = True
        self.cur = self.conn.cursor()

    def q(self, sql, args=None):
        self.cur.execute(sql, args or ())
        cols = [d[0] for d in self.cur.description]
        return [dict(zip(cols, row)) for row in self.cur.fetchall()]

    def close(self):
        self.cur.close()
        self.conn.close()


def read_snapshot(db):
    """一次性读全：角色表、用户表、ab_user_role 全量。返回内存映射。"""
    roles = {r["id"]: r["name"] for r in db.q("SELECT id,name FROM ab_role ORDER BY id")}
    users = {u["id"]: u for u in db.q(
        "SELECT id,username,active FROM ab_user ORDER BY id")}
    user_roles = {uid: set() for uid in users}
    for row in db.q("SELECT user_id,role_id FROM ab_user_role"):
        user_roles.setdefault(row["user_id"], set()).add(row["role_id"])
    return {"roles": roles, "users": users, "user_roles": user_roles}


def username_of(snapshot, uid):
    u = snapshot["users"].get(uid)
    return u["username"] if u else None


def find_user(snapshot, username):
    for u in snapshot["users"].values():
        if u["username"] == username:
            return u
    return None


def find_role_id(snapshot, role_name):
    for rid, name in snapshot["roles"].items():
        if name == role_name:
            return rid
    return None


def find_dept_role(snapshot, dept_code):
    """按 6 位码匹配 科室_<名称>（<码>） 角色名（全角括号）。"""
    code = str(dept_code)
    for rid, name in snapshot["roles"].items():
        m = DEPT_ROLE_RE.match(name or "")
        if m and m.group(2) == code:
            return rid, name
    return None, None


def dept_members(snapshot, dept_role_id):
    """科室角色成员（active 用户），返回 [(user_id, username)]。"""
    out = []
    for uid, rids in snapshot["user_roles"].items():
        if dept_role_id in rids:
            u = snapshot["users"].get(uid)
            if u and u["active"]:
                out.append((uid, u["username"]))
    return sorted(out, key=lambda x: (len(x[1]), x[1]))


class Api:
    """REST 写通道三件套：Session 保 cookie + Bearer + X-CSRFToken（实测口径）。"""

    def __init__(self, base, admin, password):
        if not (base and admin and password):
            die(3, "缺少 SUP_BASE / SUP_ADMIN / SUP_ADMIN_PWD 环境变量")
        self.base = base.rstrip("/")
        self.s = requests.Session()
        r = self.s.post(self.base + "/api/v1/security/login",
                        json={"username": admin, "password": password,
                              "provider": "db", "refresh": True}, timeout=60)
        if r.status_code != 200:
            die(2, "登录失败 %s: %s" % (r.status_code, r.text[:300]))
        token = r.json().get("access_token")
        self.s.headers["Authorization"] = "Bearer " + token
        r = self.s.get(self.base + "/api/v1/security/csrf_token/", timeout=60)
        if r.status_code != 200:
            die(2, "获取 CSRF token 失败 %s: %s" % (r.status_code, r.text[:300]))
        self.s.headers["X-CSRFToken"] = r.json()["result"]

    def get_user(self, uid):
        r = self.s.get(self.base + "/api/v1/security/users/%d" % uid, timeout=60)
        if r.status_code != 200:
            raise RuntimeError("GET users/%d → %s %s" % (uid, r.status_code, r.text[:300]))
        return r.json()["result"]

    def put_roles(self, uid, role_ids):
        r = self.s.put(self.base + "/api/v1/security/users/%d" % uid,
                       json={"roles": sorted(int(x) for x in role_ids)}, timeout=60)
        if r.status_code != 200:
            raise RuntimeError("PUT users/%d roles=%s → %s %s"
                               % (uid, sorted(role_ids), r.status_code, r.text[:300]))
        return r.json()["result"]


def write_json(name, obj):
    path = os.path.join("/tmp", name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print("REPORT_JSON %s" % path)


def role_label(snapshot, rid):
    return "%s(%d)" % (snapshot["roles"].get(rid, "?"), rid)


def labels_of(snapshot, rids):
    return sorted(role_label(snapshot, r) for r in rids)


# ---------------------------------------------------------------- 子命令实现

def apply_user_role_change(db, api, snapshot, user, target_role_name, add, dry_run,
                           report, refused=None):
    """单用户增/删一个角色。PUT 全量替换（现值∪{目标} 或 现值−{目标}）。
    返回 (status, detail)：status ∈ no_change / planned / applied / refused / error。
    refused 传入时表示已由上层判定的拒绝（受保护绑定）。"""
    uid = user["id"]
    username = user["username"]
    target_rid = find_role_id(snapshot, target_role_name)
    if target_rid is None:
        die(3, "角色不存在：%s" % target_role_name)
    current = snapshot["user_roles"].get(uid, set())

    if refused:
        report.append({"username": username, "role": target_role_name,
                       "status": "refused_protected",
                       "reason": refused, "current": labels_of(snapshot, current)})
        return "refused", None

    if add:
        target_ids = current | {target_rid}
        if target_rid in current:
            report.append({"username": username, "role": target_role_name,
                           "status": "no_change", "current": labels_of(snapshot, current)})
            return "no_change", None
    else:
        if is_protected(username, target_role_name):
            reason = "受保护绑定（人工冻结），拒绝摘除"
            report.append({"username": username, "role": target_role_name,
                           "status": "refused_protected", "reason": reason,
                           "current": labels_of(snapshot, current)})
            return "refused", None
        if target_rid not in current:
            report.append({"username": username, "role": target_role_name,
                           "status": "no_change", "current": labels_of(snapshot, current)})
            return "no_change", None
        target_ids = current - {target_rid}

    if dry_run:
        report.append({"username": username, "role": target_role_name,
                       "status": "planned",
                       "before": labels_of(snapshot, current),
                       "after": labels_of(snapshot, target_ids)})
        return "planned", None

    with Lock():
        # 锁内重读该用户现值，防止与同步并发漂移
        fresh = db.q("SELECT role_id FROM ab_user_role WHERE user_id=%s", (uid,))
        current = {r["role_id"] for r in fresh}
        target_ids = (current | {target_rid}) if add else (current - {target_rid})
        if add and target_rid in current:
            report.append({"username": username, "role": target_role_name,
                           "status": "no_change"})
            return "no_change", None
        if (not add) and target_rid not in current:
            report.append({"username": username, "role": target_role_name,
                           "status": "no_change"})
            return "no_change", None
        if (not add) and is_protected(username, target_role_name):
            report.append({"username": username, "role": target_role_name,
                           "status": "refused_protected",
                           "reason": "受保护绑定（人工冻结），拒绝摘除"})
            return "refused", None
        api.put_roles(uid, target_ids)
        # DB 回读断言：全量替换后应精确等于 target_ids
        fresh2 = db.q("SELECT role_id FROM ab_user_role WHERE user_id=%s", (uid,))
        after = {r["role_id"] for r in fresh2}
        if after != target_ids:
            raise RuntimeError("回读断言失败 user=%s after=%s expected=%s"
                               % (username, sorted(after), sorted(target_ids)))
        snapshot["user_roles"][uid] = set(after)
        report.append({"username": username, "role": target_role_name,
                       "status": "applied",
                       "before": labels_of(snapshot, current),
                       "after": labels_of(snapshot, after)})
        return "applied", None


def cmd_user_change(args, add):
    action = "grant-user" if add else "revoke-user"
    require_role_name(args.role, action)
    db = Db()
    snapshot = read_snapshot(db)
    user = find_user(snapshot, args.username)
    if user is None:
        die(3, "用户不存在：%r" % args.username)
    api = None if args.dry_run else Api(os.environ.get("SUP_BASE"),
                                        os.environ.get("SUP_ADMIN"),
                                        os.environ.get("SUP_ADMIN_PWD"))
    report = []
    entry = {"command": action, "ts": now_iso(), "dry_run": bool(args.dry_run),
             "username": args.username, "user_id": user["id"],
             "role": args.role, "changes": report}
    status, _ = apply_user_role_change(db, api, snapshot, user, args.role, add,
                                       args.dry_run, report)
    entry["result"] = status
    write_json("rbac_%s.json" % ("grant_user" if add else "revoke_user"), entry)
    db.close()
    print("%s → %s" % (action, status))
    if status == "refused":
        sys.exit(3)  # 受保护绑定/受拒操作：明确退出码供验收脚本（PR1/PR2）判定


def cmd_dept_change(args, add):
    action = "grant-dept" if add else "revoke-dept"
    require_role_name(args.role, action)
    db = Db()
    snapshot = read_snapshot(db)
    dept_rid, dept_name = find_dept_role(snapshot, args.dept_code)
    if dept_rid is None:
        die(3, "科室角色不存在：找不到 科室_XXX（%s）" % args.dept_code)
    members = dept_members(snapshot, dept_rid)
    api = None if args.dry_run else Api(os.environ.get("SUP_BASE"),
                                        os.environ.get("SUP_ADMIN"),
                                        os.environ.get("SUP_ADMIN_PWD"))
    report = []
    stats = {"applied": 0, "planned": 0, "no_change": 0, "refused": 0, "error": 0}
    errors = []
    for uid, username in members:
        user = snapshot["users"][uid]
        try:
            status, _ = apply_user_role_change(db, api, snapshot, user, args.role,
                                               add, args.dry_run, report)
            stats[status] = stats.get(status, 0) + 1
        except Exception as e:  # 单人失败不中断整科室
            stats["error"] += 1
            errors.append({"username": username, "error": str(e)})
    entry = {"command": action, "ts": now_iso(), "dry_run": bool(args.dry_run),
             "dept_code": str(args.dept_code), "dept_role": dept_name,
             "role": args.role, "member_count": len(members),
             "stats": stats, "changes": report}
    if errors:
        entry["errors"] = errors
    write_json("rbac_%s_%s.json" % ("grant_dept" if add else "revoke_dept",
                                    args.dept_code), entry)
    db.close()
    print("%s（%s→%s）成员 %d 人：%s" % (action, dept_name, args.role, len(members), stats))
    if stats.get("error"):
        sys.exit(2)


def cmd_status(args):
    db = Db()
    snapshot = read_snapshot(db)
    rbac_roles = {rid: name for rid, name in snapshot["roles"].items()
                  if (name or "").startswith(ROLE_PREFIX)}
    members = {rid: sorted(username_of(snapshot, uid)
                           for uid, rids in snapshot["user_roles"].items()
                           if rid in rids and snapshot["users"].get(uid, {}).get("active"))
               for rid in rbac_roles}
    protected_ok = []
    for p in PROTECTED_BINDINGS:
        u = find_user(snapshot, p["username"])
        rid = find_role_id(snapshot, p["role"])
        ok = bool(u and rid and rid in snapshot["user_roles"].get(u["id"], set()))
        protected_ok.append({"username": p["username"], "role": p["role"],
                             "in_place": ok})
    entry = {"command": "status", "ts": now_iso(),
             "counts": {"roles_total": len(snapshot["roles"]),
                        "rbac_roles": len(rbac_roles),
                        "users_total": len(snapshot["users"]),
                        "active_users": sum(1 for u in snapshot["users"].values() if u["active"]),
                        "user_role_rows": sum(len(v) for v in snapshot["user_roles"].values())},
             "rbac_roles_members": {rbac_roles[rid]: {"role_id": rid,
                                                     "member_count": len(ms),
                                                     "members": ms}
                                     for rid, ms in members.items()},
             "protected_bindings": protected_ok}
    write_json("rbac_status.json", entry)
    db.close()
    print("status: roles=%d rbac_roles=%d users=%d protected=%s"
          % (entry["counts"]["roles_total"], len(rbac_roles),
             entry["counts"]["users_total"],
             "ALL_OK" if all(x["in_place"] for x in protected_ok) else "MISSING!"))


def cmd_audit(args):
    db = Db()
    snapshot = read_snapshot(db)
    rbac_rids = {rid for rid, name in snapshot["roles"].items()
                 if (name or "").startswith(ROLE_PREFIX)}
    dept_rids = {rid for rid, name in snapshot["roles"].items()
                 if DEPT_ROLE_RE.match(name or "")}

    role_members = {rid: sorted(username_of(snapshot, uid)
                                for uid, rids in snapshot["user_roles"].items()
                                if rid in rids) for rid in rbac_rids}
    user_rbac = {}
    for uid, rids in snapshot["user_roles"].items():
        mine = sorted(snapshot["roles"][r] for r in rids if r in rbac_rids)
        if mine:
            u = snapshot["users"].get(uid)
            user_rbac[u["username"] if u else str(uid)] = {
                "user_id": uid, "active": bool(u and u["active"]),
                "rbac_roles": mine,
                "other_roles": sorted(snapshot["roles"][r] for r in rids
                                       if r not in rbac_rids and r not in dept_rids),
                "dept_roles": sorted(snapshot["roles"][r] for r in rids if r in dept_rids)}

    protected = []
    for p in PROTECTED_BINDINGS:
        u = find_user(snapshot, p["username"])
        rid = find_role_id(snapshot, p["role"])
        protected.append({"username": p["username"], "role": p["role"],
                          "in_place": bool(u and rid and rid in snapshot["user_roles"].get(u["id"], set())),
                          "user_found": bool(u), "active": bool(u and u["active"])})

    # 命名规范核查：任何不在已知前缀集合的自定义角色都点名（信息项，不判失败）
    known_prefixes = (ROLE_PREFIX, "Admin", "Alpha", "Gamma", "Public", "sql_lab",
                      "科室_", "role_")
    odd_roles = sorted(name for name in snapshot["roles"].values()
                       if not any((name or "").startswith(px) for px in known_prefixes))

    entry = {"command": "audit", "ts": now_iso(),
             "counts": {"rbac_roles": len(rbac_rids),
                        "users_with_rbac": len(user_rbac),
                        "total_rbac_bindings": sum(len(v["rbac_roles"])
                                                   for v in user_rbac.values())},
             "role_members": {snapshot["roles"][rid]: v
                              for rid, v in sorted(role_members.items())},
             "user_rbac_roles": dict(sorted(user_rbac.items())),
             "protected_bindings": protected,
             "odd_named_roles": odd_roles}
    write_json("rbac_audit.json", entry)
    db.close()
    print("audit: rbac_roles=%d users_with_rbac=%d bindings=%d protected=%s odd_roles=%d"
          % (entry["counts"]["rbac_roles"], entry["counts"]["users_with_rbac"],
             entry["counts"]["total_rbac_bindings"],
             "ALL_OK" if all(x["in_place"] for x in protected) else "MISSING!",
             len(odd_roles)))


def cmd_sync_policy(args):
    if not os.path.exists(POLICY_FILE):
        die(3, "策略文件不存在：%s" % POLICY_FILE)
    with open(POLICY_FILE, encoding="utf-8") as f:
        policy = json.load(f)
    if args.apply and args.dry_run:
        die(3, "--apply 与 --dry-run 互斥，请只给其一")
    dry_run = not args.apply

    db = Db()
    snapshot = read_snapshot(db)
    api = None if dry_run else Api(os.environ.get("SUP_BASE"),
                                   os.environ.get("SUP_ADMIN"),
                                   os.environ.get("SUP_ADMIN_PWD"))

    problems = []
    dept_reports = []
    stats = {"users_to_change": 0, "bindings_planned": 0, "bindings_applied": 0,
             "extra_bindings": 0, "protected_kept": 0, "no_change_users": 0}

    for dept in policy.get("departments", []):
        code = str(dept["dept_code"])
        expected_names = list(dept.get("roles", []))
        for rn in expected_names:
            require_role_name(rn, "sync-policy")
        dept_rid, dept_name = find_dept_role(snapshot, code)
        if dept_rid is None:
            problems.append({"dept_code": code, "error": "科室角色不存在"})
            continue
        expected_rids = {}
        for rn in expected_names:
            rid = find_role_id(snapshot, rn)
            if rid is None:
                problems.append({"dept_code": code, "error": "角色不存在：%s" % rn})
            else:
                expected_rids[rid] = rn
        members = dept_members(snapshot, dept_rid)
        actions = []
        extras = []
        for uid, username in members:
            user = snapshot["users"][uid]
            current = snapshot["user_roles"].get(uid, set())
            current_rbac = {r for r in current if r in expected_rids.keys()
                            or (snapshot["roles"].get(r, "").startswith(ROLE_PREFIX))}
            missing_rids = set(expected_rids.keys()) - current_rbac
            extra_rbac = current_rbac - set(expected_rids.keys())
            for erid in extra_rbac:
                if is_protected(username, snapshot["roles"][erid]):
                    stats["protected_kept"] += 1
            rec = {"username": username, "user_id": uid,
                   "current_rbac": sorted(snapshot["roles"][r] for r in current_rbac),
                   "missing": sorted(expected_rids[r] for r in missing_rids),
                   "extra": sorted(snapshot["roles"][r] for r in extra_rbac)}
            if missing_rids:
                stats["users_to_change"] += 1
                stats["bindings_planned" if dry_run else "bindings_applied"] += len(missing_rids)
                if args.apply:
                    try:
                        with Lock():
                            fresh = db.q("SELECT role_id FROM ab_user_role WHERE user_id=%s", (uid,))
                            current = {r["role_id"] for r in fresh}
                            target_ids = current | set(missing_rids)
                            api.put_roles(uid, target_ids)
                            fresh2 = db.q("SELECT role_id FROM ab_user_role WHERE user_id=%s", (uid,))
                            after = {r["role_id"] for r in fresh2}
                            if not set(missing_rids) <= after:
                                raise RuntimeError("回读断言失败 user=%s" % username)
                            snapshot["user_roles"][uid] = set(after)
                        rec["status"] = "applied"
                    except Exception as e:
                        rec["status"] = "error"
                        rec["error"] = str(e)
                        problems.append({"dept_code": code, "username": username,
                                         "error": str(e)})
                else:
                    rec["status"] = "planned"
                actions.append(rec)
            else:
                stats["no_change_users"] += 1
            if extra_rbac:
                stats["extra_bindings"] += len(extra_rbac)
                extras.append(rec)
        dept_reports.append({
            "dept_code": code, "dept_name": dept.get("dept_name", ""),
            "dept_role": dept_name, "policy_roles": expected_names,
            "member_count": len(members), "actions": actions, "extras": extras})

    entry = {"command": "sync-policy", "ts": now_iso(), "dry_run": dry_run,
             "policy_version": policy.get("version"),
             "policy_updated": policy.get("updated"),
             "stats": stats, "departments": dept_reports}
    if problems:
        entry["problems"] = problems
    write_json("rbac_sync_policy.json", entry)
    db.close()
    print("sync-policy(%s): %s" % ("dry-run" if dry_run else "apply", stats))
    if problems:
        sys.exit(2)


def main():
    p = argparse.ArgumentParser(description="报表授权_ 角色人员赋权管理工具")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")
    sub.add_parser("audit")

    for name in ("grant-user", "revoke-user"):
        sp = sub.add_parser(name)
        sp.add_argument("--username", required=True)
        sp.add_argument("--role", required=True)
        sp.add_argument("--dry-run", action="store_true")

    for name in ("grant-dept", "revoke-dept"):
        sp = sub.add_parser(name)
        sp.add_argument("--dept-code", required=True)
        sp.add_argument("--role", required=True)
        sp.add_argument("--dry-run", action="store_true")

    sp = sub.add_parser("sync-policy")
    sp.add_argument("--dry-run", action="store_true",
                    help="只预览不写库（默认行为，可显式给出）")
    sp.add_argument("--apply", action="store_true",
                    help="实际补齐 missing 赋权")

    args = p.parse_args()
    try:
        if args.cmd == "status":
            cmd_status(args)
        elif args.cmd == "audit":
            cmd_audit(args)
        elif args.cmd == "grant-user":
            cmd_user_change(args, add=True)
        elif args.cmd == "revoke-user":
            cmd_user_change(args, add=False)
        elif args.cmd == "grant-dept":
            cmd_dept_change(args, add=True)
        elif args.cmd == "revoke-dept":
            cmd_dept_change(args, add=False)
        elif args.cmd == "sync-policy":
            cmd_sync_policy(args)
    except SystemExit:
        raise
    except Exception as e:
        traceback.print_exc()
        die(2, "%s" % e)


if __name__ == "__main__":
    main()
