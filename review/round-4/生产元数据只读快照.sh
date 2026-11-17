docker exec -i superset-web /app/.venv/bin/python - <<'PY'
import json, os, re, hashlib, collections, pathlib, datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import sqlglot
from sqlglot import exp

conn = psycopg2.connect(host='postgres', dbname='superset', user='superset', password=os.environ['POSTGRES_PASSWORD'], connect_timeout=10)
conn.set_session(readonly=True)
cur = conn.cursor(cursor_factory=RealDictCursor)
def rows(sql):
    cur.execute(sql)
    return [dict(x) for x in cur.fetchall()]
def parse_json(value, default):
    try: return json.loads(value) if isinstance(value, str) else (value or default)
    except (ValueError, TypeError): return default

out = {'captured_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'scope':'仅 Superset 元数据和迁移过程文件；不执行 HIS/ODS 业务 SQL', 'sqlglot_version': sqlglot.__version__}
out['counts'] = {name: rows('SELECT COUNT(*) n FROM ' + name)[0]['n'] for name in ['tables','slices','dashboards','ab_user','ab_role','row_level_security_filters']}
out['user_status'] = rows('SELECT active,COUNT(*) n FROM ab_user GROUP BY active')
out['role_counts'] = rows("SELECT CASE WHEN name LIKE 'role_%' THEN 'department' ELSE 'other' END kind,COUNT(*) n FROM ab_role GROUP BY 1")
out['databases'] = rows('SELECT id,database_name,allow_dml,allow_ctas,allow_cvas,allow_file_upload,expose_in_sqllab,allow_run_async FROM dbs ORDER BY id')
out['rls_dataset_coverage'] = rows('SELECT t.id,t.table_name,COUNT(DISTINCT r.id) rule_count,COUNT(DISTINCT rr.role_id) role_count FROM tables t JOIN rls_filter_tables rt ON t.id=rt.table_id JOIN row_level_security_filters r ON r.id=rt.rls_filter_id LEFT JOIN rls_filter_roles rr ON r.id=rr.rls_filter_id GROUP BY t.id,t.table_name ORDER BY t.id')
out['rls_types'] = rows('SELECT filter_type,COUNT(*) n FROM row_level_security_filters GROUP BY filter_type')
out['permission_relation_tables'] = rows("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND (table_name LIKE '%role%' OR table_name LIKE '%column%') ORDER BY table_name")
out['chart_dataset_groups'] = rows("SELECT CASE WHEN t.table_name LIKE 'RPT_SRD_%' THEN 'SRD' WHEN t.table_name LIKE 'RPT_SRDR_%' THEN 'SRD_retry' WHEN t.table_name LIKE 'RPT_CORE_%' THEN 'core' ELSE 'other' END kind,COUNT(*) n FROM slices s LEFT JOIN tables t ON s.datasource_id=t.id GROUP BY 1 ORDER BY 1")

charts = rows('SELECT id,slice_name,datasource_id,table_id,params,query_context FROM slices ORDER BY id')
out['charts'] = []
for item in charts:
    p = parse_json(item.pop('params'), {})
    qc = parse_json(item.pop('query_context'), {})
    item.update({k:p.get(k) for k in ['row_limit','query_mode','granularity_sqla','time_range','server_pagination','server_page_length','order_by_cols']})
    item['all_columns_count'] = len(p.get('all_columns') or [])
    item['adhoc_filters_count'] = len(p.get('adhoc_filters') or [])
    item['has_query_context'] = bool(qc)
    out['charts'].append(item)

out['dashboards'] = []
for d in rows('SELECT id,dashboard_title,published,position_json,json_metadata FROM dashboards ORDER BY id'):
    pos = parse_json(d.pop('position_json'), {})
    meta = parse_json(d.pop('json_metadata'), {})
    visual_charts = [v.get('meta',{}).get('chartId') for v in pos.values() if isinstance(v,dict) and v.get('type')=='CHART']
    d['layout_chart_ids'] = visual_charts
    d['layout_node_types'] = dict(collections.Counter(v.get('type') for v in pos.values() if isinstance(v,dict)))
    d['native_filter_count'] = len(meta.get('native_filter_configuration') or [])
    d['native_filters'] = [{'name':x.get('name'),'filterType':x.get('filterType'),'targets':x.get('targets'),'scope':x.get('scope')} for x in meta.get('native_filter_configuration') or []]
    d['associated_chart_ids'] = [x['slice_id'] for x in rows('SELECT slice_id FROM dashboard_slices WHERE dashboard_id='+str(int(d['id']))+' ORDER BY slice_id')]
    d['roles'] = rows('SELECT r.id,r.name FROM dashboard_roles dr JOIN ab_role r ON r.id=dr.role_id WHERE dr.dashboard_id='+str(int(d['id']))+' ORDER BY r.id')
    out['dashboards'].append(d)

out['datasets'] = []
for d in rows('SELECT id,table_name,database_id,main_dttm_col,sql FROM tables ORDER BY id'):
    sql = d.pop('sql') or ''
    d['sql_sha256'] = hashlib.sha256(sql.encode()).hexdigest()
    d['sql_length'] = len(sql)
    d['has_jinja'] = '{{' in sql or '{%' in sql
    d['has_group_by'] = bool(re.search(r'\bGROUP\s+BY\b',sql,re.I))
    d['has_order_by'] = bool(re.search(r'\bORDER\s+BY\b',sql,re.I))
    d['has_union'] = bool(re.search(r'\bUNION\b',sql,re.I))
    d['null_comparison_regex'] = bool(re.search(r'(?:=|<>|!=|>=|<=|>|<)\s*NULL\b|\bBETWEEN\s+NULL\b|\bLIKE\s+NULL\b',sql,re.I))
    d['null_predicates'] = []
    try:
        tree = sqlglot.parse_one(sql, read='oracle') if sql else None
        if tree:
            for node in tree.walk():
                if isinstance(node,(exp.EQ,exp.NEQ,exp.GT,exp.GTE,exp.LT,exp.LTE,exp.Like,exp.Between)) and any(isinstance(n, exp.Null) for n in node.iter_expressions()):
                    d['null_predicates'].append(node.sql(dialect='oracle')[:240])
        d['ast_parsed'] = True
    except Exception:
        d['ast_parsed'] = False
    out['datasets'].append(d)

out['files'] = {}
for parent in ['/app/superset_home/scripts','/tmp']:
    for filename in ['srd_meta_all.json','deploy_srd_result.json','srd_retry_result.json','srd_fail_detail.json','deploy_core_result.json','deploy_v5_result.json']:
        p = pathlib.Path(parent) / filename
        if not p.is_file(): continue
        data = p.read_bytes()
        j = json.loads(data)
        rec = {'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
        if isinstance(j,list):
            rec['count'] = len(j)
            if filename=='srd_meta_all.json':
                rec['keys'] = list(j[0]) if j else []
                rec['pbselect_count'] = sum(bool(x.get('sql_is_pbselect')) for x in j)
                rec['parameterized_count'] = sum(bool(re.search(r'(?<![:\w]):[A-Za-z_][A-Za-z0-9_.]*',x.get('sql',''))) for x in j)
            if filename=='srd_fail_detail.json':
                rec['error_counts'] = dict(collections.Counter((re.search(r'ORA-\d+',x.get('err','')).group(0) if re.search(r'ORA-\d+',x.get('err','')) else 'other') for x in j))
                rec['identifiers'] = [{'pbd':x.get('pbd'),'dw':x.get('dw')} for x in j]
        elif isinstance(j,dict):
            rec['keys'] = list(j)
            rec['ok_count'] = len(j.get('ok',[]))
            rec['fail_count'] = len(j.get('fail',[]))
            rec['ok'] = j.get('ok',[])
            rec['fail_stage_counts'] = dict(collections.Counter(x.get('err','').split()[0] if x.get('err') else 'unknown' for x in j.get('fail',[])))
            rec['fails'] = [{'name':x.get('name'),'dw':x.get('dw'),'stage':x.get('err','').split()[0] if x.get('err') else None,'ora':(re.search(r'ORA-\d+',x.get('err','')).group(0) if re.search(r'ORA-\d+',x.get('err','')) else None)} for x in j.get('fail',[]) ]
        out['files'][str(p)] = rec

print(json.dumps(out, ensure_ascii=False, indent=2))
conn.rollback()
conn.close()
PY
