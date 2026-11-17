{% set tf = get_time_filter('STAT_BEGIN', strftime='%Y-%m-%d %H:%M:%S', remove_filter=True) %}
{% set tf_s = "'" + tf.from_expr + "'" if tf.from_expr else 'NULL' %}
{% set tf_e = "'" + tf.to_expr + "'" if tf.to_expr else 'NULL' %}
WITH input_bounds AS (
  SELECT NVL(TO_DATE({{ tf_s }},'YYYY-MM-DD HH24:MI:SS'),ADD_MONTHS(TRUNC(SYSDATE,'MM'),-1)) d1,
         NVL(TO_DATE({{ tf_e }},'YYYY-MM-DD HH24:MI:SS'),TRUNC(SYSDATE,'MM'))-1/86400 d2 FROM dual),
chk AS (SELECT CASE WHEN d2<d1 OR TRUNC(d2)-TRUNC(d1)+1>366 THEN 1 ELSE 0 END over_limit FROM input_bounds),
bnd AS (SELECT d1,d2 FROM input_bounds WHERE (SELECT over_limit FROM chk)=0),
legacy AS (select  d.tj_ksmc as dept_code,

       null jgs,

  sum(t.total_num) total_num,

  sum(t.normal_num) normal_num,

  sum(t.emergency_num) emergency_num,

  sum(t.emer_died_num) emer_died_num,

  sum(t.catch_num) catch_num,

  sum(t.catch_died_num) catch_died_num,

  sum(t.check_num) check_num,

  sum(t.recover) recover,

  sum(t.effect) effect,

  sum(t.untreat) untreat,

  sum(t.died) died,

  sum(t.other) other,

  sum(t.ADM_OUTP_NUM) ADM_OUTP_NUM,

  sum(t.FROM_OTHER_HOSPITAL_NUM) FROM_OTHER_HOSPITAL_NUM,

   sum(t.orial) orial,

    sum(t.curr) curr,

    d.tj_ksmc,

    d.plsx

from (



select a.dept_code,

    total_num,

    normal_num,

    emergency_num,

    emer_died_num,

    catch_num,

    catch_died_num,

    check_num,

    0 recover,

    0 effect,

    0 untreat,

    0  died,

    0 other,

    0 ADM_OUTP_NUM,

    0 FROM_OTHER_HOSPITAL_NUM,

    0 as orial,

    0 as curr

from 

(select dept_code,

    sum(total_num) total_num,

    sum(normal_num) normal_num,

    sum(emergency_num) emergency_num,

    sum(emer_died_num) emer_died_num,

    sum(catch_num) catch_num,

    sum(catch_died_num) catch_died_num,

    sum(check_num) check_num

   

FROM

(select Nvl(clinic_master.visit_dept,'') dept_code,

    count(*) total_num,

    sum(decode(nvl(clinic_master.clinic_type,'*'),'专家号主',1,'专家号副',1,'知名专家',1,0)) normal_num,

    sum(decode(nvl(clinic_master.clinic_type,'*'),'急诊号',1,0)) emergency_num,

    0 emer_died_num,

    0 catch_num,

    0 catch_died_num,

    0 check_num

 from clinic_master,dept_dict 

where ( Trunc(clinic_master.Visit_date) between (SELECT d1 FROM bnd) and (SELECT d2 FROM bnd)  ) and 

    ( clinic_master.RETURNED_DATE is null ) and

    (dept_dict.dept_code(+) =clinic_master.visit_dept) 

group by Nvl(visit_dept,'')

union all

select Nvl(DEPT_CODE,'') ,

    0,

    0,

    0,

    0 ,

    0 ,

    0 ,

    sum(HEALTH_EXAM_NUM) check_num

from DEPT_OUTP_NUM_DAY 

where ( Trunc(ST_DATE) between (SELECT d1 FROM bnd) and (SELECT d2 FROM bnd)  ) 

group by Nvl(DEPT_CODE,'')

union all

select Nvl(DEPT_CODE,'') ,

    0,

    0,

    0,

    sum(died_in_clinic_num) emer_died_num,

    sum(admitted_num) catch_num,

    sum(died_in_observ_num) catch_died_num,

    0 check_num

  from EMERGENCY_DAY 

where ( Trunc(ST_DATE) between (SELECT d1 FROM bnd) and (SELECT d2 FROM bnd)  ) 

    

group by Nvl(DEPT_CODE,''))

group by dept_code) a

) t, dept_dict d

where t.dept_code = d.dept_code(+)

   group by d.tj_ksmc,d.plsx

   order by d.plsx )
SELECT (SELECT d1 FROM bnd) stat_begin, TRUNC((SELECT d2 FROM bnd)) stat_end,
  tj_ksmc ksdm,plsx,jgs,total_num,total_num ji,total_num-emergency_num men_zhens,
  emergency_num jizhens,emer_died_num jizhen_siwang,catch_num guancha,
  catch_died_num guancha_siwang,check_num jiancha FROM legacy
UNION ALL
SELECT NULL,NULL,'所选日期无效或超过366天，请缩小范围后重试',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL
FROM dual WHERE (SELECT over_limit FROM chk)=1
ORDER BY plsx,ksdm
