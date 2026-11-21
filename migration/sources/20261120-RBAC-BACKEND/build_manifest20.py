# -*- coding: utf-8 -*-
"""20261120-RBAC-BACKEND：生成 PRODUCTION-MANIFEST-20261120.json（offline-bundle ↔ 生产全量对齐）。

相对 20261119 版差异：+scripts/superset_rbac_manage.py、+scripts/rbac_policy.json，
superset_health_check.sh 升级第 9 项 RBAC 恒常（17→18 项全绿）。
"""
import hashlib
import json
import os
import re
import sys
import time

sys.path.insert(0, r"F:\python\superset\migration\tools")
import remote_exec  # noqa: E402
from remote_exec import run  # noqa: E402

BUNDLE = r"F:\python\superset\offline-bundle"

MAP = [
    (r"compose\docker-compose.yml", "/home/superset/docker-compose.yml"),
    (r"config\superset_config.py", "/home/superset/superset_config.py"),
    (r"nginx.conf", "/home/superset/nginx.conf"),
    (r"custom\brand.js", "/home/superset/custom/brand.js"),
    (r"custom\monthly-report.js", "/home/superset/custom/monthly-report.js"),
    (r"custom\report-dates.js", "/home/superset/custom/report-dates.js"),
    (r"custom\report-ui.js", "/home/superset/custom/report-ui.js"),
    (r"custom\home-ui.js", "/home/superset/custom/home-ui.js"),
    (r"custom\report-guards.js", "/home/superset/custom/report-guards.js"),
    (r"custom\date-range-zh.js", "/home/superset/custom/date-range-zh.js"),
    (r"custom\roles-zh.js", "/home/superset/custom/roles-zh.js"),
    (r"custom\app-recovery.js", "/home/superset/custom/app-recovery.js"),
    (r"custom\browser-compat.js", "/home/superset/custom/browser-compat.js"),
    (r"custom\browser-polyfills.js", "/home/superset/custom/browser-polyfills.js"),
    (r"custom\messages.json", "/home/superset/custom/messages.json"),
    (r"custom\logo.png", "/home/superset/custom/logo.png"),
    (r"custom\logo-bar.png", "/home/superset/custom/logo-bar.png"),
    (r"custom\logo-bar-light.png", "/home/superset/custom/logo-bar-light.png"),
    (r"custom\vendor\flatpickr-4.6.13\flatpickr.min.js", "/home/superset/custom/vendor/flatpickr-4.6.13/flatpickr.min.js"),
    (r"custom\vendor\flatpickr-4.6.13\flatpickr.min.css", "/home/superset/custom/vendor/flatpickr-4.6.13/flatpickr.min.css"),
    (r"custom\vendor\flatpickr-4.6.13\monthSelect.js", "/home/superset/custom/vendor/flatpickr-4.6.13/monthSelect.js"),
    (r"custom\vendor\flatpickr-4.6.13\monthSelect.css", "/home/superset/custom/vendor/flatpickr-4.6.13/monthSelect.css"),
    (r"custom\vendor\flatpickr-4.6.13\zh.js", "/home/superset/custom/vendor/flatpickr-4.6.13/zh.js"),
    (r"custom\vendor\flatpickr-4.6.13\LICENSE.md", "/home/superset/custom/vendor/flatpickr-4.6.13/LICENSE.md"),
    (r"custom\vendor\flatpickr-4.6.13\来源与哈希.json", "/home/superset/custom/vendor/flatpickr-4.6.13/来源与哈希.json"),
    (r"scripts\superset_user_sync.py", "/home/superset/scripts/superset_user_sync.py"),
    (r"scripts\run_sync.sh", "/home/superset/scripts/run_sync.sh"),
    (r"scripts\pg_backup.sh", "/home/superset/scripts/pg_backup.sh"),
    (r"scripts\superset_cache_warmup.py", "/home/superset/superset_home/scripts/superset_cache_warmup.py"),
    (r"scripts\run_warmup.sh", "/home/superset/superset_home/scripts/run_warmup.sh"),
    (r"scripts\warmup_templates.json", "/home/superset/superset_home/scripts/warmup_templates.json"),
    (r"scripts\superset_health_check.sh", "/home/superset/superset_home/scripts/superset_health_check.sh"),
    (r"scripts\superset_rbac_manage.py", "/home/superset/superset_home/scripts/superset_rbac_manage.py"),
    (r"scripts\rbac_policy.json", "/home/superset/superset_home/scripts/rbac_policy.json"),
    (r"translations\messages.json", "/home/superset/translations_zh/messages.json"),
]

