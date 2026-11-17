\echo ===ROLE_MEMBERS_DETAIL===
select r.id||'|'||r.name||'|'||coalesce(string_agg(u.username||'('||coalesce(u.first_name,'')||')',', '),'(空)')
from ab_role r
left join ab_user_role ur on ur.role_id=r.id
left join ab_user u on u.id=ur.user_id
where r.id in (341,343,344,345) group by r.id,r.name order by r.id;
\echo ===DASH_TITLES===
select id||'|'||dashboard_title||'|published='||published from dashboards where id in (1,2,47,49,50,51,52,61,62,63,64,65,66,67,68,69,70) order by id;
\echo ===DS_NAMES===
select id||'|'||table_name from tables where id in (4,276,279,321,332,333) order by id;
\echo ===D2_SLICES===
select d.id||'|'||coalesce(string_agg(s.id||':'||s.slice_name,','),'(none)')
from dashboards d left join dashboard_slices ds on ds.dashboard_id=d.id left join slices s on s.id=ds.slice_id
where d.id=2 group by d.id;
