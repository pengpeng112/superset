#!/usr/bin/env bash
# 每日用户同步入口 v2（cron 06:00 调用）；凭据从 /home/superset/.env 注入，不落脚本
# 2026-10-15 T14：补时间戳/run_id/退出码——此前 [sync] 行无时间、日志无法证明某日 06:00 自然触发。
# 保持同步 python 逻辑、cron 时刻、熔断与 --dry-run 语义完全不变。
set -uo pipefail
cd /home/superset
LOG=/home/superset/logs/sync.log
RUN_ID="sync-$(date +%F-%H%M%S)"
ts() { date '+%F %T'; }
{
  echo "[$(ts)] $RUN_ID start mode=${*:-full}"
} >> "$LOG"
set -a; . ./.env; set +a
docker compose -p superset-prod exec -T \
  -e SYNC_ORA_DSN=10.10.8.216:1521/orcl \
  -e SYNC_ORA_USER=ods \
  -e SYNC_ORA_PWD="$SYNC_ORA_PWD" \
  -e SUP_BASE=http://superset-web:8088 \
  -e SUP_ADMIN=admin \
  -e SUP_ADMIN_PWD="$ADMIN_INIT_PASSWORD" \
  -e RLS_TABLE_ID=0 \
  superset-worker /app/.venv/bin/python /app/superset_home/scripts/superset_user_sync.py "$@" 2>&1 \
  | while IFS= read -r line; do echo "[$(ts)] $RUN_ID $line"; done >> "$LOG"
RC=${PIPESTATUS[0]}
echo "[$(ts)] $RUN_ID end exit=$RC" >> "$LOG"
exit $RC
