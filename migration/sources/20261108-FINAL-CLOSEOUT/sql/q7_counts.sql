select 'slices|'||count(*) from slices;
select 'datasets|'||count(*) from tables;
select 'dashboards|'||count(*) from dashboards;
select 'published|'||count(*) from dashboards where published;
select 'users|'||count(*) from ab_user;
select 'roles|'||count(*) from ab_role;
select 'rls|'||count(*) from row_level_security_filters;
