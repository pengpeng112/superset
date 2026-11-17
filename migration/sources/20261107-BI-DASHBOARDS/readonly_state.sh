#!/bin/bash
# 20261107-BI-DASHBOARDS 交接用只读现状采集：只 SELECT，不写任何业务/元数据。
q(){ docker exec superset-postgres psql -U superset -d superset -At -c "$1"; }
echo "TS $(date -Is)"
echo "== COUNTS"
q "select 'charts='||(select count(*) from slices)||' datasets='||(select count(*) from tables)||' dashboards='||(select count(*) from dashboards)||' published='||(select count(*) from dashboards where published)||' dash_slices='||(select count(*) from dashboard_slices)||' dash_roles='||(select count(*) from dashboard_roles)"
echo "== MAXIDS"
q "select 'slices='||(select max(id) from slices)||' tables='||(select max(id) from tables)||' dashboards='||(select max(id) from dashboards)||' table_columns='||(select max(id) from table_columns)||' sql_metrics='||(select max(id) from sql_metrics)||' ab_view_menu='||(select max(id) from ab_view_menu)||' ab_permission_view='||(select max(id) from ab_permission_view)||' ab_permission_view_role='||(select max(id) from ab_permission_view_role)"
echo "== BI_DASHBOARDS"
q "select id||'|'||coalesce(slug,'')||'|published='||published||'|'||dashboard_title from dashboards where id>70 order by id"
echo "== BI_DASHBOARD_ROLES"
q "select dashboard_id||'|role='||role_id from dashboard_roles where dashboard_id>70 order by 1"
echo "== BI_DASHBOARD_SLICES"
q "select dashboard_id||'|'||string_agg(slice_id::text,',' order by slice_id) from dashboard_slices where dashboard_id>70 group by dashboard_id order by 1"
echo "== BI_CHARTS"
q "select id||'|col_viz='||viz_type||'|params_viz='||coalesce(params::json->>'viz_type','?')||'|ds='||datasource_id||'|cache='||coalesce(cache_timeout::text,'-')||'|'||slice_name from slices where id>354 order by id"
echo "== NEW_DATASETS"
q "select id||'|'||table_name from tables where id>372 order by id"
echo "== FILTERS"
q "select id||'|'||coalesce(json_metadata::jsonb->'native_filter_configuration'->0->>'id','NONE')||'|default='||coalesce(json_metadata::jsonb->'native_filter_configuration'->0->'defaultDataMask'->'filterState'->>'value','(none)') from dashboards where id>70 order by id"
echo "== MAIN_DTTM"
q "select id||'|'||coalesce(main_dttm_col,'-')||'|'||table_name from tables where id in (322,323,324,325,326,338,345,347,348,350,365) order by id"
echo "== USER_003158_ROLES"
q "select r.id||'|'||r.name from ab_user u join ab_user_role ur on ur.user_id=u.id join ab_role r on r.id=ur.role_id where u.username='003158' order by 1"
echo "== GAMMA_MEMBERS"
q "select count(*) from ab_user_role where role_id=4"
echo "== CHART3_PARAMS"
q "select params from slices where id=3"
echo "== PIVOT_EXISTING"
q "select s.id||'|'||s.slice_name||'|dash='||coalesce(string_agg(ds.dashboard_id::text,','),'-') from slices s left join dashboard_slices ds on ds.slice_id=s.id where s.viz_type='pivot_table_v2' group by s.id,s.slice_name"
mkdir -p /tmp/bi_sql && rm -f /tmp/bi_sql/*.sql
for i in 322 323 324 325 326 338 345 347 348 350; do q "select sql from tables where id=$i" > /tmp/bi_sql/ds$i.sql; done
tar czf /tmp/bi_sql.tgz -C /tmp bi_sql
ls -la /tmp/bi_sql | tail -n +2
echo "DONE"
