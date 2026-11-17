{% set tf = get_time_filter('STAT_DATE', strftime='%Y-%m-%d', remove_filter=True) %}
{% set tf_s = tf.from_expr %}{% set tf_e = tf.to_expr %}
{# 原窗口按单日统计（各半点桶为该日内窗口）。范围控件消费：仅取起始日为统计日；所选范围>1天或超出今日-366天明确提示不出数；默认今日。 #}
WITH input_bounds AS (
  SELECT NVL(TRUNC(TO_DATE({{ "'" + tf_s + "'" if tf_s else 'NULL' }},'YYYY-MM-DD')), TRUNC(SYSDATE)) AS d1,
         NVL(CASE WHEN TO_DATE({{ "'" + tf_e + "'" if tf_e else 'NULL' }},'YYYY-MM-DD') = TRUNC(TO_DATE({{ "'" + tf_e + "'" if tf_e else 'NULL' }},'YYYY-MM-DD'))
                  THEN TRUNC(TO_DATE({{ "'" + tf_e + "'" if tf_e else 'NULL' }},'YYYY-MM-DD')) - 1
                  ELSE TRUNC(TO_DATE({{ "'" + tf_e + "'" if tf_e else 'NULL' }},'YYYY-MM-DD')) END, TRUNC(SYSDATE)) AS d2x FROM dual),
chk AS (SELECT CASE WHEN d2x - d1 + 1 <> 1 OR d1 > TRUNC(SYSDATE)+1 OR d1 < TRUNC(SYSDATE)-366 THEN 1 ELSE 0 END over_limit, d1, d2x FROM input_bounds),
bnd AS (SELECT d1 FROM chk WHERE over_limit=0)
select q.*, (SELECT d1 FROM bnd) STAT_DATE,
       (SELECT CASE WHEN over_limit=1 THEN '本报表按单日统计：请选择单一日期（起始=结束当天）；默认今日' END FROM chk) 提示
  from (


SELECT * FROM (

select '08:00' dtime, count(distinct(b.rcpt_no))

  from outp_rcpt_master a, OUTP_ORDER_DESC b

 where a.patient_id = b.patient_id

   and a.rcpt_no = b.rcpt_no

   and presc_indicator <> 0

   and a.visit_date >= to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD') || '00:00:00' , 'yyyy-mm-dd hh24:mi:ss')

   and a.visit_date <

       to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD')  ||' 08:00:00', 'yyyy-mm-dd hh24:mi:ss')

union all

select '08:30' dtime, count(distinct(b.rcpt_no))

  from outp_rcpt_master a, OUTP_ORDER_DESC b

 where a.patient_id = b.patient_id

   and a.rcpt_no = b.rcpt_no

   and presc_indicator <> 0

   and a.visit_date >= to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD') || '00:00:00' , 'yyyy-mm-dd hh24:mi:ss')

   and a.visit_date <

       to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD')  ||' 08:30:00', 'yyyy-mm-dd hh24:mi:ss')

union all

select '09:00' dtime, count(distinct(b.rcpt_no))

  from outp_rcpt_master a, OUTP_ORDER_DESC b

 where a.patient_id = b.patient_id

   and a.rcpt_no = b.rcpt_no

   and presc_indicator <> 0

   and a.visit_date >= to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD') || '00:00:00' , 'yyyy-mm-dd hh24:mi:ss')

   and a.visit_date <

       to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD')  ||' 09:00:00', 'yyyy-mm-dd hh24:mi:ss')

union all

select '09:30' dtime, count(distinct(b.rcpt_no))

  from outp_rcpt_master a, OUTP_ORDER_DESC b

 where a.patient_id = b.patient_id

   and a.rcpt_no = b.rcpt_no

   and presc_indicator <> 0

   and a.visit_date >= to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD') || '00:00:00' , 'yyyy-mm-dd hh24:mi:ss')

   and a.visit_date <

       to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD')  ||' 09:30:00', 'yyyy-mm-dd hh24:mi:ss')

union all

select '10:00' dtime, count(distinct(b.rcpt_no))

  from outp_rcpt_master a, OUTP_ORDER_DESC b

 where a.patient_id = b.patient_id

   and a.rcpt_no = b.rcpt_no

   and presc_indicator <> 0

   and a.visit_date >= to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD') || '00:00:00' , 'yyyy-mm-dd hh24:mi:ss')

   and a.visit_date <

       to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD')  ||' 10:00:00', 'yyyy-mm-dd hh24:mi:ss')

union all

select '10:30' dtime,count(distinct(b.rcpt_no))

  from outp_rcpt_master a, OUTP_ORDER_DESC b

 where a.patient_id = b.patient_id

   and a.rcpt_no = b.rcpt_no

   and presc_indicator <> 0

   and a.visit_date >= to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD') || '00:00:00' , 'yyyy-mm-dd hh24:mi:ss')

   and a.visit_date <

       to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD')  ||' 10:30:00', 'yyyy-mm-dd hh24:mi:ss')

union all

select '11:00' dtime, count(distinct(b.rcpt_no))

  from outp_rcpt_master a, OUTP_ORDER_DESC b

 where a.patient_id = b.patient_id

   and a.rcpt_no = b.rcpt_no

   and presc_indicator <> 0

   and a.visit_date >= to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD') || '00:00:00' , 'yyyy-mm-dd hh24:mi:ss')

   and a.visit_date <

       to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD')  ||' 11:00:00', 'yyyy-mm-dd hh24:mi:ss')

union all

select '11:30' dtime, count(distinct(b.rcpt_no))

  from outp_rcpt_master a, OUTP_ORDER_DESC b

 where a.patient_id = b.patient_id

   and a.rcpt_no = b.rcpt_no

   and presc_indicator <> 0

   and a.visit_date >= to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD') || '00:00:00' , 'yyyy-mm-dd hh24:mi:ss')

   and a.visit_date <

       to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD')  ||' 11:30:00', 'yyyy-mm-dd hh24:mi:ss')

union all

select '12:00' dtime, count(distinct(b.rcpt_no))

  from outp_rcpt_master a, OUTP_ORDER_DESC b

 where a.patient_id = b.patient_id

   and a.rcpt_no = b.rcpt_no

   and presc_indicator <> 0

   and a.visit_date >= to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD') || '00:00:00' , 'yyyy-mm-dd hh24:mi:ss')

   and a.visit_date <

       to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD')  ||' 12:00:00', 'yyyy-mm-dd hh24:mi:ss')

union all

select '13:30' dtime, count(distinct(b.rcpt_no))

  from outp_rcpt_master a, OUTP_ORDER_DESC b

 where a.patient_id = b.patient_id

   and a.rcpt_no = b.rcpt_no

   and presc_indicator <> 0

   and a.visit_date >= to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD') || '00:00:00' , 'yyyy-mm-dd hh24:mi:ss')

   and a.visit_date <

       to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD')  ||'13:30:00', 'yyyy-mm-dd hh24:mi:ss')

union all

select '14:00' dtime, count(distinct(b.rcpt_no))

  from outp_rcpt_master a, OUTP_ORDER_DESC b

 where a.patient_id = b.patient_id

   and a.rcpt_no = b.rcpt_no

   and presc_indicator <> 0

   and a.visit_date >= to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD') || '00:00:00' , 'yyyy-mm-dd hh24:mi:ss')

   and a.visit_date <

       to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD')  ||' 14:00:00', 'yyyy-mm-dd hh24:mi:ss')

union all

select '14:30' dtime, count(distinct(b.rcpt_no))

  from outp_rcpt_master a, OUTP_ORDER_DESC b

 where a.patient_id = b.patient_id

   and a.rcpt_no = b.rcpt_no

   and presc_indicator <> 0

   and a.visit_date >= to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD') || '00:00:00' , 'yyyy-mm-dd hh24:mi:ss')

   and a.visit_date <

       to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD')  ||' 14:30:00', 'yyyy-mm-dd hh24:mi:ss')

union all

select '15:00' dtime, count(distinct(b.rcpt_no))

  from outp_rcpt_master a, OUTP_ORDER_DESC b

 where a.patient_id = b.patient_id

   and a.rcpt_no = b.rcpt_no

   and presc_indicator <> 0

   and a.visit_date >= to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD') || '00:00:00' , 'yyyy-mm-dd hh24:mi:ss')

   and a.visit_date <

       to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD')  ||' 15:00:00', 'yyyy-mm-dd hh24:mi:ss')

union all

select '15:30' dtime, count(distinct(b.rcpt_no))

  from outp_rcpt_master a, OUTP_ORDER_DESC b

 where a.patient_id = b.patient_id

   and a.rcpt_no = b.rcpt_no

   and presc_indicator <> 0

   and a.visit_date >= to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD') || '00:00:00' , 'yyyy-mm-dd hh24:mi:ss')

   and a.visit_date <

       to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD')  ||' 15:30:00', 'yyyy-mm-dd hh24:mi:ss')

union all

select '16:00' dtime, count(distinct(b.rcpt_no))

  from outp_rcpt_master a, OUTP_ORDER_DESC b

 where a.patient_id = b.patient_id

   and a.rcpt_no = b.rcpt_no

   and presc_indicator <> 0

   and a.visit_date >= to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD') || '00:00:00' , 'yyyy-mm-dd hh24:mi:ss')

   and a.visit_date <

       to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD')  ||' 16:00:00', 'yyyy-mm-dd hh24:mi:ss')

union all

select '16:30' dtime, count(distinct(b.rcpt_no))

  from outp_rcpt_master a, OUTP_ORDER_DESC b

 where a.patient_id = b.patient_id

   and a.rcpt_no = b.rcpt_no

   and presc_indicator <> 0

   and a.visit_date >= to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD') || '00:00:00' , 'yyyy-mm-dd hh24:mi:ss')

   and a.visit_date <

       to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD')  ||' 16:30:00', 'yyyy-mm-dd hh24:mi:ss')

union all

select '17:00' dtime, count(distinct(b.rcpt_no))

  from outp_rcpt_master a, OUTP_ORDER_DESC b

 where a.patient_id = b.patient_id

   and a.rcpt_no = b.rcpt_no

   and presc_indicator <> 0

   and a.visit_date >= to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD') || '00:00:00' , 'yyyy-mm-dd hh24:mi:ss')

   and a.visit_date <

       to_date(TO_CHAR((SELECT d1 FROM bnd),'YYYY-MM-DD')  ||' 17:00:00', 'yyyy-mm-dd hh24:mi:ss')

)


) q

