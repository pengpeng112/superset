#!/usr/bin/env bash
# 每日缓存预热入口（cron 06:15 调用，20261112-WARMUP-PERF 批）。
# 凭据从 /home/superset/.env 的 ADMIN_INIT_PASSWORD 注入（同 run_sync.sh 模式），不落脚本。
# 文件锁 /tmp/superset_warmup.lock 防重入；预热在 superset-worker 容器内执行，
# 只向 superset-web:8088 串行发请求（间隔 2s、超时 90s、连续 3 失败熔断）。
# 退出码：0 全部成功；1 部分失败；2 熔断；3 登录/模板错误；4 已有实例在跑。
set -uo pipefail
LOCK=/tmp/superset_warmup.lock
exec 9>"$LOCK"
if ! flock -n 9; then
  echo "[$(date '+%F %T')] warmup-$(date +%F-%H%M%S) skip: another instance holds $LOCK"
  exit 4
fi
cd /home/superset
RUN_ID="warmup-$(date +%F-%H%M%S)"
ts() { date '+%F %T'; }
echo "[$(ts)] $RUN_ID start args=${*:-}"
set -a; . ./.env; set +a
docker compose -p superset-prod exec -T \
  -e SUP_BASE=http://superset-web:8088 \
  -e SUP_WARMUP_USER=admin \
  -e SUP_WARMUP_PWD="$ADMIN_INIT_PASSWORD" \
  superset-worker /app/.venv/bin/python /app/superset_home/scripts/superset_cache_warmup.py "$@" 2>&1 \
  | while IFS= read -r line; do echo "[$(ts)] $RUN_ID $line"; done
RC=${PIPESTATUS[0]}
echo "[$(ts)] $RUN_ID end exit=$RC"
exit $RC
