{% set tf = get_time_filter('STAT_BEGIN', strftime='%Y-%m-%d', remove_filter=True) %}
{% set tf_s = "'" + tf.from_expr + "'" if tf.from_expr else 'NULL' %}
{% set tf_e = "'" + tf.to_expr + "'" if tf.to_expr else 'NULL' %}
WITH input_bounds AS (
  SELECT NVL(TRUNC(TO_DATE({{ tf_s }},'YYYY-MM-DD')), ADD_MONTHS(TRUNC(SYSDATE,'MM'),-1)) AS d1,
         NVL(CASE WHEN TO_DATE({{ tf_e }},'YYYY-MM-DD') = TRUNC(TO_DATE({{ tf_e }},'YYYY-MM-DD'))
                  THEN TRUNC(TO_DATE({{ tf_e }},'YYYY-MM-DD')) - 1
                  ELSE TRUNC(TO_DATE({{ tf_e }},'YYYY-MM-DD')) END,
             TRUNC(SYSDATE,'MM')-1) AS d2 FROM dual),
chk AS (SELECT CASE WHEN d2<d1 OR d2-d1+1>366 THEN 1 ELSE 0 END over_limit FROM input_bounds),
bnd AS (SELECT d1,d2 FROM input_bounds WHERE (SELECT over_limit FROM chk)=0),
rng AS (SELECT d1, d2, (d2 - d1) + 1 AS days FROM bnd),
cal AS (SELECT (SELECT d1 FROM rng) + LEVEL - 1 AS dd FROM dual CONNECT BY (SELECT d1 FROM rng) + LEVEL - 1 <= (SELECT d2 FROM rng)),
fx AS (SELECT stat_deptcode, start_date, ori_bednum, modify_date, modify_bednum FROM stat_dept_modifyfix),
bedday AS (SELECT f.stat_deptcode, c.dd,
             CASE WHEN f.modify_date IS NULL OR c.dd < f.modify_date THEN NVL(f.ori_bednum,0) ELSE NVL(f.modify_bednum,0) END beds
           FROM fx f JOIN cal c ON c.dd >= f.start_date
           WHERE NOT EXISTS (SELECT 1 FROM fx f2 WHERE f2.stat_deptcode=f.stat_deptcode
                              AND f2.start_date > f.start_date AND f2.start_date <= c.dd)),
beds AS (SELECT stat_deptcode dept_code, SUM(beds) open_days,
                 SUM(CASE WHEN dd = (SELECT d2 FROM rng) THEN beds ELSE 0 END) bed_end
         FROM bedday GROUP BY stat_deptcode),
flow AS (SELECT a.dept_code,
           SUM(NVL(a.discharge_disposition_recover,0)) recover,
           SUM(NVL(a.discharge_disposition_effect,0)) effect,
           SUM(NVL(a.discharge_disposition_invaled,0)) untreat,
           SUM(NVL(a.discharge_disposition_died,0)) died,
           SUM(NVL(a.discharge_disposition_other,0)) other_n,
           SUM(NVL(a.trans_dept_num,0)) trans_num,
           SUM(NVL(a.bed_used_num,0)) used_days
         FROM dept_adt_day a
         WHERE a.st_date >= (SELECT d1 FROM rng) AND a.st_date <= (SELECT d2 FROM rng)
         GROUP BY a.dept_code),
dsc AS (SELECT t.dept_stayed dept_code,
          SUM(CASE WHEN TRUNC(t.discharge_date_time)=TRUNC(t.admission_date_time) THEN 1 ELSE TRUNC(t.discharge_date_time)-TRUNC(t.admission_date_time) END) occ_days
        FROM transfer t JOIN pat_visit s ON s.patient_id = t.patient_id AND s.visit_id = t.visit_id
        WHERE t.discharge_date_time >= (SELECT d1 FROM rng) AND (t.discharge_date_time <= (SELECT d2 FROM rng)+1-1/86400 OR t.discharge_date_time IS NULL)
          AND s.admission_cause <> '新生儿'
        GROUP BY t.dept_stayed),
