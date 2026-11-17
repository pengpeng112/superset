#!/usr/bin/env bash
# Superset 元数据库每日备份 v2（2026-10-15 T14：generation 化）
# 变更（相对 C4 版）：
#   1) 每次运行独立 generation 目录（含秒级时间戳，同日重跑不覆盖上一份）；
#   2) dump/secrets/manifest 全部在 .staging 暂存并校验通过后，才整体发布为完整 generation；
#      任一步失败保留上一完整 generation，staging 留 FAIL 标记目录；
#   3) secrets 与 dump 同 generation 发布（此前 secrets 先替换，失败会破坏上一组合）；
#   4) 写 DONE 完成标记与 latest 指针；14 天清理按 generation 目录整体进行；
#   5) 兼容：保留顶层旧布局文件不动；月检手册以 generation 目录为准（T16 已登记）。
set -euo pipefail
BASE=${BASE_DIR:-/home/superset}
BACKUP_DIR=$BASE/backup
LOG=$BASE/logs/backup.log
KEEP_DAYS=14
STAMP=$(date +%F)
RUN=$(date +%F-%H%M%S)
GENS="$BACKUP_DIR/gens"
GEN="$GENS/$RUN"
STG="$GENS/.staging-$RUN"

log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

mkdir -p "$GENS" "$STG" "$BASE/logs"
fail() { trap - EXIT; log "FAIL $RUN $*"; echo "FAIL: $*" > "$STG/FAILED" 2>/dev/null || true; mv "$STG" "$GEN-FAILED" 2>/dev/null || true; exit 1; }
trap 'fail interrupted' EXIT

log "START $RUN generation backup"

# 1) dump → staging
if ! docker compose -f $BASE/docker-compose.yml -p superset-prod exec -T postgres \
    pg_dump -U superset -Fc superset > "$STG/superset-$STAMP.dump"; then
  fail pg_dump
fi

# 2) dump 完整性：pg_restore --list 可列出且非空
SIZE=$(stat -c%s "$STG/superset-$STAMP.dump" 2>/dev/null || echo 0)
if [ "$SIZE" -lt 1024 ] || ! docker exec -i superset-postgres pg_restore -U superset --list < "$STG/superset-$STAMP.dump" >/dev/null 2>&1; then
  fail "verify size=${SIZE}"
fi

# 3) secrets → staging
if ! cp -a $BASE/secrets "$STG/secrets"; then
  fail secrets_copy
fi

# 4) manifest（live 计数标注采集时刻；dump 内部计数以恢复演练为准）
SHA=$(sha256sum "$STG/superset-$STAMP.dump" | cut -d' ' -f1)
PW=$(grep -oP '(?<=^POSTGRES_PASSWORD=).*' $BASE/.env 2>/dev/null | tr -d '"' || true)
DBOBJS=$(docker exec -e POSTGRES_PASSWORD="$PW" superset-postgres psql -U superset -tAc \
  "SELECT (SELECT count(*) FROM slices)||'/'||(SELECT count(*) FROM dashboards)" 2>/dev/null || echo '?')
cat > "$STG/manifest.txt" <<EOF
run=$RUN
date=${STAMP}
dump=superset-${STAMP}.dump
sha256=${SHA}
bytes=${SIZE}
live_objects(slices/dashboards)_at_dump=${DBOBJS}
created_by=pg_backup.sh(v2-generation)
EOF

# 5) 发布完整 generation（原子 mv）+ DONE + latest 指针
echo "DONE $RUN" > "$STG/DONE"
mv "$STG" "$GEN"
trap - EXIT
ln -sfn "$GEN" "$GENS/latest"
log "OK $RUN bytes=${SIZE} sha256=${SHA:0:12} objs=${DBOBJS} gen=$GEN"

# 6) 清理：14 天前的完整 generation；1 天前的 FAILED/staging 残留
find "$GENS" -maxdepth 1 -type d -name '20*' -mtime +${KEEP_DAYS} -exec rm -rf {} +
find "$GENS" -maxdepth 1 -type d \( -name '*-FAILED' -o -name '.staging-*' \) -mtime +1 -exec rm -rf {} +
