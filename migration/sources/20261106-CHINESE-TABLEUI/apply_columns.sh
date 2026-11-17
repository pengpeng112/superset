#!/bin/bash
# 20261106-CHINESE-TABLEUI 持锁受控写入：备份→校验→UPDATE→Redis db0/db1 清缓存。
set -e
q(){ docker exec superset-postgres psql -U superset -d superset -At -c "$1"; }
(
flock -x 9
echo "LOCKED $(date -Is)"
IDS=1765,2304,2305,2306,2612,2613,1785,2614,2422,2615,2616,2617,2618,2619,2263,2264,2265,2266,2267,2057,2058,2059,2637,2062,2282,2622,2096,2097,2098,2101,2102,2623,2625,2626,2627,2105,2106,2107,2112,2628,2630,2631,2632,2633,2190,2634,2635,2636,2398,2509,2510,2511,2512,2544,2545,2571,2572,2591,2712
# 1) 写前备份当前 verbose_name
q "select json_agg(row_to_json(x)) from (select id as column_id, table_id, column_name, coalesce(verbose_name,'') as old_verbose_name from table_columns where id in ($IDS) order by id) x" > /home/superset/migration-private/20261106-CHINESE-TABLEUI/columns_before.json
echo "BACKUP:"; cat /home/superset/migration-private/20261106-CHINESE-TABLEUI/columns_before.json

# 2) 校验：备份行数必须=59，且全部 verbose_name 与预期 old（空或=column_name）一致
N=$(q "select count(*) from table_columns where id in ($IDS)")
if [ "$N" != "59" ]; then echo "ABORT: expected 59 rows, got $N"; exit 1; fi
BAD=$(q "select count(*) from table_columns where id in ($IDS) and coalesce(verbose_name,'')<>'' and verbose_name<>column_name")
if [ "$BAD" != "0" ]; then echo "ABORT: $BAD rows already have non-trivial verbose_name"; exit 1; fi

# 3) 写入（UPDATE 各行，逐条 dollar-quote）
cat /home/superset/migration-private/20261106-CHINESE-TABLEUI/update_columns.sql | docker exec -i superset-postgres psql -U superset -d superset -v ON_ERROR_STOP=1

# 4) 校验写入结果
q "select count(*) from table_columns where id in ($IDS) and verbose_name is null or verbose_name=''" || true
q "select count(*) from (select id from table_columns where id in ($IDS) and coalesce(verbose_name,'')='') z"
echo "REMAIN_EMPTY_ABOVE(expect 0)"
) 9>/tmp/user_sync.lock
# 5) Redis 缓存清理：仅 db0(CACHE) 与 db1(DATA_CACHE)；严禁 db3/db4
docker exec superset-redis redis-cli -n 0 DBSIZE
docker exec superset-redis redis-cli -n 1 DBSIZE
docker exec superset-redis redis-cli -n 0 FLUSHDB
docker exec superset-redis redis-cli -n 1 FLUSHDB
docker exec superset-redis redis-cli -n 0 DBSIZE
docker exec superset-redis redis-cli -n 1 DBSIZE
echo "REDIS-DB2-UNTouched: $(docker exec superset-redis redis-cli -n 2 DBSIZE) db3:$(docker exec superset-redis redis-cli -n 3 DBSIZE) db4:$(docker exec superset-redis redis-cli -n 4 DBSIZE)"
echo APPLY-DONE
