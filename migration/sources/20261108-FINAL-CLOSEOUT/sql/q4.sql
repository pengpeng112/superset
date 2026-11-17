\echo ===ALL_TABLES===
select tablename from pg_tables where schemaname='public' order by 1;
\echo ===DS_PERMS_ALL===
select v.id||'|'||v.name from ab_view_menu v where v.name like 'datasource_access%' or v.name like '[%' order by v.id;
