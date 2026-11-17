\pset format unaligned
\pset fieldsep '	'
\pset tuples_only on
select d.id, d.dashboard_title, d.published,
       coalesce((select string_agg(r.name, ', ' order by r.name) from dashboard_roles dr join ab_role r on r.id=dr.role_id where dr.dashboard_id=d.id),'(未绑定)'),
       coalesce((select string_agg(s.id::text, ',' order by s.id) from dashboard_slices ds join slices s on s.id=ds.slice_id where ds.dashboard_id=d.id),'(无)'),
       coalesce((select string_agg(distinct s.datasource_id::text, ',') from dashboard_slices ds join slices s on s.id=ds.slice_id where ds.dashboard_id=d.id),'(无)')
from dashboards d where d.id in (1,2,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,72,73,74)
order by d.id;
