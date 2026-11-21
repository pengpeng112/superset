# -*- coding: utf-8 -*-
"""Page.addScriptToEvaluateOnNewDocument 注入 fetch hook，抓 373 真实请求 body 与响应值。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_rbac_frontend_polish as V

HOOK = r"""(function(){
  window.__cap373=[];
  var orig=window.fetch?window.fetch.bind(window):null;
  if(!orig)return;
  window.fetch=function(input,init){
    try{
      var url=typeof input==='string'?input:((input&&input.url)||'');
      if(init&&String(init.method||'').toUpperCase()==='POST'&&url.indexOf('/api/v1/chart/data')>=0&&typeof init.body==='string'){
        var b=JSON.parse(init.body);
        var sid=(b.form_data||{}).slice_id;
        if(sid===373){
          var rec={tr:b.queries&&b.queries[0]?b.queries[0].time_range:null,
                   ds:b.datasource,
                   where:b.queries&&b.queries[0]?b.queries[0].extras&&b.queries[0].extras.where:null,
                   url:url.slice(0,90)};
          window.__cap373.push(rec);
          var p=orig(input,init);
          return p.then(function(r){
            var cl=r.clone();
            cl.json().then(function(j){
              var res=(j.result||[{}])[0];
              rec.resp=JSON.stringify(res.data);
              rec.cached=res.is_cached;
            }).catch(function(){});
            return r;
          });
        }
      }
    }catch(e){}
    return orig(input,init);
  };
})()"""


def main():
    s = V.Session("chrome", V.CHROME, 1920, 1080, "diag-hook")
    try:
        assert s.tab.login("admin", V.ADMIN_PW)
        s.tab.send("Page.addScriptToEvaluateOnNewDocument", {"source": HOOK})
        s.open(V.BASE + "/superset/dashboard/72/", 12.0)
        for _ in range(8):
            if s.tab.eval("!!document.querySelector('[data-test=\"grid-content\"]')"):
                break
            time.sleep(4)
        time.sleep(10)
        caps = s.tab.eval("JSON.stringify(window.__cap373||[])")
        print("captured 373 requests:", caps)
    finally:
        s.close()


if __name__ == "__main__":
    main()
