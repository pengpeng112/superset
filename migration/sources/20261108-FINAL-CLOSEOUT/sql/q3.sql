
\echo ===TABLES_LIKE_DATA===
select tablename from pg_tables where schemaname='public' and (tablename like '%dataset%' or tablename like '%slice%' or tablename like '%dashboard%') order by 1;
\echo ===ROLE_PERMS===
select r.id||'|'||p.name||' on '||v.name
from ab_role r
join ab_permission_view_role pvr on pvr.role_id=r.id
join ab_permission_view pv on pv.id=pvr.permission_view_id
join ab_permission p on p.id=pv.permission_id
join ab_view_menu v on v.id=pv.view_menu_id
where r.id in (341,343) order by r.id,p.name,v.name;
