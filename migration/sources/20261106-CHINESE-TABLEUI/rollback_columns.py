# -*- coding: utf-8 -*-
"""20261106-CHINESE-TABLEUI 一键回退：把本批 59 列 verbose_name 恢复为写前值（columns_before.json）。
用法：python rollback_columns.py   （凭据经环境变量注入，经 remote_exec 在服务器执行）
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "tools")))


def main():
    before = json.load(open(os.path.join(HERE, "columns_before.json"), encoding="utf-8"))
    assert isinstance(before, list) and before, "columns_before.json 为空，拒绝回退"
    lines = []
    for r in before:
        old = (r["old_verbose_name"] or "").replace("$", "$$")
        lines.append(
            "UPDATE table_columns SET verbose_name = %s WHERE id = %d AND table_id = %d AND column_name = $hh$%s$hh$;"
            % (("$hh$%s$hh$" % old) if old else "NULL", r["column_id"], r["table_id"], r["column_name"])
        )
    sql = "\n".join(lines) + "\n"
    p = os.path.join(HERE, "rollback_columns.sql")
    open(p, "w", encoding="utf-8", newline="").write(sql)
    print("rollback SQL -> %s (%d rows)" % (p, len(lines)))
    print("在服务器执行：")
    print("  flock -x 9 /tmp/user_sync.lock bash -c 'cat rollback_columns.sql | docker exec -i superset-postgres psql -U superset -d superset -v ON_ERROR_STOP=1'")
    print("  docker exec superset-redis redis-cli -n 0 FLUSHDB; docker exec superset-redis redis-cli -n 1 FLUSHDB")


if __name__ == "__main__":
    main()
