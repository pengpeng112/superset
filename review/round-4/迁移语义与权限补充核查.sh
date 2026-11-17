docker exec -i superset-web /app/.venv/bin/python - <<'PY'
import json,os,re,hashlib,pathlib,collections,datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import sqlglot
from sqlglot import exp
from importlib.metadata import version

conn=psycopg2.connect(host='postgres',dbname='superset',user='superset',password=os.environ['POSTGRES_PASSWORD'],connect_timeout=10)
conn.set_session(readonly=True)
cur=conn.cursor(cursor_factory=RealDictCursor)
def rows(sql):
    cur.execute(sql)
    return [dict(r) for r in cur.fetchall()]

T,F,U='TRUE','FALSE','UNKNOWN'
def and_value(a,b):
    if F in (a,b): return F
    if U in (a,b): return U
    return T
def or_value(a,b):
    if T in (a,b): return T
    if U in (a,b): return U
    return F
def possibilities(n):
    if isinstance(n,exp.Paren): return possibilities(n.this)
    if isinstance(n,exp.And): return {and_value(a,b) for a in possibilities(n.this) for b in possibilities(n.expression)}
    if isinstance(n,exp.Or): return {or_value(a,b) for a in possibilities(n.this) for b in possibilities(n.expression)}
    if isinstance(n,exp.Not): return {T if a==F else F if a==T else U for a in possibilities(n.this)}
    if isinstance(n,(exp.EQ,exp.NEQ,exp.GT,exp.GTE,exp.LT,exp.LTE,exp.Like)) and any(isinstance(c,exp.Null) for c in n.iter_expressions()): return {U}
    if isinstance(n,exp.Between) and any(isinstance(c,exp.Null) for c in n.iter_expressions()): return {F,U}
    if isinstance(n,exp.Is) and isinstance(n.this,exp.Null) and isinstance(n.expression,exp.Null): return {T}
    return {T,F,U}

metas=json.loads(pathlib.Path('/app/superset_home/scripts/srd_meta_all.json').read_text())
out={'captured_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'installed_superset_version':version('apache-superset')}
out['gamma_permissions']=rows("SELECT p.name permission,v.name resource FROM ab_permission_view_role pr JOIN ab_role r ON r.id=pr.role_id JOIN ab_permission_view pv ON pv.id=pr.permission_view_id JOIN ab_permission p ON p.id=pv.permission_id JOIN ab_view_menu v ON v.id=pv.view_menu_id WHERE r.name='Gamma' ORDER BY v.name,p.name")
out['datasource_access_permissions']=rows("SELECT r.name role_name,p.name permission,v.name resource FROM ab_permission_view_role pr JOIN ab_role r ON r.id=pr.role_id JOIN ab_permission_view pv ON pv.id=pr.permission_view_id JOIN ab_permission p ON p.id=pv.permission_id JOIN ab_view_menu v ON v.id=pv.view_menu_id WHERE p.name IN ('datasource_access','database_access','all_datasource_access','all_database_access','schema_access','catalog_access') AND r.name <> 'Admin' ORDER BY r.name,v.name")
out['column_metadata']=rows("SELECT c.table_id,c.column_name,c.type,c.is_dttm FROM table_columns c JOIN tables t ON t.id=c.table_id WHERE t.table_name LIKE 'RPT_SRD_%' OR t.table_name LIKE 'RPT_SRDR_%' ORDER BY c.table_id,c.id")
out['source_mapping']=[]
for d in rows("SELECT id,table_name,sql FROM tables WHERE table_name LIKE 'RPT_SRD_%' OR table_name LIKE 'RPT_SRDR_%' ORDER BY id"):
    sql=d.pop('sql')
    i=int(re.search(r'_(\d+)$',d['table_name']).group(1))
    m=metas[i-1]
    raw=m['sql'].strip().rstrip(';')
    nulled=re.sub(r'(?<![:\w]):[A-Za-z_][A-Za-z0-9_.]*','NULL',raw)
    tree=sqlglot.parse_one(sql,read='oracle')
    outer=tree.args.get('from') or tree.args.get('from_')
    inner=outer.this.this if outer and isinstance(outer.this,exp.Subquery) else tree
    parsed_original=None
    try: parsed_original=sqlglot.parse_one(nulled,read='oracle')
    except Exception: pass
    d.update({'source_index':i,'pbd':m.get('pbd'),'dw':m['dw'],'source_title':m.get('title'),'source_has_bind':bool(re.search(r'(?<![:\w]):[A-Za-z_][A-Za-z0-9_.]*',raw)),'source_bind_names':sorted(set(re.findall(r'(?<![:\w]):([A-Za-z_][A-Za-z0-9_.]*)',raw))),'source_ast_equal_after_null':bool(parsed_original and inner==parsed_original),'source_ast_parsed':parsed_original is not None})
    rejected=[]
    selects=list(inner.find_all(exp.Select))
    for idx,s in enumerate(selects):
        w=s.args.get('where')
        if w and T not in possibilities(w.this):
            rejected.append({'select_index':idx,'has_group_by':s.args.get('group') is not None,'has_aggregate':any(isinstance(n,exp.AggFunc) for e in s.expressions for n in e.walk())})
    d['provably_rejected_query_blocks']=rejected
    d['select_count']=len(selects)
    top_where=inner.args.get('where') if isinstance(inner,exp.Select) else None
    d['top_where_provably_rejects']=bool(top_where and T not in possibilities(top_where.this))
    d['source_has_compute_in_raw_srd']=None
    out['source_mapping'].append(d)

out['migration_result_files']=[]
for parent in ['/app/superset_home/scripts','/tmp']:
    for p in pathlib.Path(parent).glob('*srd*'):
        if p.is_file(): out['migration_result_files'].append({'path':str(p),'bytes':p.stat().st_size})

from flask import Flask
# 仅文本读取配置，避免初始化应用；只记录非机密配置行。
config=pathlib.Path('/app/pythonpath/superset_config.py')
out['query_timeout_config_lines']=[]
if config.exists():
    for line in config.read_text().splitlines():
        if re.match(r'\s*(SQLLAB_TIMEOUT|SUPERSET_WEBSERVER_TIMEOUT|GLOBAL_ASYNC_QUERIES|ROW_LIMIT|SQL_MAX_ROW|TABLE_VIZ_MAX_ROW_SERVER|DEFAULT_SQLLAB_LIMIT)\s*=',line): out['query_timeout_config_lines'].append(line.strip())
print(json.dumps(out,ensure_ascii=False,indent=2))
conn.rollback()
conn.close()
PY
find /home/superset -maxdepth 3 -type f -name '*srd*' -printf '\nFILE %p %s bytes\n'
