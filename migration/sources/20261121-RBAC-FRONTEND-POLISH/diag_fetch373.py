# -*- coding: utf-8 -*-
"""浏览器内 fetch 复现：带窗 vs No filter 的 373 查询，读各返回值 + 抓页面真实 POST。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_rbac_frontend_polish as V

FETCH_TEST = r"""(function(){
  function mk(tr){
    return {datasource:'348__table',force:false,
      queries:[{time_range:tr,granularity:'STAT_BEGIN',filters:[],
        extras:{having:'',where:''},applied_time_extras:{},columns:[],
        metrics:[{expressionType:'SIMPLE',column:{column_name:'EXIT_N'},aggregate:'SUM',label:'住院出院总人数',hasCustomLabel:true}],
        annotation_layers:{},series_limit:0,order_desc:true,url_params:{},custom_params:{},custom_form_data:{}}],
      form_data:{datasource:'348__table',viz_type:'big_number_total',slice_id:373,url_params:{},time_range:tr},
      result_format:'json',result_type:'full'};
  }
  function post(tr){
    return fetch('/api/v1/chart/data?form_data=%7B%22slice_id%22%3A373%7D&dashboard_id=72',
      {method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},
       body:JSON.stringify(mk(tr))})
      .then(function(r){return r.json();})
      .then(function(j){var res=(j.result||[{}])[0];
        return tr+' -> '+JSON.stringify(res.data)+' cached='+res.is_cached;})
      .catch(function(e){return tr+' ERR '+e.message;});
  }
  var csrf=document.cookie.match(/(?:^|;\s*)(?:csrf_token|csrftoken)=([^;]+)/);
  var H={};
  if(csrf)H['X-CSRFToken']=decodeURIComponent(csrf[1]);
  window.__f1=post('2026-10-01 : 2026-11-01');
  window.__f2=post('No filter');
  return 'started';
})()"""


def main():
    s = V.Session("chrome", V.CHROME, 1920, 1080, "diag-fetch")
    posts = []
    try:
        assert s.tab.login("admin", V.ADMIN_PW)
        s.open(V.BASE + "/superset/dashboard/72/", 10.0)
        s.tab.eval(FETCH_TEST)
        time.sleep(8)
        print("fetch OCT:", s.tab.eval("window.__f1"))
        print("fetch ALL:", s.tab.eval("window.__f2"))
        kpi = s.tab.eval("(function(){var h=document.querySelector('.dashboard-chart-id-373');return h?(h.textContent||'').replace(/\\s+/g,' ').slice(0,40):'';})()")
        print("KPI on page:", kpi)
    finally:
        s.close()


if __name__ == "__main__":
    main()
