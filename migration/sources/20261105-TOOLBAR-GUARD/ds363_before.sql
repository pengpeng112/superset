{% set tf = get_time_filter('开单日期T', strftime='%Y-%m-%d', remove_filter=True) %}
{% set tf_s = "'" + tf.from_expr + "'" if tf.from_expr else 'NULL' %}
{% set tf_e = "'" + tf.to_expr + "'" if tf.to_expr else 'NULL' %}
SELECT
  a."处方编号",
  a."患者唯一标识",
  a."患者就诊唯一标识",
  a."性别",
  a."出生日期",
  a."特殊人群",
  a."身高(cm)" AS "身高（cm）",
  a."体重(kg)" AS "体重（kg）",
  a."处方开立日期",
  a."患者就诊类型",
  a."处方开立科室名称",
  a."处方开立科室代码",
  a."诊断",
  a."描述性诊断",
  a."处方金额（元）",
  a."药品编码",
  a."药物名称",
  a."剂型",
  a."规格",
  a."包装",
  a."给药途径",
  a."给药频率",
  a."单次剂量",
  a."单次剂量单位",
  a."发药数量",
  a."发药数量单位",
  a."药品分组",
  a."药品金额（元）",
  a."用药条件",
  a."用药天数",
  a."是否过敏试验",
  a."过敏试验结果",
  TO_DATE(a."处方开立日期", 'YYYY-MM-DD') AS "开单日期T"
FROM FXHIS.V_kjyw_OUTP_PRESC a
WHERE TO_DATE(a."处方开立日期", 'YYYY-MM-DD') >= NVL(TO_DATE({{ tf_s }}, 'YYYY-MM-DD'), TRUNC(ADD_MONTHS(SYSDATE, -1), 'MM'))
  AND TO_DATE(a."处方开立日期", 'YYYY-MM-DD') <  NVL(TO_DATE({{ tf_e }}, 'YYYY-MM-DD'), TRUNC(SYSDATE, 'MM'))
