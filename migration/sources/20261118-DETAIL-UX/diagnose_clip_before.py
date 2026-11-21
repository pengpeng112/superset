# -*- coding: utf-8 -*-
"""阶段0：真机 DOM 几何裁剪取证（修复前基线，2026-11-17）。

Chrome × {1366x768, 1920x1080}，admin 登录访问 5 个代表页：
  36（常规 DataTable）65（抗菌办宽表）39（pivot_table_v2）32（月报自绘 hm-scroll）72（BI 对照组）
数据加载完成后采集 [data-test="grid-content"] 往下每一层
（grid-row / resizable-container / chart-holder / chart-container / slice_container /
 superset-chart-table / frame / scroll / table / pagination / pvtTable / hm-scroll）
的 tagName/className/clientHeight/scrollHeight/rect.top/rect.bottom/overflow，
并记录外层页面溢出、末行/分页器/横向滚动条被裁切的像素值。
输出 evidence/clip_before.json。凭据经环境变量 DIAG_USER/DIAG_PW 注入。
"""
import json
import os
import subprocess
import sys
import time

import urllib.request
import websocket

sys.path.insert(0, r"F:\python\superset\migration\sources\20261112-WARMUP-PERF")
from wb_run import Tab, new_tab  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "http://127.0.0.1:18180"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PAGES = [
    ("36", "常规 DataTable 明细/汇总页"),
    ("65", "抗菌办宽字段分页大明细表"),
    ("39", "pivot_table_v2 透视表页"),
    ("32", "monthly-report 自绘月报页"),
    ("72", "多图表 BI 驾驶舱对照组"),
]
WAIT_MAX = {"36": 75, "65": 120, "39": 120, "32": 75, "72": 75}

PROBE = r"""(function(){
  function info(el){
    if(!el)return null;
    var r=el.getBoundingClientRect(),s=getComputedStyle(el);
    return {tag:el.tagName.toLowerCase(),cls:String(el.getAttribute('class')||'').slice(0,110),
      h:Math.round(r.height),top:Math.round(r.top),bottom:Math.round(r.bottom),right:Math.round(r.right),
      clientH:el.clientHeight,scrollH:el.scrollHeight,clientW:el.clientWidth,scrollW:el.scrollWidth,
      ov:s.overflowX+'/'+s.overflowY,pos:s.position};
  }
  var se=document.scrollingElement||document.documentElement;
  var out={path:location.pathname,ts:Date.now(),
    innerW:window.innerWidth,innerH:window.innerHeight,
    docScrollH:se.scrollHeight,docClientH:se.clientHeight,docScrollTop:se.scrollTop,
    pageOverflowPx:se.scrollHeight-window.innerHeight,
    htmlCls:String(document.documentElement.getAttribute('class')||''),
    uiVer:(window.hospitalReportUI||{}).version||'',
    header:null,filterBar:null,markdown:null,grid:null,gridAncestors:[],holders:[]};
  out.header=info(document.querySelector('header'));
  out.filterBar=info(document.querySelector('[data-test="filter-bar"]'));
  out.markdown=info(document.querySelector('.dashboard-markdown'));
  var grid=document.querySelector('[data-test="grid-content"]');
  out.grid=info(grid);
  var a=grid;
  while(a&&a!==document.body){a=a.parentElement;if(a&&a!==document.body)out.gridAncestors.push(info(a));}
  var hs=document.querySelectorAll('.dashboard-component-chart-holder');
  for(var i=0;i<hs.length;i++){
    var h=hs[i];
    var rec={main:/(^|\s)dashboard-chart-id-/.test(String(h.getAttribute('class')||'')),
      self:info(h),sliceHeader:info(h.querySelector('[data-test="slice-header"]')),
      chart:info(h.querySelector('.chart-container')),slice:info(h.querySelector('.slice_container')),
      toolbar:info(h.querySelector('.hh-query-toolbar')),banner:info(h.querySelector('.hh-truncation-banner')),
      controls:info(h.querySelector('.dt-controls')),table:info(h.querySelector('table')),
      pagination:info(h.querySelector('.pagination')),pvt:info(h.querySelector('.pvtTable')),
      pvtWrap:info(h.querySelector('.pvtTable')?h.querySelector('.pvtTable').parentElement:null),
      empty:!!h.querySelector('.ant-empty'),chain:[]};
    var st=h.querySelector('.superset-chart-table');
    if(st){
      var n=st;rec.chain.push(info(n));
      var guard=0;
      while(n&&n.tagName!=='TABLE'&&guard<12){
        var kids=n.children,next=null;
        for(var k=0;k<kids.length;k++){
          if(kids[k].tagName==='TABLE'||kids[k].querySelector('table')){next=kids[k];break;}
        }
        if(!next)break;
        n=next;rec.chain.push(info(n));guard++;
      }
      var tb=st.querySelector('table');
      rec.scroll=info(tb?tb.parentElement:null);
      rec.frame=info(tb?tb.parentElement.parentElement:null);
      rec.wrapper=info(tb?tb.parentElement.parentElement.parentElement:null);
      var tbody=st.querySelector('tbody');
      var lr=tbody&&tbody.rows[tbody.rows.length-1];
      rec.lastRow=info(lr);
      rec.rows=tbody?tbody.rows.length:0;
      if(tb&&rec.scroll){
        rec.clip={lastRowBelowScroll:rec.lastRow?(rec.lastRow.bottom-rec.scroll.bottom):null,
          holderBelowViewport:rec.self.bottom-window.innerHeight,
          scrollBottomBelowViewport:rec.scroll.bottom-window.innerHeight,
          hscrollVisible:rec.scroll.scrollW>rec.scroll.clientW,
          hscrollBelowViewport:rec.scroll.bottom-window.innerHeight};
      }
    }
    out.holders.push(rec);
  }
  out.hm=info(document.getElementById('hospital-monthly-report'));
  out.hmScroll=info(document.querySelector('#hospital-monthly-report .hm-scroll'));
  out.hmFooter=info(document.querySelector('#hospital-monthly-report .hm-footer'));
  return JSON.stringify(out);
})()"""

