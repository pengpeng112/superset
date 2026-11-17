\pset format unaligned
\pset tuples_only on
select 'D39_JSON_METADATA||'||json_metadata from dashboards where id=39;
select 'D39_PARAMS||'||left(params,600) from dashboards where id=39;
select 'CH283_PARAMS||'||left(params,900) from slices where id=283;
select 'DS281_SQL||'||sql from tables where id=281;
