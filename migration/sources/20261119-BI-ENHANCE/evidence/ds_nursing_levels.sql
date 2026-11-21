{% set tf = get_time_filter('STAT_BEGIN', strftime='%Y-%m-%d %H:%M:%S', remove_filter=True) %}
{% set tf_s = "'" + tf.from_expr + "'" if tf.from_expr else 'NULL' %}
{% set tf_e = "'" + tf.to_expr + "'" if tf.to_expr else 'NULL' %}
SELECT v.stat_begin, m.lvl AS 级别,
  CASE m.lvl WHEN '特级护理' THEN v.spec_care WHEN '病危' THEN v.crit_ill WHEN '病重' THEN v.crit_severe
       WHEN '普通护理' THEN v.gen_lvl1 WHEN '二级护理' THEN v.lvl2 ELSE v.lvl3 END AS val
FROM (
WITH input_bounds AS (
  SELECT NVL(TO_DATE({{ tf_s }},'YYYY-MM-DD HH24:MI:SS'),TRUNC(SYSDATE)-1) d1,
         NVL(TO_DATE({{ tf_e }},'YYYY-MM-DD HH24:MI:SS'),TRUNC(SYSDATE))-1/86400 d2 FROM dual),
chk AS (SELECT CASE WHEN d2<d1 OR TRUNC(d2)-TRUNC(d1)+1>366 THEN 1 ELSE 0 END over_limit FROM input_bounds),
bnd AS (SELECT d1,d2 FROM input_bounds WHERE (SELECT over_limit FROM chk)=0),
m0(ward,val) AS (SELECT waed_code ward,nvl ( sum ( bed_used_num ) , 0 ) from waed_adt_day where st_date >= (SELECT d1 FROM bnd) and st_date < (SELECT d2 FROM bnd) GROUP BY waed_code),
m1(ward,val) AS (SELECT b.ward_stayed ward,nvl ( count ( distinct a.patient_id ) , 0 ) from pat_visit a , ward_transfer b where a.patient_id =b.patient_id and a.visit_id =b.visit_id and instr ( a.patient_id , '_' ) =0 and a.admission_date_time >= (SELECT d1 FROM bnd) and a.admission_date_time <=(SELECT d2 FROM bnd) GROUP BY b.ward_stayed),
m2(ward,val) AS (SELECT b.ward_stayed ward,nvl ( count ( distinct a.patient_id ) , 0 ) from pat_visit a , ward_transfer b where a.patient_id =b.patient_id and a.visit_id =b.visit_id and instr ( a.patient_id , '_' ) =0 and a.admission_date_time >= (SELECT d1 FROM bnd) + 17 / 24 and a.admission_date_time < (SELECT d2 FROM bnd) + 8 / 24 GROUP BY b.ward_stayed),
m3(ward,val) AS (SELECT a.waed_code ward,NVL ( sum ( "A"."FROM_OTHER_WAED_NUM" ) , 0 ) FROM_OTHER_DEPT_NUM FROM WAED_ADT_DAY A WHERE A.ST_DATE >= (SELECT d1 FROM bnd) AND A.ST_DATE <= (SELECT d2 FROM bnd) GROUP BY a.waed_code),
m4(ward,val) AS (SELECT a.ward_code ward,nvl ( count ( distinct a.patient_id ) , 0 ) from ( select a.patient_id , c.order_text , a.ward_code , row_number ( ) over ( partition by c.patient_id order by c.start_date_time desc ) rn from ( select *from bedpats_in_hospital where stat_date_time =trunc ( sysdate ) - 1 and instr ( patient_id , '_' ) =0 ) a left join orders c on a.patient_id =c.patient_id and a.visit_id =c.visit_id where c.order_text in ( 'Ⅰ级护理' , 'Ⅱ级护理' , 'Ⅲ级护理' , '特级护理' ) and c.start_date_time < trunc ( sysdate ) and ( c.stop_date_time is null or c.stop_date_time > trunc ( sysdate - 1 ) ) ) a where a.rn =1 and a.order_text ='特级护理' GROUP BY a.ward_code),
m5(ward,val) AS (SELECT a.ward_code ward,nvl ( count ( distinct a.patient_id ) , 0 ) from ( select *from bedpats_in_hospital where stat_date_time =trunc ( sysdate ) - 1 and instr ( patient_id , '_' ) =0 ) a , ( select patient_id , visit_id , count ( 1 ) from ( select patient_id , visit_id , row_number ( ) over ( partition by patient_id order by start_date_time desc ) rn from orders where order_text in ( '病重' ) and start_date_time < trunc ( sysdate ) and ( stop_date_time is null or stop_date_time > trunc ( sysdate - 1 ) ) union all select patient_id , visit_id , row_number ( ) over ( partition by patient_id order by start_date_time desc ) rn from orders where order_text in ( 'Ⅰ级护理' ) and start_date_time < trunc ( sysdate ) and ( stop_date_time is null or stop_date_time > trunc ( sysdate - 1 ) ) ) where rn =1 group by patient_id , visit_id having count ( 1 ) > 1 ) b where a.patient_id =b.patient_id and a.visit_id =b.visit_id GROUP BY a.ward_code),
m6(ward,val) AS (SELECT a.ward_code ward,nvl ( count ( distinct a.patient_id ) , 0 ) from ( select *from bedpats_in_hospital where stat_date_time =trunc ( sysdate ) - 1 and instr ( patient_id , '_' ) =0 ) a , ( select patient_id , visit_id , count ( 1 ) from ( select patient_id , visit_id , row_number ( ) over ( partition by patient_id order by start_date_time desc ) rn from orders where order_text in ( '病危' ) and start_date_time < trunc ( sysdate ) and ( stop_date_time is null or stop_date_time > trunc ( sysdate - 1 ) ) union all select patient_id , visit_id , row_number ( ) over ( partition by patient_id order by start_date_time desc ) rn from orders where order_text in ( 'Ⅰ级护理' ) and start_date_time < trunc ( sysdate ) and ( stop_date_time is null or stop_date_time > trunc ( sysdate - 1 ) ) ) where rn =1 group by patient_id , visit_id having count ( 1 ) > 1 ) b where a.patient_id =b.patient_id and a.visit_id =b.visit_id GROUP BY a.ward_code),
m7(ward,val) AS (SELECT a.ward_code ward,count ( a.patient_id ) from ( select a.patient_id , c.order_text , a.ward_code , row_number ( ) over ( partition by c.patient_id order by c.start_date_time desc ) rn from ( select *from bedpats_in_hospital where stat_date_time =trunc ( sysdate ) - 1 and instr ( patient_id , '_' ) =0 ) a left join orders c on a.patient_id =c.patient_id and a.visit_id =c.visit_id where c.order_text in ( 'Ⅰ级护理' , 'Ⅱ级护理' , 'Ⅲ级护理' , '特级护理' ) and c.start_date_time < trunc ( sysdate ) and ( c.stop_date_time is null or c.stop_date_time > trunc ( sysdate - 1 ) ) ) a where a.rn =1 and a.order_text ='Ⅰ级护理' GROUP BY a.ward_code),
m8(ward,val) AS (SELECT a.ward_code ward,nvl ( count ( distinct a.patient_id ) , 0 ) from ( select a.patient_id , c.order_text , a.ward_code , row_number ( ) over ( partition by c.patient_id order by c.start_date_time desc ) rn from ( select *from bedpats_in_hospital where stat_date_time =trunc ( sysdate ) - 1 and instr ( patient_id , '_' ) =0 ) a left join orders c on a.patient_id =c.patient_id and a.visit_id =c.visit_id where c.order_text in ( 'Ⅰ级护理' , 'Ⅱ级护理' , 'Ⅲ级护理' , '特级护理' ) and c.start_date_time < trunc ( sysdate ) and ( c.stop_date_time is null or c.stop_date_time > trunc ( sysdate - 1 ) ) ) a where a.rn =1 and a.order_text ='Ⅱ级护理' GROUP BY a.ward_code),
m9(ward,val) AS (SELECT a.ward_code ward,nvl ( count ( distinct a.patient_id ) , 0 ) from ( select a.patient_id , c.order_text , a.ward_code , row_number ( ) over ( partition by c.patient_id order by c.start_date_time desc ) rn from ( select *from bedpats_in_hospital where stat_date_time =trunc ( sysdate ) - 1 and instr ( patient_id , '_' ) =0 ) a left join orders c on a.patient_id =c.patient_id and a.visit_id =c.visit_id where c.order_text in ( 'Ⅰ级护理' , 'Ⅱ级护理' , 'Ⅲ级护理' , '特级护理' ) and c.start_date_time < trunc ( sysdate ) and ( c.stop_date_time is null or c.stop_date_time > trunc ( sysdate - 1 ) ) ) a where a.rn =1 and a.order_text ='Ⅲ级护理' GROUP BY a.ward_code),
m10(ward,val) AS (SELECT waed_code ward,nvl ( sum ( trans_waed_num ) , 0 ) FROM WAED_ADT_DAY WHERE ST_DATE >= (SELECT d1 FROM bnd) AND ST_DATE <= (SELECT d2 FROM bnd) GROUP BY waed_code),
m11(ward,val) AS (SELECT waed_code ward,nvl ( sum ( discharge_normal_num ) , 0 ) FROM WAED_ADT_DAY WHERE ST_DATE >= (SELECT d1 FROM bnd) AND ST_DATE <= (SELECT d2 FROM bnd) GROUP BY waed_code),
m12(ward,val) AS (SELECT a.ward_code ward,nvl ( count ( distinct a.patient_id ) , 0 ) from ( select *from bedpats_in_hospital where stat_date_time =trunc ( sysdate ) - 1 and instr ( patient_id , '_' ) =0 ) a left join orders c on a.patient_id =c.patient_id and a.visit_id =c.visit_id where c.order_text like '%呼吸机%' and ( c.stop_date_time is null or c.stop_date_time > trunc ( sysdate - 1 ) ) GROUP BY a.ward_code),
spine AS (SELECT stat_deptcode ward,stat_deptname ks,plsx FROM stat_ward_modifyfix),
base AS (SELECT sp.ward,sp.ks,sp.plsx,
NVL(m0.val,0) STAY_NUM,
NVL(m1.val,0) TOTAL_ADM,
NVL(m2.val,0) NIGHT_ADM,
NVL(m3.val,0) TRANSIN_NUM,
NVL(m4.val,0) SPEC_CARE,
NVL(m5.val,0) CRIT_SEVERE,
NVL(m6.val,0) CRIT_ILL,
NVL(m7.val,0) LVL1,
NVL(m8.val,0) LVL2,
NVL(m9.val,0) LVL3,
NVL(m10.val,0) TRANSOUT_NUM,
NVL(m11.val,0) DISCH_NUM,
NVL(m12.val,0) VENTILATOR
FROM spine sp
LEFT JOIN m0 ON m0.ward=sp.ward
LEFT JOIN m1 ON m1.ward=sp.ward
LEFT JOIN m2 ON m2.ward=sp.ward
LEFT JOIN m3 ON m3.ward=sp.ward
LEFT JOIN m4 ON m4.ward=sp.ward
LEFT JOIN m5 ON m5.ward=sp.ward
LEFT JOIN m6 ON m6.ward=sp.ward
LEFT JOIN m7 ON m7.ward=sp.ward
LEFT JOIN m8 ON m8.ward=sp.ward
LEFT JOIN m9 ON m9.ward=sp.ward
LEFT JOIN m10 ON m10.ward=sp.ward
LEFT JOIN m11 ON m11.ward=sp.ward
LEFT JOIN m12 ON m12.ward=sp.ward),
g AS (SELECT ward,ks,plsx,SUM(stay_num) stay_num,SUM(total_adm) total_adm,SUM(night_adm) night_adm,
SUM(transin_num) transin_num,SUM(spec_care) spec_care,SUM(crit_severe) crit_severe,SUM(crit_ill) crit_ill,
SUM(lvl1-crit_severe-crit_ill) gen_lvl1,SUM(lvl2) lvl2,SUM(lvl3) lvl3,
SUM(transout_num) transout_num,SUM(disch_num) disch_num,SUM(ventilator) ventilator
FROM base GROUP BY GROUPING SETS ((ward,ks,plsx), ()))
SELECT ward ward_code,NULL err_msg,CASE WHEN ward IS NULL THEN '合计' ELSE ks END ks,plsx,
stay_num,total_adm,night_adm,transin_num,spec_care,crit_severe,crit_ill,gen_lvl1,lvl2,lvl3,
transout_num,disch_num,ventilator,(SELECT d1 FROM bnd) stat_begin,TRUNC((SELECT d2 FROM bnd)) stat_end
FROM g WHERE (SELECT over_limit FROM chk)=0
UNION ALL
SELECT NULL,'所选日期无效或超过366天，请缩小范围后重试',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL
FROM dual WHERE (SELECT over_limit FROM chk)=1

) v
CROSS JOIN (
  SELECT '特级护理' AS lvl FROM dual UNION ALL SELECT '病危' FROM dual UNION ALL SELECT '病重' FROM dual
  UNION ALL SELECT '普通护理' FROM dual UNION ALL SELECT '二级护理' FROM dual UNION ALL SELECT '三级护理' FROM dual
) m
WHERE v.ks NOT IN ('合计','总计','全院','计')
  AND CASE m.lvl WHEN '特级护理' THEN v.spec_care WHEN '病危' THEN v.crit_ill WHEN '病重' THEN v.crit_severe
       WHEN '普通护理' THEN v.gen_lvl1 WHEN '二级护理' THEN v.lvl2 ELSE v.lvl3 END > 0