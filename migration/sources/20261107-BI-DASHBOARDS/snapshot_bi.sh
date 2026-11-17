#!/bin/bash
# 20261107-BI-DASHBOARDS 只读快照：8 组全量哈希 + “仅原有对象”过滤哈希 + 本批新增对象清单。
# 原理：写前快照（snapshot-before.raw，2026-11-08 10:18）时库内只有原有对象
#      （slices≤354、tables≤372、dashboards≤70），所以写前的全量哈希 = 原有对象哈希。
#      现在按同样的列表达式、加 id 范围过滤重算，与写前全量哈希逐组相等，即证明原有对象零修改。
# 只 SELECT，行内容不出服务器。
set -e
q(){ docker exec superset-postgres psql -U superset -d superset -At -c "$1"; }
g(){
  name="$1"; sql="$2"
  body="$(q "$sql")"
  h="$(printf '%s\n' "$body" | sha256sum | cut -d' ' -f1)"
  n="$(printf '%s\n' "$body" | grep -c . || true)"
  echo "HASH $name rows=$n sha256=$h"
}
DASH="concat_ws('|',id,coalesce(slug,''),coalesce(dashboard_title,''),coalesce(published::text,''),coalesce(position_json,''),coalesce(json_metadata,''))"
DS="concat_ws('|',id,coalesce(table_name,''),database_id,coalesce(schema,''),coalesce(sql,''),coalesce(main_dttm_col,''))"
COL="concat_ws('|',id,table_id,coalesce(column_name,''),coalesce(expression,''),is_dttm,coalesce(filterable::text,''),coalesce(groupby::text,''))"
MET="concat_ws('|',id,table_id,coalesce(metric_name,''),coalesce(expression,''),coalesce(d3format,''))"
CH="concat_ws('|',id,coalesce(slice_name,''),coalesce(viz_type,''),coalesce(datasource_id::text,''),coalesce(datasource_type,''),coalesce(params,''))"
echo "TS $(date -Is)"
echo "COUNTS charts=$(q 'select count(*) from slices') datasets=$(q 'select count(*) from tables') dashboards=$(q 'select count(*) from dashboards') users=$(q 'select count(*) from ab_user') published=$(q 'select count(*) from dashboards where published') roles=$(q 'select count(*) from ab_role') rls=$(q 'select count(*) from row_level_security_filters') favstar=$(q 'select count(*) from favstar') dash_slices=$(q 'select count(*) from dashboard_slices') perm_view_role=$(q 'select count(*) from ab_permission_view_role')"
echo "## 全量组（与写前比：G1/G3 允许因新增对象变化，其余应相同；若新建了数据集，G2 与 G6_view_menu/G6_perm_view 也会变化）"
g G1_dashboards "select $DASH from dashboards order by id"
g G1_dashboard_slices "select concat_ws('|',id,dashboard_id,slice_id) from dashboard_slices order by dashboard_id,slice_id,id"
g G1_dashboard_roles "select concat_ws('|',id,dashboard_id,role_id) from dashboard_roles order by dashboard_id,role_id,id"
g G2_datasets "select $DS from tables order by id"
g G2_columns "select $COL from table_columns order by table_id,id"
g G2_metrics "select $MET from sql_metrics order by table_id,id"
g G3_charts "select $CH from slices order by id"
g G4_users "select concat_ws('|',id,coalesce(username,''),coalesce(active::text,''),coalesce(first_name,''),coalesce(last_name,''),coalesce(email,'')) from ab_user order by id"
g G5_roles "select concat_ws('|',id,coalesce(name,'')) from ab_role order by id"
g G5_user_role "select concat_ws('|',id,user_id,role_id) from ab_user_role order by user_id,role_id,id"
g G6_permissions "select concat_ws('|',id,coalesce(name,'')) from ab_permission order by id"
g G6_view_menu "select concat_ws('|',id,coalesce(name,'')) from ab_view_menu order by id"
g G6_perm_view "select concat_ws('|',id,permission_id,view_menu_id) from ab_permission_view order by id"
g G6_perm_view_role "select concat_ws('|',id,permission_view_id,role_id) from ab_permission_view_role order by id"
g G7_rls_filters "select concat_ws('|',id,coalesce(name,''),coalesce(description,''),filter_type,coalesce(group_key,''),coalesce(clause,'')) from row_level_security_filters order by id"
g G7_rls_tables "select concat_ws('|',id,rls_filter_id,table_id) from rls_filter_tables order by rls_filter_id,table_id,id"
g G7_rls_roles "select concat_ws('|',id,rls_filter_id,role_id) from rls_filter_roles order by rls_filter_id,role_id,id"
g G8_favstar "select concat_ws('|',id,user_id,obj_id,coalesce(class_name,'')) from favstar order by user_id,obj_id,id"
echo "## 仅原有对象组（必须逐组等于写前快照的同名全量组）"
g EXIST_G1_dashboards "select $DASH from dashboards where id<=70 order by id"
g EXIST_G1_dashboard_slices "select concat_ws('|',id,dashboard_id,slice_id) from dashboard_slices where dashboard_id<=70 order by dashboard_id,slice_id,id"
g EXIST_G1_dashboard_roles "select concat_ws('|',id,dashboard_id,role_id) from dashboard_roles where dashboard_id<=70 order by dashboard_id,role_id,id"
g EXIST_G2_datasets "select $DS from tables where id<=372 order by id"
g EXIST_G2_columns "select $COL from table_columns where table_id<=372 order by table_id,id"
g EXIST_G2_metrics "select $MET from sql_metrics where table_id<=372 order by table_id,id"
g EXIST_G3_charts "select $CH from slices where id<=354 order by id"
g EXIST_G6_view_menu "select concat_ws('|',id,coalesce(name,'')) from ab_view_menu where id<=708 order by id"
g EXIST_G6_perm_view "select concat_ws('|',id,permission_id,view_menu_id) from ab_permission_view where id<=845 order by id"
echo "## 本批新增对象清单"
q "select 'NEW_DASHBOARD|'||id||'|published='||published||'|'||dashboard_title from dashboards where id>70 order by id"
q "select 'NEW_DASH_ROLE|'||dashboard_id||'|role='||role_id from dashboard_roles where dashboard_id>70 order by 1"
q "select 'NEW_CHART|'||id||'|'||viz_type||'|params_viz='||coalesce(params::json->>'viz_type','?')||'|ds='||datasource_id||'|'||slice_name from slices where id>354 order by id"
q "select 'NEW_DATASET|'||id||'|'||table_name from tables where id>372 order by id"
q "select 'NEW_VIEW_MENU|'||id||'|'||name from ab_view_menu where id>708 order by id"
echo "ASSETS"
sha256sum /home/superset/custom/home-ui.js /home/superset/custom/report-ui.js /home/superset/custom/report-guards.js /home/superset/custom/report-dates.js /home/superset/nginx.conf 2>/dev/null
stat -c 'INODE %i %n' /home/superset/nginx.conf
echo "DONE"