READY = r"""(function(){
  var hs=document.querySelectorAll('.dashboard-component-chart-holder[class*="dashboard-chart-id-"]');
  if(!hs.length)return false;
  var ok=0;
  for(var i=0;i<hs.length;i++){
    var h=hs[i];
    if(h.querySelector('#hospital-monthly-report, table, svg, canvas, .ant-empty'))ok++;
  }
  return ok>=hs.length;
})()"""


def launch(tag, w, h, port):
    profile = os.path.join(HERE, "profile-diag18-%s" % tag)
    proc = subprocess.Popen([
        CHROME, "--remote-debugging-port=%d" % port, "--user-data-dir=%s" % profile,
        "--no-first-run", "--no-default-browser-check", "--disable-session-crashed-bubble",
        "--window-size=%d,%d" % (w, h), "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ver = ""
    for _ in range(60):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port, timeout=5) as r:
                ver = json.loads(r.read().decode()).get("Browser", "")
            if ver:
                break
        except Exception:
            time.sleep(0.5)
    return proc, ver


def main():
    user = os.environ.get("DIAG_USER", "admin")
    pw = os.environ.get("DIAG_PW", "")
    results = {"meta": {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "phase": "before",
                        "uiVer": "20261108f13", "pages": dict((p[0], p[1]) for p in PAGES)},
               "runs": []}
    port = 19410
    for (w, h) in [(1366, 768), (1920, 1080)]:
        tag = "%dx%d" % (w, h)
        proc, ver = launch(tag, w, h, port)
        info = new_tab(port)
        ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=30)
        tab = Tab(ws)
        tab.send("Page.enable")
        login_ok = tab.login(user, pw)
        run = {"viewport": tag, "browser": ver, "login": login_ok, "pages": {}}
        for pid, pdesc in PAGES:
            tab.send("Page.navigate", {"url": BASE + "/superset/dashboard/%s/" % pid})
            time.sleep(2.0)
            for _ in range(60):
                if tab.eval("document.readyState") == "complete":
                    break
                time.sleep(0.5)
            deadline = time.time() + WAIT_MAX[pid]
            ready = False
            while time.time() < deadline:
                try:
                    if tab.eval(READY):
                        ready = True
                        break
                except Exception:
                    pass
                time.sleep(2.0)
            time.sleep(3.0)  # 等 fitTables/工具条稳定
            try:
                data = json.loads(tab.eval(PROBE))
                data["ready"] = ready
                data["desc"] = pdesc
                run["pages"][pid] = data
            except Exception as e:
                run["pages"][pid] = {"error": str(e), "ready": ready, "desc": pdesc}
            print("[%s] page %s ready=%s" % (tag, pid, ready), flush=True)
        run["pages"]["_order"] = [p[0] for p in PAGES]
        results["runs"].append(run)
        ws.close()
        proc.terminate()
        try:
            proc.wait(10)
        except Exception:
            proc.kill()
        time.sleep(2)
    out = os.path.join(HERE, "evidence", "clip_before.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print("saved", out, flush=True)


if __name__ == "__main__":
    main()
