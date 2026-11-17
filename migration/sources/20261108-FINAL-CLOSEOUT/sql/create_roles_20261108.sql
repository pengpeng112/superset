\set ON_ERROR_STOP on
BEGIN;

-- ============ 20261108-FINAL-CLOSEOUT 任务1：专项明细角色门禁（幂等，v2 显式 id） ============
-- ab_role / ab_permission_view / ab_permission_view_role 无自增序列，id 必须显式给值。

-- 1) 建角色（幂等；id = 当前 max + 行号）
INSERT INTO ab_role (id, name)
SELECT (SELECT max(id) FROM ab_role) + row_number() OVER (ORDER BY v.ord), v.name
FROM (VALUES (1,'报表授权_门急诊患者明细'),(2,'报表授权_手术明细提取')) AS v(ord, name)
WHERE NOT EXISTS (SELECT 1 FROM ab_role r WHERE r.name = v.name);

-- 2) 看板绑定 dashboard_roles（幂等；dashboard_roles.id 有自增）
INSERT INTO dashboard_roles (dashboard_id, role_id)
SELECT d.dashboard_id, r.id
FROM (VALUES (47),(49),(50),(51),(52)) AS d(dashboard_id)
JOIN ab_role r ON r.name = CASE
  WHEN d.dashboard_id IN (47,49) THEN '报表授权_门急诊患者明细'
  ELSE '报表授权_手术明细提取' END
WHERE NOT EXISTS (
  SELECT 1 FROM dashboard_roles dr
  WHERE dr.dashboard_id = d.dashboard_id AND dr.role_id = r.id);

-- 3) 数据集读取权限 join 行（幂等；一般已由建数据集时生成，缺则补）
INSERT INTO ab_permission_view (id, permission_id, view_menu_id)
SELECT (SELECT coalesce(max(id),0) FROM ab_permission_view) + row_number() OVER (ORDER BY v.name), p.id, v.id
FROM ab_permission p
JOIN ab_view_menu v ON v.name IN (
  '[HIS实库].[统计报表·d_clinic_pats](id:279)',
  '[HIS实库].[急诊分诊统计](id:321)',
  '[HIS实库].[统计报表·d_3](id:276)',
  '[HIS实库].[科室手术质量分析](id:332)',
  '[HIS实库].[科室住院手术数据提取](id:333)')
WHERE p.name = 'datasource_access'
  AND NOT EXISTS (
    SELECT 1 FROM ab_permission_view pv
    WHERE pv.permission_id = p.id AND pv.view_menu_id = v.id);

-- 4) 角色挂数据集权限（幂等）
INSERT INTO ab_permission_view_role (id, permission_view_id, role_id)
SELECT (SELECT coalesce(max(id),0) FROM ab_permission_view_role) + row_number() OVER (ORDER BY r.id, v.name), pv.id, r.id
FROM ab_permission_view pv
JOIN ab_view_menu v ON v.id = pv.view_menu_id
JOIN ab_permission p ON p.id = pv.permission_id AND p.name = 'datasource_access'
JOIN ab_role r ON (
  (v.name IN ('[HIS实库].[统计报表·d_clinic_pats](id:279)','[HIS实库].[急诊分诊统计](id:321)')
   AND r.name = '报表授权_门急诊患者明细')
  OR
  (v.name IN ('[HIS实库].[统计报表·d_3](id:276)','[HIS实库].[科室手术质量分析](id:332)','[HIS实库].[科室住院手术数据提取](id:333)')
   AND r.name = '报表授权_手术明细提取'))
WHERE NOT EXISTS (
  SELECT 1 FROM ab_permission_view_role pvr
  WHERE pvr.permission_view_id = pv.id AND pvr.role_id = r.id);

COMMIT;

\echo ===NEW_ROLES===
select id||'|'||name from ab_role where name like '报表授权%' order by id;
\echo ===ROLE_DASH_BINDINGS===
select r.id||'|'||r.name||'||dashboards='||coalesce((select string_agg(dr.dashboard_id::text,',' order by dr.dashboard_id) from dashboard_roles dr where dr.role_id=r.id),'none')
from ab_role r where r.name like '报表授权%' order by r.id;
\echo ===ROLE_DATASOURCE_PERMS===
select r.id||'|'||v.name
from ab_role r
join ab_permission_view_role pvr on pvr.role_id=r.id
join ab_permission_view pv on pv.id=pvr.permission_view_id
join ab_permission p on p.id=pv.permission_id
join ab_view_menu v on v.id=pv.view_menu_id
where r.name like '报表授权%' and p.name='datasource_access' order by r.id,v.name;
\echo ===ROLE_MEMBERS===
select r.id||'|'||r.name||'|members='||count(ur.user_id)
from ab_role r left join ab_user_role ur on ur.role_id=r.id
where r.name like '报表授权%' group by r.id,r.name order by r.id;