spine AS (SELECT stat_deptcode dept_code FROM stat_dept_modifyfix),
j AS (SELECT s.dept_code, (SELECT d1 FROM rng) d1, (SELECT d2 FROM rng) d2, (SELECT days FROM rng) days,
         NVL(b.bed_end,0) bed_end, NVL(b.open_days,0) open_days,
         NVL(f.recover,0) recover, NVL(f.effect,0) effect, NVL(f.untreat,0) untreat,
         NVL(f.died,0) died, NVL(f.other_n,0) other_n, NVL(f.trans_num,0) trans_num, NVL(f.used_days,0) used_days,
         NVL(d.occ_days,0) occ_days
       FROM spine s LEFT JOIN beds b ON b.dept_code=s.dept_code
       LEFT JOIN flow f ON f.dept_code=s.dept_code LEFT JOIN dsc d ON d.dept_code=s.dept_code),
g AS (SELECT j.dept_code, dd.tj_ksmc ks, dd.plsx,
        SUM(j.bed_end) bed_end, SUM(j.open_days) open_days, MAX(j.days) days,
        SUM(j.used_days) used_days, SUM(j.occ_days) occ_days, SUM(j.trans_num) trans_num,
        SUM(j.recover) recover, SUM(j.effect) effect, SUM(j.untreat) untreat, SUM(j.died) died, SUM(j.other_n) other_n
      FROM j LEFT JOIN dept_dict dd ON dd.dept_code = j.dept_code
      GROUP BY GROUPING SETS ((j.dept_code, dd.tj_ksmc, dd.plsx), ())),
r AS (SELECT dept_code, ks, CASE WHEN dept_code IS NULL THEN 1 ELSE 0 END is_total, CASE WHEN plsx IS NULL THEN 999999 ELSE plsx END plsx,
        bed_end, open_days, days, used_days, occ_days, trans_num,
        recover, effect, untreat, died, other_n,
        recover+effect+untreat+died+other_n disch_n,
        CASE WHEN open_days=0 THEN 0 ELSE open_days/days END avg_beds
      FROM g)
SELECT dept_code, CASE WHEN (SELECT over_limit FROM chk)=1 THEN '所选日期无效或超过366天，请缩小范围后重试' WHEN is_total=1 THEN '总计' ELSE ks END ks,
  bed_end, open_days, ROUND(avg_beds,2) avg_beds, used_days, occ_days, disch_n,
  ROUND(CASE WHEN disch_n=0 THEN 0 ELSE 100*recover/disch_n END,2) cure_rate,
  ROUND(CASE WHEN disch_n=0 THEN 0 ELSE 100*effect/disch_n END,2) improve_rate,
  ROUND(CASE WHEN disch_n=0 THEN 0 ELSE 100*died/disch_n END,2) death_rate,
  ROUND(CASE WHEN avg_beds=0 THEN 0 ELSE disch_n/avg_beds END,2) turnover,
  CASE WHEN is_total=1 THEN ROUND(CASE WHEN avg_beds=0 THEN 0 ELSE used_days/avg_beds END,2) ELSE CASE WHEN avg_beds=0 THEN 0 ELSE used_days/avg_beds END END work_days,
  CASE WHEN open_days=0 THEN 0 ELSE used_days/open_days*100 END usage_rate,
  CASE WHEN is_total=1 THEN ROUND(CASE WHEN disch_n+trans_num=0 THEN 0 ELSE occ_days/(disch_n+trans_num) END,2) ELSE CASE WHEN disch_n+trans_num=0 THEN 0 ELSE occ_days/(disch_n+trans_num) END END avg_los_trans,
  CASE WHEN is_total=1 THEN ROUND(CASE WHEN disch_n=0 THEN 0 ELSE occ_days/disch_n END,2) ELSE CASE WHEN disch_n=0 THEN 0 ELSE occ_days/disch_n END END avg_los,
  (SELECT d1 FROM rng) stat_begin, (SELECT d2 FROM rng) stat_end
FROM r WHERE (SELECT over_limit FROM chk)=0 OR is_total=1 ORDER BY is_total, plsx, ks
