select id||' | '||name from ab_role where name like '报表授权%' or name in ('Gamma','Admin','Public') order by id;
