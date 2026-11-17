
\echo ===ROLE_PERMS_341_343===
select r.id||'|'||p.permission_name||' on '||v.view_name
from ab_role r
join ab_permission_view_role pvr on pvr.role_id=r.id
join ab_permission_view pv on pv.id=pvr.permission_view_id
join ab_permission p on p.id=pv.permission_id
join ab_view_menu v on v.id=pv.view_menu_id
where r.id in (341,343) order by r.id,p.permission_name,v.view_name;
\echo ===DASH_ROLE_BINDINGS===
select dr.id||'|'||coalesce(string_agg(d.id::text,', '),'(none)')
from ab_role r join dashboard_roles dr on dr.role_id=r.id
join dashboards d on d.id=dr.dashboard_id
where r.id in (341,343) group by dr.id,r.id order by dr.id;
\echo ===TARGET_DASHBOARDS===
select id||'|'||dashboard_title||'|published='||published||'|roles='||coalesce((select string_agg(role_id::text,',') from dashboard_roles where dashboard_id=d.id),'none')
from dashboards d where id in (1,2,32,34,47,49,50,51,52,72,73,74) order by id;
\echo ===D47_49_50_51_52_SLICES===
select d.id||'|'||coalesce(string_agg(s.id::text,','),'(none)')
from dashboards d left join dashboard_slices ds on ds.dashboard_id=d.id left join slices s on s.id=ds.slice_id
where d.id in (47,49,50,51,52) group by d.id order by d.id;
\echo ===SLICE_DATASETS===
select s.id||'|'||s.slice_name||'|ds='||s.datasource_id||'|'||s.datasource_type
from slices s where s.id in (select slice_id from dashboard_slices where dashboard_id in (47,49,50,51,52)) order by s.id;
\echo ===ROLE_MEMBERS===
select r.id||'|'||r.name||'|members='||count(ab_user.id)
from ab_role r left join ab_user_role ur on ur.role_id=r.id left join ab_user on ab_user.id=ur.user_id
where r.id in (341,343) group by r.id,r.name;
\echo ===DATASET_NAMES===
select id||'|'||table_name from datasets where id in (select datasource_id from slices where id in (select slice_id from dashboard_slices where dashboard_id in (47,49,50,51,52)));
