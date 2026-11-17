#!/bin/bash
# 20261104-NAV-SEARCH 元数据快照：8 组保护哈希 + 计数。
# 只输出哈希与计数，行内容不出服务器。写前/写后各跑一次做零变化对比。
set -e
q(){ docker exec superset-postgres psql -U superset -d superset -At -c "$1"; }
echo "TS $(date -Is)"
echo "COUNTS charts=$(q 'select count(*) from slices') datasets=$(q 'select count(*) from tables') dashboards=$(q 'select count(*) from dashboards') users=$(q 'select count(*) from ab_user') published=$(q 'select count(*) from dashboards where published') roles=$(q 'select count(*) from ab_role') rls=$(q 'select count(*) from row_level_security_filters') favstar=$(q 'select count(*) from favstar') dash_slices=$(q 'select count(*) from dashboard_slices') perm_view_role=$(q 'select count(*) from ab_permission_view_role')"
g(){
  name="$1"; sql="$2"
  body="$(q "$sql")"
  h="$(printf '%s\n' "$body" | sha256sum | cut -d' ' -f1)"
  n="$(printf '%s\n' "$body" | grep -c . || true)"
  echo "HASH $name rows=$n sha256=$h"
}
g G1_dashboards "select concat_ws('|',id,coalesce(slug,''),coalesce(dashboard_title,''),coalesce(published::text,''),coalesce(position_json,''),coalesce(json_metadata,'')) from dashboards order by id"
g G1_dashboard_slices "select concat_ws('|',id,dashboard_id,slice_id) from dashboard_slices order by dashboard_id,slice_id,id"
g G1_dashboard_roles "select concat_ws('|',id,dashboard_id,role_id) from dashboard_roles order by dashboard_id,role_id,id"
g G2_datasets "select concat_ws('|',id,coalesce(table_name,''),database_id,coalesce(schema,''),coalesce(sql,''),coalesce(main_dttm_col,'')) from tables order by id"
g G2_columns "select concat_ws('|',id,table_id,coalesce(column_name,''),coalesce(expression,''),is_dttm,coalesce(filterable::text,''),coalesce(groupby::text,'')) from table_columns order by table_id,id"
g G2_metrics "select concat_ws('|',id,table_id,coalesce(metric_name,''),coalesce(expression,''),coalesce(d3format,'')) from sql_metrics order by table_id,id"
g G3_charts "select concat_ws('|',id,coalesce(slice_name,''),coalesce(viz_type,''),coalesce(datasource_id::text,''),coalesce(datasource_type,''),coalesce(params,'')) from slices order by id"
# 用户组不含 last_login/login_count 等登录计数（浏览器验收本身会登录，不算元数据变化）
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
echo "ASSETS"
sha256sum /home/superset/custom/home-ui.js /home/superset/custom/report-ui.js /home/superset/custom/report-dates.js /home/superset/nginx.conf 2>/dev/null
stat -c 'INODE %i %n' /home/superset/nginx.conf
echo "DONE"
