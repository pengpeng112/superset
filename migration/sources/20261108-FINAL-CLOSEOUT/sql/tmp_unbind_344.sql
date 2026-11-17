\set ON_ERROR_STOP on
BEGIN;
DELETE FROM ab_user_role WHERE role_id=344 AND user_id=(SELECT id FROM ab_user WHERE username='003158');
COMMIT;
select 'TEMP_UNBIND|remaining='||count(*) FROM ab_user_role WHERE role_id=344;
