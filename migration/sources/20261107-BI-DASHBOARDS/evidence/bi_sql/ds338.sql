{% set tf = get_time_filter('STAT_BEGIN', strftime='%Y-%m-%d %H:%M:%S', remove_filter=True) %}
{% set tf_s = "'" + tf.from_expr + "'" if tf.from_expr else 'NULL' %}
{% set tf_e = "'" + tf.to_expr + "'" if tf.to_expr else 'NULL' %}
WITH input_bounds AS (
  SELECT NVL(TO_DATE({{ tf_s }},'YYYY-MM-DD HH24:MI:SS'),ADD_MONTHS(TRUNC(SYSDATE,'MM'),-1)) d1,
         NVL(TO_DATE({{ tf_e }},'YYYY-MM-DD HH24:MI:SS'),TRUNC(SYSDATE,'MM'))-1/86400 d2 FROM dual),
chk AS (SELECT CASE WHEN d2<d1 OR TRUNC(d2)-TRUNC(d1)+1>366 THEN 1 ELSE 0 END over_limit FROM input_bounds),
bnd AS (SELECT d1,d2 FROM input_bounds WHERE (SELECT over_limit FROM chk)=0),
legacy AS (select t.dept_code,

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

       sum(t.will) will,

       sum(t.transfer) transfer,

       sum(t.TRANS_HOSPITAL_NUM) TRANS_HOSPITAL_NUM,

       sum(t.ADM_OUTP_NUM) ADM_OUTP_NUM,

       sum(t.FROM_OTHER_HOSPITAL_NUM) FROM_OTHER_HOSPITAL_NUM,

       sum(t.CANCEL_DISCHARGE_NUM) CANCEL_DISCHARGE_NUM,

sum(t.FROM_OTHER_DEPT_NUM) FROM_OTHER_DEPT_NUM,

SUM(T.TRANS_DEPT_NUM) TRANS_DEPT_NUM,

       sum(t.orial) orial,

       t.ksdm,

       t.plsx



  from (SELECT '' DEPT_CODE,

               0 total_num,

               0 normal_num,

               0 emergency_num,

               0 emer_died_num,

               0 catch_num,

               0 catch_died_num,

               0 check_num,

               0 recover,

               0 effect,

               0 untreat,

               0 died,

               0 other,

               0 will,

               0 transfer,

               0 TRANS_HOSPITAL_NUM,

               0 as ADM_OUTP_NUM,

               0 as FROM_OTHER_HOSPITAL_NUM,

               0 as CANCEL_DISCHARGE_NUM,

0 FROM_OTHER_DEPT_NUM,

0 TRANS_DEPT_NUM,

               0 as orial,

               dept_dict.tj_ksmc ksdm,

               dept_dict.plsx plsx

          FROM V_PAT_VISIT, DEPT_DICT

         WHERE V_PAT_VISIT.DEPT_DISCHARGE_FROM = DEPT_DICT.Dept_Code(+)

           AND (V_PAT_VISIT.DISCHARGE_DATE_TIME >= (SELECT d1 FROM bnd))

           AND (V_PAT_VISIT.DISCHARGE_DATE_TIME <= (SELECT d2 FROM bnd))

           and instr(V_PAT_VISIT.PATIENT_ID,'_') <= 0 

         GROUP BY dept_dict.tj_ksmc, dept_dict.plsx

        

        union all

        

        SELECT '' DEPT_CODE,

               0 total_num,

               0 normal_num,

               0 emergency_num,

               0 emer_died_num,

               0 catch_num,

               0 catch_died_num,

               0 check_num,

               nvl(sum(DEPT_ADT_DAY.Discharge_Disposition_Recover),0) recover,

               nvl(sum(DEPT_ADT_DAY.Discharge_Disposition_Effect),0) effect,

               nvl(sum(DEPT_ADT_DAY.Discharge_Disposition_Invaled),0) untreat,

               nvl(sum(DEPT_ADT_DAY.Discharge_Disposition_Died),0) died,

               nvl(sum(DEPT_ADT_DAY.DISCHARGE_DISPOSITION_OTHER),0) other,

               nvl(sum(DEPT_ADT_DAY.DISCHARGE_DISPOSITION_WILL),0) will,

               nvl(sum(DEPT_ADT_DAY.DISCHARGE_DISPOSITION_TRANSFER),0) transfer,

               nvl(sum(DEPT_ADT_DAY.TRANS_HOSPITAL_NUM),0) TRANS_HOSPITAL_NUM,

               SUM(NVL("DEPT_ADT_DAY"."ADM_OUTP_NUM", 0)) ADM_OUTP_NUM,

               SUM(NVL("DEPT_ADT_DAY"."FROM_OTHER_HOSPITAL_NUM", 0)) FROM_OTHER_HOSPITAL_NUM,

               SUM(NVL("DEPT_ADT_DAY"."CANCEL_DISCHARGE_NUM", 0)) CANCEL_DISCHARGE_NUM,

SUM(NVL("DEPT_ADT_DAY"."FROM_OTHER_DEPT_NUM", 0)) FROM_OTHER_DEPT_NUM,

SUM(NVL("DEPT_ADT_DAY"."TRANS_DEPT_NUM", 0)) TRANS_DEPT_NUM,

               0 orial,

               dept_dict.tj_ksmc ksdm,

               dept_dict.plsx plsx

          FROM "DEPT_ADT_DAY", dept_dict

         WHERE DEPT_ADT_DAY.Dept_Code = dept_dict.dept_code(+)

           and ("DEPT_ADT_DAY"."ST_DATE" >= (SELECT d1 FROM bnd))

           AND ("DEPT_ADT_DAY"."ST_DATE" <= (SELECT d2 FROM bnd))

         GROUP BY dept_dict.tj_ksmc, dept_dict.plsx

     union all

               SELECT '' DEPT_CODE,

               0 total_num,

               0 normal_num,

               0 emergency_num,

               0 emer_died_num,

               0 catch_num,

               0 catch_died_num,

               0 check_num,

               0 recover,

               0 effect,

               0 untreat,

               0 died,

               0 other,

               0 will,

               0 transfer,

               0 TRANS_HOSPITAL_NUM,

               0 ADM_OUTP_NUM,

               0 FROM_OTHER_HOSPITAL_NUM,

               0 as CANCEL_DISCHARGE_NUM,

0 FROM_OTHER_DEPT_NUM,

0 TRANS_DEPT_NUM,

               SUM(decode("DEPT_ADT_DAY"."ST_DATE",

                          trunc(last_day(add_months((SELECT d1 FROM bnd),-1))),

                          "DEPT_ADT_DAY"."BED_USED_NUM",

                          0)) orial,

               dept_dict.tj_ksmc ksdm,

               dept_dict.plsx plsx

          FROM "DEPT_ADT_DAY", dept_dict

         WHERE DEPT_ADT_DAY.Dept_Code = dept_dict.dept_code(+)

           and ("DEPT_ADT_DAY"."ST_DATE" = trunc(last_day(add_months((SELECT d1 FROM bnd),-1))))

         GROUP BY dept_dict.tj_ksmc, dept_dict.plsx

) t

 group by t.dept_code,t.ksdm, t.plsx

 order by substr(t.dept_code,1,4), t.plsx),
r AS (SELECT l.ksdm,l.plsx,l.orial,

  l.adm_outp_num+l.from_other_hospital_num+l.cancel_discharge_num rumen,
  l.from_other_dept_num zhuanru,l.recover,l.effect,l.untreat,l.died,
  l.other other_n,l.will will_n,l.transfer xfer,
  l.recover+l.effect+l.untreat+l.died+l.other+l.will+l.transfer chuyuan,
  l.trans_dept_num zhuanchu
FROM legacy l)
SELECT (SELECT d1 FROM bnd) stat_begin, TRUNC((SELECT d2 FROM bnd)) stat_end,
  ksdm,plsx,orial,rumen,zhuanru,recover,effect,untreat,died,other_n,will_n,xfer,chuyuan,zhuanchu,
  orial+rumen+zhuanru-chuyuan-zhuanchu curr, 0 diff_n FROM r
UNION ALL
SELECT NULL,NULL,'所选日期无效或超过366天，请缩小范围后重试',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL
FROM dual WHERE (SELECT over_limit FROM chk)=1
ORDER BY plsx,ksdm
