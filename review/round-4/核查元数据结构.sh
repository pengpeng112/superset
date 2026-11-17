docker exec -i superset-web /app/.venv/bin/python - <<'PY'
import json, os, psycopg2
conn = psycopg2.connect(host='postgres', dbname='superset', user='superset', password=os.environ['POSTGRES_PASSWORD'], connect_timeout=10)
conn.set_session(readonly=True)
cur = conn.cursor()
cur.execute("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema='public' AND (table_name IN ('tables','slices','dashboards','dbs','ab_user','ab_role','row_level_security_filters') OR table_name LIKE '%rls%' OR table_name LIKE '%row_level%' OR table_name LIKE '%dashboard%' OR table_name LIKE '%table_role%') ORDER BY table_name,ordinal_position")
out = {}
for table, col in cur.fetchall(): out.setdefault(table, []).append(col)
print(json.dumps(out, ensure_ascii=False, indent=2))
conn.rollback()
conn.close()
PY
