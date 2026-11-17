python3 - <<'PY'
import ast,json,pathlib,re,hashlib
out={}
for name in ['deploy_reports_srd.py','srd_retry.py']:
    p=pathlib.Path('/home/superset/superset_home/scripts')/name
    if not p.exists():continue
    data=p.read_bytes()
    text=data.decode('utf-8')
    tree=ast.parse(text)
    output_paths=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='open' and n.args and isinstance(n.args[0],ast.Constant) and isinstance(n.args[0].value,str):
            if len(n.args)>1 and isinstance(n.args[1],ast.Constant) and 'w' in str(n.args[1].value):output_paths.append({'line':n.lineno,'path':n.args[0].value})
    out[name]={'sha256':hashlib.sha256(data).hexdigest(),'output_paths':output_paths}
for name in ['deploy_srd_run.log','srd_retry.log']:
    p=pathlib.Path('/home/superset/scripts')/name
    if p.exists():
        classes=[]
        for line in p.read_text(errors='replace').splitlines():
            m=re.match(r'^([A-Za-z_]+(?:Error|Exception)):',line)
            if m:classes.append(m.group(1))
        out[name]={'terminal_exception_classes':classes}
print(json.dumps(out,ensure_ascii=False,indent=2))
PY
docker exec -i superset-web /app/.venv/bin/python - <<'PY'
import pathlib,json,collections,re
out={}
for parent in ['/app/superset_home/scripts','/tmp']:
    for p in pathlib.Path(parent).glob('*srd*result*'):
        if not p.is_file():continue
        j=json.loads(p.read_text())
        out[str(p)]={'ok_count':len(j.get('ok',[])),'fail_count':len(j.get('fail',[])),'failure_stage_counts':dict(collections.Counter(x.get('err','').split()[0] for x in j.get('fail',[]) if x.get('err')))}
print(json.dumps(out,ensure_ascii=False,indent=2))
PY
