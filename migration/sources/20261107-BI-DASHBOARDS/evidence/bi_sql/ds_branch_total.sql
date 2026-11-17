{% set tf = get_time_filter('STAT_BEGIN', strftime='%Y-%m-%d %H:%M:%S', remove_filter=True) %}
{% set tf_s = "'" + tf.from_expr + "'" if tf.from_expr else 'NULL' %}
{% set tf_e = "'" + tf.to_expr + "'" if tf.to_expr else 'NULL' %}
SELECT '门诊' AS branch_name, t.oper_num, t.stat_begin FROM (
{% set branch = '0' %}
WITH input_bounds AS (
  SELECT NVL(TO_DATE({{ tf_s }},'YYYY-MM-DD HH24:MI:SS'),TRUNC(SYSDATE)-7) d1,
         NVL(TO_DATE({{ tf_e }},'YYYY-MM-DD HH24:MI:SS'),TRUNC(SYSDATE))-1/86400 d2 FROM dual),
chk AS (SELECT CASE WHEN d2<d1 OR TRUNC(d2)-TRUNC(d1)+1>366 THEN 1 ELSE 0 END over_limit FROM input_bounds),
bnd AS (SELECT d1,d2 FROM input_bounds WHERE (SELECT over_limit FROM chk)=0),
legacy AS (select * from 

(

select dept_dict.tj_ksmc, dept_dict.plsx, count(*) oper_num

  from (select distinct a.rcpt_no,a.visit_date,a.performed_by,a.item_class from  outp_bill_items a where a.item_class = 'F') outp_bill_items, dept_dict

 where outp_bill_items.performed_by = dept_dict.dept_code

   and outp_bill_items.item_class = 'F'

   and outp_bill_items.RCPT_NO IN (SELECT RCPT_NO FROM OUTP_RCPT_MASTER WHERE CHARGE_INDICATOR = 0)

   and (outp_bill_items.visit_date between (SELECT d1 FROM bnd) and (SELECT d2 FROM bnd))

   and {{ branch }} = 0

 group by dept_dict.tj_ksmc, dept_dict.plsx

 order by dept_dict.plsx

)

union all

select * from 

(

select tj_ksmc, plsx,count(*) oper_num

  from (select a.start_date_time as 手术时间,

               a.patient_id as Id,

               a.visit_id as 住院次数,

               c.name as 姓名,

               a.diag_after_operation 术后诊断,

               b.dept_name tj_ksmc, 

               (select operation

                  from (select e.patient_id,

                               e.visit_id,

                               listagg(e.operation, ' || ') within group(order by e.operation) as operation

                          from operation_name e

                         group by e.patient_id, e.visit_id)

                 where patient_id = a.patient_id

                   and visit_id = a.visit_id) 手术名称,

               b.plsx

          from (select a.start_date_time,

                       a.patient_id,

                       a.visit_id,

                       a.diag_after_operation,

                       (case

                         when (select count(1)

                                 from lend_bed_log

                                where dept_code <> lend_dept_code

                             and patient_id = a.patient_id

                             and visit_id = a.visit_id

                             and lend_end_date is not null) > 0 then

                          (select lend_dept_code

                             from lend_bed_log

                            where dept_code <> lend_dept_code

                         and patient_id = a.patient_id

                         and visit_id = a.visit_id

                         and rownum = 1)

                         else

                          a.operating_dept

                       end) operating_dept

                  from operation_master a) a,

               dept_dict b,

               pat_master_index c

         where a.start_date_time between (SELECT d1 FROM bnd) and (SELECT d2 FROM bnd) 

           and a.operating_dept = b.dept_code

           and a.patient_id = c.patient_id

  			  and {{ branch }} = 1)

 group by tj_ksmc , plsx

 order by plsx

) ),
data_rows AS (SELECT tj_ksmc,plsx,oper_num FROM legacy),
r AS (SELECT tj_ksmc,plsx,oper_num,0 is_total FROM data_rows
 UNION ALL SELECT '合计',NULL,SUM(oper_num),1 FROM data_rows)
SELECT ROW_NUMBER() OVER (ORDER BY is_total,plsx,tj_ksmc) xh,tj_ksmc,oper_num,
  {% if branch == '0' %}'门诊'{% else %}'住院'{% endif %} branch_name,
  (SELECT d1 FROM bnd) stat_begin,TRUNC((SELECT d2 FROM bnd)) stat_end FROM r
WHERE (SELECT over_limit FROM chk)=0
UNION ALL
SELECT NULL,'所选日期无效或超过366天，请缩小范围后重试',NULL,NULL,NULL,NULL
FROM dual WHERE (SELECT over_limit FROM chk)=1
ORDER BY xh
) t WHERE t.tj_ksmc = '合计'
UNION ALL
SELECT '住院' AS branch_name, t.oper_num, t.stat_begin FROM (
{% set branch = '1' %}
WITH input_bounds AS (
  SELECT NVL(TO_DATE({{ tf_s }},'YYYY-MM-DD HH24:MI:SS'),TRUNC(SYSDATE)-7) d1,
         NVL(TO_DATE({{ tf_e }},'YYYY-MM-DD HH24:MI:SS'),TRUNC(SYSDATE))-1/86400 d2 FROM dual),
chk AS (SELECT CASE WHEN d2<d1 OR TRUNC(d2)-TRUNC(d1)+1>366 THEN 1 ELSE 0 END over_limit FROM input_bounds),
bnd AS (SELECT d1,d2 FROM input_bounds WHERE (SELECT over_limit FROM chk)=0),
legacy AS (select * from 

(

select dept_dict.tj_ksmc, dept_dict.plsx, count(*) oper_num

  from (select distinct a.rcpt_no,a.visit_date,a.performed_by,a.item_class from  outp_bill_items a where a.item_class = 'F') outp_bill_items, dept_dict

 where outp_bill_items.performed_by = dept_dict.dept_code

   and outp_bill_items.item_class = 'F'

   and outp_bill_items.RCPT_NO IN (SELECT RCPT_NO FROM OUTP_RCPT_MASTER WHERE CHARGE_INDICATOR = 0)

   and (outp_bill_items.visit_date between (SELECT d1 FROM bnd) and (SELECT d2 FROM bnd))

   and {{ branch }} = 0

 group by dept_dict.tj_ksmc, dept_dict.plsx

 order by dept_dict.plsx

)

union all

select * from 

(

select tj_ksmc, plsx,count(*) oper_num

  from (select a.start_date_time as 手术时间,

               a.patient_id as Id,

               a.visit_id as 住院次数,

               c.name as 姓名,

               a.diag_after_operation 术后诊断,

               b.dept_name tj_ksmc, 

               (select operation

                  from (select e.patient_id,

                               e.visit_id,

                               listagg(e.operation, ' || ') within group(order by e.operation) as operation

                          from operation_name e

                         group by e.patient_id, e.visit_id)

                 where patient_id = a.patient_id

                   and visit_id = a.visit_id) 手术名称,

               b.plsx

          from (select a.start_date_time,

                       a.patient_id,

                       a.visit_id,

                       a.diag_after_operation,

                       (case

                         when (select count(1)

                                 from lend_bed_log

                                where dept_code <> lend_dept_code

                             and patient_id = a.patient_id

                             and visit_id = a.visit_id

                             and lend_end_date is not null) > 0 then

                          (select lend_dept_code

                             from lend_bed_log

                            where dept_code <> lend_dept_code

                         and patient_id = a.patient_id

                         and visit_id = a.visit_id

                         and rownum = 1)

                         else

                          a.operating_dept

                       end) operating_dept

                  from operation_master a) a,

               dept_dict b,

               pat_master_index c

         where a.start_date_time between (SELECT d1 FROM bnd) and (SELECT d2 FROM bnd) 

           and a.operating_dept = b.dept_code

           and a.patient_id = c.patient_id

  			  and {{ branch }} = 1)

 group by tj_ksmc , plsx

 order by plsx

) ),
data_rows AS (SELECT tj_ksmc,plsx,oper_num FROM legacy),
r AS (SELECT tj_ksmc,plsx,oper_num,0 is_total FROM data_rows
 UNION ALL SELECT '合计',NULL,SUM(oper_num),1 FROM data_rows)
SELECT ROW_NUMBER() OVER (ORDER BY is_total,plsx,tj_ksmc) xh,tj_ksmc,oper_num,
  {% if branch == '0' %}'门诊'{% else %}'住院'{% endif %} branch_name,
  (SELECT d1 FROM bnd) stat_begin,TRUNC((SELECT d2 FROM bnd)) stat_end FROM r
WHERE (SELECT over_limit FROM chk)=0
UNION ALL
SELECT NULL,'所选日期无效或超过366天，请缩小范围后重试',NULL,NULL,NULL,NULL
FROM dual WHERE (SELECT over_limit FROM chk)=1
ORDER BY xh
) t WHERE t.tj_ksmc = '合计'
ORDER BY branch_name