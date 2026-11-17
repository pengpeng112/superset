select table_name||'|'||column_name||'|'||is_nullable||'|'||coalesce(column_default,'(none)')
from information_schema.columns
where table_name in ('ab_role','dashboard_roles','ab_permission_view','ab_permission_view_role')
and column_name in ('id','permission_id','role_id','dashboard_id','view_menu_id','permission_view_id') order by table_name,ordinal_position;
select 'MAXIDS|'||(select max(id) from ab_role)||'|'||(select max(id) from dashboard_roles)||'|'||(select max(id) from ab_permission_view)||'|'||(select max(id) from ab_permission_view_role);
