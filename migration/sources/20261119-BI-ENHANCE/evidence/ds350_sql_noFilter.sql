SELECT anon_1."出院" 
FROM (SELECT sum("DISCH_N") AS "出院" 
FROM (


WITH input_bounds AS (
  SELECT NVL(TRUNC(TO_DATE(NULL,'YYYY-MM-DD')), ADD_MONTHS(TRUNC(SYSDATE,'MM'),-1)) AS d1,
         NVL(CASE WHEN TO_DATE(NULL,'YYYY-MM-DD') = TRUNC(TO_DATE(NULL,'YYYY-MM-DD'))
                  THEN TRUNC(TO_DATE(NULL,'YYYY-MM-DD')) - 1
                  ELSE TRUNC(TO_DATE(NULL,'YYYY-MM-DD')) END,
             TRUNC(SYSDATE,'MM')-1) AS d2 FROM dual),
chk AS (SELECT CASE WHEN d2<d1 OR d2-d1+1>366 THEN 1 ELSE 0 END over_limit FROM input_bounds),
bnd AS (SELECT d1,d2 FROM input_bounds WHERE (SELECT over_limit FROM chk)=0),
rng AS (SELECT d1, d2, (d2-d1)+1 days FROM bnd),
cal AS (SELECT (SELECT d1 FROM rng) + LEVEL - 1 dd FROM dual CONNECT BY (SELECT d1 FROM rng) + LEVEL - 1 <= (SELECT d2 FROM rng)),
fx AS (SELECT stat_deptcode, start_date, ori_bednum, modify_date, modify_bednum FROM stat_ward_modifyfix),
bedday AS (SELECT f.stat_deptcode, c.dd,
             CASE WHEN f.modify_date IS NULL OR c.dd < f.modify_date THEN NVL(f.ori_bednum,0) ELSE NVL(f.modify_bednum,0) END beds
           FROM fx f JOIN cal c ON c.dd >= f.start_date
           WHERE NOT EXISTS (SELECT 1 FROM fx f2 WHERE f2.stat_deptcode=f.stat_deptcode
                              AND f2.start_date > f.start_date AND f2.start_date <= c.dd)),
beds AS (SELECT stat_deptcode ward, SUM(beds) open_days,
                 SUM(CASE WHEN dd=(SELECT d2 FROM rng) THEN beds ELSE 0 END) bed_end FROM bedday GROUP BY stat_deptcode),
flow AS (SELECT a.waed_code ward,
           SUM(NVL(a.discharge_disposition_recover,0)) recover,
           SUM(NVL(a.discharge_disposition_effect,0)) effect,
           SUM(NVL(a.discharge_disposition_invaled,0)) untreat,
           SUM(NVL(a.discharge_disposition_died,0)) died,
           SUM(NVL(a.discharge_disposition_other,0)) other_n,
           SUM(NVL(a.trans_waed_num,0)) trans_num,
           SUM(NVL(a.bed_used_num,0)) used_days,
           MAX(NVL(a.bed_used_num,0)) peak_num
         FROM waed_adt_day a
         WHERE a.st_date >= (SELECT d1 FROM rng) AND a.st_date <= (SELECT d2 FROM rng)
         GROUP BY a.waed_code),
dsc AS (SELECT t.ward_stayed ward,
          SUM(CASE WHEN TRUNC(t.discharge_date_time)=TRUNC(t.admission_date_time) THEN 1 ELSE TRUNC(t.discharge_date_time)-TRUNC(t.admission_date_time) END) occ_days
        FROM ward_transfer t JOIN pat_visit s ON s.patient_id=t.patient_id AND s.visit_id=t.visit_id
        WHERE s.discharge_date_time >= (SELECT d1 FROM rng) AND s.discharge_date_time < (SELECT d2 FROM rng)+1
          AND s.admission_cause <> '新生儿'
        GROUP BY t.ward_stayed),
spine AS (SELECT stat_deptcode ward, stat_deptname ward_name, plsx FROM stat_ward_modifyfix),
j AS (SELECT s.ward, s.ward_name, NVL(s.plsx,999999) plsx, (SELECT days FROM rng) days,
         NVL(b.bed_end,0) bed_end, NVL(b.open_days,0) open_days,
         NVL(f.recover,0) recover, NVL(f.effect,0) effect, NVL(f.untreat,0) untreat, NVL(f.died,0) died,
         NVL(f.other_n,0) other_n, NVL(f.trans_num,0) trans_num, NVL(f.used_days,0) used_days,
         NVL(f.peak_num,0) peak_num, NVL(d.occ_days,0) occ_days
       FROM spine s LEFT JOIN beds b ON b.ward=s.ward LEFT JOIN flow f ON f.ward=s.ward LEFT JOIN dsc d ON d.ward=s.ward),
x AS (SELECT ward, CASE WHEN ward IS NULL THEN '合计' ELSE ward_name END ks,
        CASE WHEN ward IS NULL THEN 1 ELSE 0 END is_total, plsx, MAX(days) days,
        SUM(bed_end) bed_end, SUM(open_days) open_days, SUM(used_days) used_days, SUM(peak_num) peak_num,
        SUM(occ_days) occ_days, SUM(trans_num) trans_num,
        SUM(recover) recover, SUM(effect) effect, SUM(untreat) untreat, SUM(died) died, SUM(other_n) other_n
      FROM j GROUP BY GROUPING SETS ((ward, ward_name, plsx, days), ())),
r AS (SELECT ward,ks, is_total, plsx, days, bed_end, open_days, used_days, peak_num, occ_days, trans_num,
        recover, effect, untreat, died, other_n, recover+effect+untreat+died+other_n disch_n,
        CASE WHEN open_days=0 OR days=0 THEN 0 ELSE open_days/days END avg_beds
      FROM x)
SELECT ward ward_code,CASE WHEN (SELECT over_limit FROM chk)=1 THEN '所选日期无效或超过366天，请缩小范围后重试' ELSE ks END ks, bed_end, open_days, ROUND(avg_beds,2) avg_beds, used_days, occ_days, disch_n,
  ROUND(CASE WHEN disch_n=0 THEN 0 ELSE 100*recover/disch_n END,2) cure_rate,
  ROUND(CASE WHEN disch_n=0 THEN 0 ELSE 100*effect/disch_n END,2) improve_rate,
  ROUND(CASE WHEN disch_n=0 THEN 0 ELSE 100*died/disch_n END,2) death_rate,
  ROUND(CASE WHEN avg_beds=0 THEN 0 ELSE disch_n/avg_beds END,2) turnover,
  CASE WHEN is_total=1 THEN ROUND(CASE WHEN avg_beds=0 THEN 0 ELSE used_days/avg_beds END,2) ELSE CASE WHEN avg_beds=0 THEN 0 ELSE used_days/avg_beds END END work_days,
  CASE WHEN open_days=0 THEN 0 ELSE used_days/open_days*100 END usage_rate,
  CASE WHEN is_total=1 THEN ROUND(CASE WHEN disch_n+trans_num=0 THEN 0 ELSE occ_days/(disch_n+trans_num) END,2) ELSE CASE WHEN disch_n+trans_num=0 THEN 0 ELSE occ_days/(disch_n+trans_num) END END avg_los_trans,
  CASE WHEN is_total=1 THEN ROUND(CASE WHEN disch_n=0 THEN 0 ELSE occ_days/disch_n END,2) ELSE CASE WHEN disch_n=0 THEN 0 ELSE occ_days/disch_n END END avg_los,
  CASE WHEN days=0 THEN 0 ELSE ROUND(used_days/days,2) END avg_inpat,
  peak_num,
  (SELECT d1 FROM rng) stat_begin, (SELECT d2 FROM rng) stat_end
FROM r WHERE (SELECT over_limit FROM chk)=0 OR is_total=1 ORDER BY is_total, plsx, ks
) virtual_table) anon_1 
WHERE ROWNUM <= 5;