SECRET_PAT = re.compile(r"(P@ssw0rd|<REDACTED-ODS-PW>|hveTK|hveTK7|<REDACTED-DEFAULT-EMPLOYEE-PW>|SECRET_KEY\s*=\s*['\"][^'\"]{8,}|PASSWORD\s*=\s*['\"][^'\"]{4,})")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    dirty = []
    for root, dirs, files in os.walk(BUNDLE):
        for fn in files:
            if fn.endswith("$f"):
                dirty.append(os.path.relpath(os.path.join(root, fn), BUNDLE))
    assert not dirty, "发现 $f 脏文件: %r" % dirty
    secret_hits = []
    for rel, _ in MAP:
        p = os.path.join(BUNDLE, rel)
        ext = os.path.splitext(p)[1].lower()
        if ext in (".py", ".sh", ".js", ".json", ".yml", ".conf", ""):
            try:
                txt = open(p, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            for m in SECRET_PAT.finditer(txt):
                secret_hits.append("%s: %s" % (rel, m.group(0)[:40]))
    cfg = open(os.path.join(BUNDLE, r"config\superset_config.py"), encoding="utf-8").read()
    env_ok = ("os.environ" in cfg)

    jb, tgt = remote_exec.connect()
    try:
        cmd = "; ".join("sha256sum '%s' 2>/dev/null || echo MISSING '%s'" % (sp, sp) for _, sp in MAP)
        rc, out, err = run(tgt, cmd, timeout=120)
        server = {}
        for line in out.strip().splitlines():
            parts = line.split(None, 1)
            if len(parts) == 2:
                server[parts[1].strip()] = parts[0].strip()
        files = []
        mismatch = []
        for rel, sp in MAP:
            p = os.path.join(BUNDLE, rel)
            sha = sha256_file(p)
            ssha = server.get(sp, "ABSENT")
            ok = sha == ssha
            if not ok:
                mismatch.append(rel)
            files.append({
                "server_path": sp,
                "local_path": "offline-bundle/" + rel.replace("\\", "/"),
                "bytes": os.path.getsize(p),
                "sha256": sha,
                "server_sha256": ssha,
                "match": ok,
            })
        rc2, out2, err2 = run(tgt, "stat -c %i /home/superset/nginx.conf")
        inode = out2.strip()
        man = {
            "generated": time.strftime("%Y-%m-%d"),
            "batch": "20261120-RBAC-BACKEND",
            "purpose": "offline-bundle 离线灾备包与生产 /home/superset/ 全量对齐清单（RBAC 后端权限重构：11 角色矩阵 + Gamma 解绑 34 业务看板 + 17 科室 311 绑定 + 体检第 9 项 RBAC 恒常）",
            "server_host": "10.10.8.73 (/home/superset)",
            "alignment": "%d/%d 文件 SHA256 与生产一致" % (len([f for f in files if f["match"]]), len(files)),
            "nginx_inode": inode,
            "dirty_files": "无",
            "secret_scan": {"hits": secret_hits, "config_env_injection": env_ok,
                            "note": "superset_user_sync.py 的 <REDACTED-DEFAULT-EMPLOYEE-PW> 为 INIT_PASSWORD 环境变量默认值（H1 定案业务常量），非连接凭据；本批新增 rbac 工具均走环境变量注入（SUP_ADMIN_PWD / PGPASSWORD / SYNC_ORA_*）"},
            "excluded": [
                "chrome80-assets/（体积大，生产在用，灾备恢复时另行打包）",
                ".env / secrets/（含口令，严禁落盘文档）",
                "superset-bundle.tar（镜像介质 1.2GB）",
                "pgdata/ redis/ logs/ backup/（运行时数据）",
                "migration_20261120/（一次性迁移工具 apply/rollback/verify/audit，存 73:migration-private 与本地批目录，不入灾备包）",
            ],
            "files": files,
        }
        outp = os.path.join(BUNDLE, "PRODUCTION-MANIFEST-20261120.json")
        with open(outp, "w", encoding="utf-8") as f:
            json.dump(man, f, ensure_ascii=False, indent=1)
        print("alignment:", man["alignment"], "inode:", man["nginx_inode"])
        print("mismatch:", mismatch)
        print("secret hits:", len(secret_hits), secret_hits[:3])
        print("saved", outp)
    finally:
        tgt.close()
        jb.close()


if __name__ == "__main__":
    main()
