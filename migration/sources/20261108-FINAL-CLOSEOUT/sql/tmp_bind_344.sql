\set ON_ERROR_STOP on
BEGIN;
INSERT INTO ab_user_role (id, user_id, role_id)
SELECT (SELECT coalesce(max(id),0) FROM ab_user_role)+1, u.id, 344
FROM ab_user u WHERE u.username='003158'
  AND NOT EXISTS (SELECT 1 FROM ab_user_role ur WHERE ur.user_id=u.id AND ur.role_id=344);
COMMIT;
select 'TEMP_BIND|'||u.username||'|role=344|ok='||(count(ur.id)>0)
from ab_user u left join ab_user_role ur on ur.user_id=u.id and ur.role_id=344
where u.username='003158' group by u.username;
