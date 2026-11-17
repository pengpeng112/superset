#!/bin/bash
# 20261106-CHINESE-TABLEUI 只读扫描：在用查询页(32,35-70)数据集的未汉化列 + 全库已汉化列参考映射。
# 只读 SELECT，不改任何数据。输出 JSON 到 /tmp/ct_scan*.json（列名与译名为元数据，可出服务器）。
set -e
q(){ docker exec superset-postgres psql -U superset -d superset -At -c "$1"; }

# 1) 在用查询页挂载的图表与数据集（32,35-70）
q "select distinct dsl.dashboard_id, s.id as slice_id, s.slice_name, s.datasource_id, t.table_name
   from dashboards ds
   join dashboard_slices dsl on dsl.dashboard_id=ds.id
   join slices s on s.id=dsl.slice_id
   join tables t on t.id=s.datasource_id and s.datasource_type='table'
   where ds.id=32 or (ds.id>=35 and ds.id<=70)
   order by dsl.dashboard_id, s.id" > /tmp/ct_scan_pages.tsv

# 2) 这些数据集中未汉化列（verbose_name 空 或 =column_name，且列名含英文字母；排除保护数据集 3-12/166/171/176）
q "select tc.table_id, t.table_name, tc.id as column_id, tc.column_name, tc.is_dttm::text, tc.groupby::text, tc.filterable::text, coalesce(tc.verbose_name,''), tc.type
   from table_columns tc
   join tables t on t.id=tc.table_id
   where t.id in (select distinct s.datasource_id from dashboards ds
                  join dashboard_slices dsl on dsl.dashboard_id=ds.id
                  join slices s on s.id=dsl.slice_id
                  where s.datasource_type='table' and (ds.id=32 or (ds.id>=35 and ds.id<=70)))
     and t.id not in (3,4,5,6,7,8,9,10,11,12,166,171,176)
     and tc.column_name ~ '[A-Za-z]'
     and (coalesce(tc.verbose_name,'')='' or tc.verbose_name=tc.column_name)
   order by tc.table_id, tc.id" > /tmp/ct_scan_untranslated.tsv

# 3) 全库已汉化参考：column_name≠verbose_name 且两者非空、列名含英文字母（同名物理列的既有中文译名）
q "select tc.column_name, tc.verbose_name, count(distinct tc.table_id) as n_tables
   from table_columns tc
   where coalesce(tc.verbose_name,'')<>'' and tc.verbose_name<>tc.column_name and tc.column_name ~ '[A-Za-z]'
   group by tc.column_name, tc.verbose_name
   order by tc.column_name, n_tables desc" > /tmp/ct_scan_reference.tsv

# 4) 数据集清单（供映射分组）
q "select t.id, t.table_name, count(tc.id) filter (where tc.column_name ~ '[A-Za-z]' and (coalesce(tc.verbose_name,'')='' or tc.verbose_name=tc.column_name)) as untranslated_n
   from tables t join table_columns tc on tc.table_id=t.id
   where t.id in (select distinct s.datasource_id from dashboards ds
                  join dashboard_slices dsl on dsl.dashboard_id=ds.id
                  join slices s on s.id=dsl.slice_id
                  where s.datasource_type='table' and (ds.id=32 or (ds.id>=35 and ds.id<=70)))
   group by t.id, t.table_name order by t.id" > /tmp/ct_scan_datasets.tsv

wc -l /tmp/ct_scan_pages.tsv /tmp/ct_scan_untranslated.tsv /tmp/ct_scan_reference.tsv /tmp/ct_scan_datasets.tsv
echo SCAN-DONE
