python3 - <<'PY'
import json,subprocess,pathlib,re,datetime,hashlib
names=['superset-postgres','superset-redis','superset-web','superset-worker','superset-beat','superset-nginx']
out={'captured_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'containers':[]}
for name in names:
    r=subprocess.run(['docker','inspect',name],capture_output=True,text=True,timeout=10)
    if r.returncode:
        out['containers'].append({'name':name,'inspect_rc':r.returncode});continue
    d=json.loads(r.stdout)[0]
    out['containers'].append({'name':name,'status':d['State']['Status'],'health':d['State'].get('Health',{}).get('Status'),'restart_policy':d['HostConfig']['RestartPolicy']['Name']})
r=subprocess.run(['systemctl','is-active','his-tunnel'],capture_output=True,text=True,timeout=10)
out['his_tunnel_status']=r.stdout.strip()
root=pathlib.Path('/home/superset/backup')
out['backup_files']=[{'name':p.name,'bytes':p.stat().st_size,'modified_at_utc':datetime.datetime.fromtimestamp(p.stat().st_mtime,datetime.timezone.utc).isoformat()} for p in sorted(root.glob('*')) if p.is_file()] if root.exists() else []
config=pathlib.Path('/home/superset/superset_config.py')
out['query_timeout_config_lines']=[]
if config.exists():
    for line in config.read_text().splitlines():
        if re.match(r'\s*(SQLLAB_TIMEOUT|SUPERSET_WEBSERVER_TIMEOUT|ROW_LIMIT|SQL_MAX_ROW|TABLE_VIZ_MAX_ROW_SERVER|DEFAULT_SQLLAB_LIMIT)\s*=',line): out['query_timeout_config_lines'].append(line.strip())
r=subprocess.run(['crontab','-l'],capture_output=True,text=True,timeout=10)
out['scheduled_jobs']=[]
for line in r.stdout.splitlines():
    if not line.strip() or line.lstrip().startswith('#'):continue
    if 'superset' in line:
        out['scheduled_jobs'].append({'schedule':' '.join(line.split()[:5]),'backup':'pg_backup' in line,'user_sync':'run_sync' in line})
out['migration_log_facts']=[]
for filename in ['deploy_srd_run.log','srd_retry.log']:
    p=pathlib.Path('/home/superset/scripts')/filename
    if p.exists():
        # 仅输出固定前缀的非机密完成状态，不输出异常回溯或查询内容。
        out['migration_log_facts'].extend([line for line in p.read_text(errors='replace').splitlines() if re.match(r'^(BATCH_DONE|DASHBOARD |SUMMARY |RETRY_DONE|APPEND )',line)])
print(json.dumps(out,ensure_ascii=False,indent=2))
PY
docker exec -i superset-web /app/.venv/bin/python - <<'PY'
from pathlib import Path
import json
p=Path('/app/superset/models/core.py')
text=p.read_text()
print(json.dumps({'oracle_11g_rownum_patch_present':'ROWNUM <= {int(limit)}' in text}))
PY
