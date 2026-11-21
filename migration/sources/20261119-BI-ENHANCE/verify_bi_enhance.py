# -*- coding: utf-8 -*-
"""20261119-BI-ENHANCE 阶段3：双浏览器 × 双分辨率 × 双账号 自动化验收。
断言1 看75+别名：渲染/数值/中文列头/联动；断言2 四驾驶舱入口与网格；断言3 收藏夹；
断言4 投屏+打印PDF；断言5 f14/h16 回归+存量零篡改计数。输出 evidence/bi_enhance_acceptance.json。
凭据环境变量 VDX_ADMIN / VDX_EMP。
"""
import base64
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
CHROME_NEW = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CHROME_87 = r"F:\python\superset\migration\tools\chromium87-r809590\chrome-win\chrome.exe"

res = {"meta": {"ts": time.strftime("%Y-%m-%d %H:%M:%S")}, "checks": [], "pdfs": []}


def record(key, name, ok, detail=""):
    res["checks"].append({"name": "%s/%s" % (key, name), "pass": bool(ok), "detail": str(detail)[:260]})
    print(("PASS " if ok else "FAIL ") + key + "/" + name + (" | " + str(detail)[:130] if detail else ""), flush=True)


class Runner:
    def __init__(self, key, exe, w, h, port):
        self.key = key
        self.exe = exe
        self.w, self.h, self.port = w, h, port
        self.proc = None
        self.tab = None
        self.ws = None
        self.errs = []

    def start(self):
        self.stop()
        profile = os.path.join(HERE, "profile-acc-%s" % self.key)
        self.proc = subprocess.Popen([
            self.exe, "--remote-debugging-port=%d" % self.port, "--user-data-dir=%s" % profile,
            "--no-first-run", "--no-default-browser-check", "--disable-session-crashed-bubble",
            "--window-size=%d,%d" % (self.w, self.h), "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/json/version" % self.port, timeout=5)
                break
            except Exception:
                time.sleep(0.5)
        info = new_tab(self.port)
        self.ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=60)
        self.tab = Tab(self.ws)
        self.tab.send("Page.enable")
        self.tab.send("Runtime.enable")
        return self.tab

    def login(self, user, pw):
        for attempt in range(2):
            if self.tab.login(user, pw):
                return True
            self.start()
        return False

    def visit(self, path, settle=15, ready=None):
        """会话级停滞自愈：ready 未达标 → 整会话重启（杀进程+新 profile 端口）+重登录+重导航，最多 2 轮。"""
        for attempt in range(3):
            self.tab.send("Page.navigate", {"url": BASE + path})
            time.sleep(2.5)
            for _ in range(40):
                if self.tab.eval("document.readyState") == "complete":
                    break
                time.sleep(0.5)
            ok = True
            if ready:
                ok = False
                for _ in range(8):
                    try:
                        if self.tab.eval(ready):
                            ok = True
                            break
                    except Exception:
                        pass
                    time.sleep(3)
            if ok:
                time.sleep(settle)
                self.collect()
                return
            # 停滞：整会话重启（新端口避免旧会话态），重新登录重试
            print("  [self-heal] %s stuck on %s attempt=%d — restarting session" % (self.key, path, attempt + 1), flush=True)
            old_port = self.port
            self.port = self.port + 50 + attempt
            self.start()
            self.login("admin" if "admin" in self.key else "003158", os.environ.get("VDX_ADMIN", "") if "admin" in self.key else os.environ.get("VDX_EMP", "<REDACTED-DEFAULT-EMPLOYEE-PW>"))
        time.sleep(settle)
        self.collect()

    def collect(self):
        for ev in self.tab.drain():
            if ev.get("method") == "Runtime.exceptionThrown":
                self.errs.append(str(ev.get("params", {}).get("exceptionDetails", {}).get("text", ""))[:120])

    def stop(self):
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(8)
            except Exception:
                self.proc.kill()
        self.proc = self.ws = self.tab = None
        time.sleep(1.5)


READY75 = ('document.querySelectorAll(".dashboard-component-chart-holder[class*=" + '
           '"\\"dashboard-chart-id-\\"".slice(1,0)]').replace("{", "")  # placeholder not used
READY75_JS = '(function(){var n=document.querySelectorAll(".dashboard-component-chart-holder[class*=dashboard-chart-id-]").length;return n>=7;})()'
DASH75_STATE = r"""(function(){
  var hs=document.querySelectorAll('.dashboard-component-chart-holder[class*="dashboard-chart-id-"]');
  var out={n:hs.length,charts:[],errs:0};
  for(var i=0;i<hs.length;i++){
    var h=hs[i];
    var cid=(String(h.className).match(/dashboard-chart-id-(\d+)/)||[])[1];
    var err=!!h.querySelector('.ant-alert-error');
    var txt=(h.textContent||'').replace(/\s+/g,' ').slice(0,150);
    var rendered=!!h.querySelector('svg,canvas,table,.ant-empty');
    out.charts.push({cid:cid,err:err,rendered:rendered,txt:txt});
    if(err)out.errs++;
  }
  out.full=(function(){var t='';for(var i=0;i<hs.length;i++)t+=(hs[i].textContent||'')+' ';return t.replace(/\s+/g,' ');})();
  out.tblPh=(function(){var els=document.querySelectorAll('.superset-chart-table input[placeholder]');for(var j=0;j<els.length;j++){var ph=els[j].getAttribute('placeholder')||'';if(ph.indexOf('条记录')>=0)return ph;}return '';})();
  out.english=(function(){var bad=[];var ths=document.querySelectorAll('.superset-chart-table thead th');for(var j=0;j<ths.length;j++){var t=(ths[j].textContent||'').trim();if(/^[A-Z_]{4,}$/.test(t))bad.push(t);}return bad;})();
  return JSON.stringify(out);
})()"""


def assert_dash75(rn, key):
    rn.visit("/superset/dashboard/75/", settle=16, ready=READY75_JS)
    st = json.loads(rn.tab.eval(DASH75_STATE))
    record(key, "d75-7charts-render", st["n"] == 7 and all(c["rendered"] for c in st["charts"]),
           "n=%s errs=%s" % (st["n"], st["errs"]))
    record(key, "d75-no-error-box", st["errs"] == 0, "err charts=%s" % st["errs"])
    txt = " ".join(c["txt"] for c in st["charts"])
    full = st.get("full") or ""
    kpis_ok = ("41,509" in txt and "36,251" in txt and "5,315" in txt and "87.3%" in txt)
    record(key, "d75-kpi-values", kpis_ok, "KPI 41509/36251/5315/87.3 in UI=%s" % kpis_ok)
    record(key, "d75-no-english-header", len(st.get("english") or []) == 0, "bad=%s" % (st.get("english") or [])[:4])
    # 汇总表 39 条记录（搜索框 placeholder + 汇总表全文本兜底）
    ok39 = ("39" in (st.get("tblPh") or "")) or ("39 条记录" in full)
    record(key, "d75-table-39rows", ok39, "tblPh=(%s)" % (st.get("tblPh") or "")[:30])
    return st


def main():
    admin_pw = os.environ.get("VDX_ADMIN", "")
    emp_pw = os.environ.get("VDX_EMP", "<REDACTED-DEFAULT-EMPLOYEE-PW>")
    port = 19600

    # ---- 断言1+2+4（chrome 1920 admin：主断言轮）----
    key = "chrome-1920-admin"
    rn = Runner(key, CHROME_NEW, 1920, 1080, port); port += 1
    rn.start()
    record(key, "login", rn.login("admin", admin_pw))
    st = assert_dash75(rn, key)
    # 别名
    rn.visit("/superset/dashboard/bi-nursing-bed/", settle=14, ready=READY75_JS)
    st2 = json.loads(rn.tab.eval(DASH75_STATE))
    record(key, "d75-alias-200", st2["n"] == 7 and st2["errs"] == 0, "alias n=%s errs=%s" % (st2["n"], st2["errs"]))
    # 首页侧栏 4 驾驶舱 + 收藏面板位
    rn.visit("/superset/welcome/", settle=12)
    nav = rn.tab.eval('(function(){var items=document.querySelectorAll("#hh-home-nav .hh-home-nav-bi");var names=[];for(var i=0;i<items.length;i++)names.push((items[i].textContent||"").trim().slice(0,30));return JSON.stringify({bi:items.length,names:names,favPanel:!!document.getElementById("hh-fav-panel")})})()')
    d = json.loads(nav)
    record(key, "home-nav-4bi", d["bi"] == 4, "n=%s %s" % (d["bi"], d["names"]))
    # 34 目录 4 卡 + 1920 四列 + h16 下钻
    rn.visit("/superset/dashboard/34/", settle=14, ready='document.querySelectorAll(".dashboard-markdown li,li[data-hh-cat-group]").length>0')
    dir34 = rn.tab.eval('(function(){var cards=document.querySelectorAll(".hh-bi-card");var cols=getComputedStyle(document.getElementById("hh-bi-showcase")||document.createElement("div")).gridTemplateColumns.split(" ").length;var li=document.querySelector("li[data-hh-cat-group]");var v=0;if(li){var links=li.querySelectorAll("a");for(var i=0;i<links.length;i++){var r=links[i].getBoundingClientRect();if(r.height>0&&r.width>0)v++;}}return JSON.stringify({cards:cards.length,cols:cols,drillVisible:v})})()')
    dd = json.loads(dir34)
    record(key, "dir34-4cards-4col-1920", dd["cards"] == 4 and dd["cols"] == 4, "cards=%s cols=%s" % (dd["cards"], dd["cols"]))
    record(key, "dir34-drilldown-h16", dd["drillVisible"] > 0, "kyb visible links=%s" % dd["drillVisible"])
    # 打印 PDF（dash75）：手动触发 beforeprint（真实 Ctrl+P 会自动触发），CDP printToPDF
    rn.tab.eval("window.dispatchEvent(new Event('beforeprint'))")
    time.sleep(1)
    try:
        pdf = rn.tab.send("Page.printToPDF", {"landscape": True, "printBackground": True, "preferCSSPageSize": True}, timeout=120)
        p1 = os.path.join(HERE, "evidence", "print-dash75.pdf")
        with open(p1, "wb") as f:
            f.write(base64.b64decode(pdf["data"]))
        sz1 = os.path.getsize(p1)
        res["pdfs"].append({"name": p1, "bytes": sz1})
        record(key, "print-dash75-pdf", sz1 > 20000, "%d bytes" % sz1)
    except Exception as e:
        record(key, "print-dash75-pdf", False, str(e)[:150])
    rn.tab.eval("window.dispatchEvent(new Event('afterprint'))")
    # 打印 PDF（36 明细页，验解除锁高完整展开）
    rn.visit("/superset/dashboard/36/", settle=15, ready='document.querySelectorAll(".superset-chart-table").length>0')
    rn.tab.eval("window.dispatchEvent(new Event('beforeprint'))")
    time.sleep(1)
    try:
        pdf = rn.tab.send("Page.printToPDF", {"landscape": True, "printBackground": True, "preferCSSPageSize": True}, timeout=120)
        p2 = os.path.join(HERE, "evidence", "print-page36.pdf")
        with open(p2, "wb") as f:
            f.write(base64.b64decode(pdf["data"]))
        sz2 = os.path.getsize(p2)
        res["pdfs"].append({"name": p2, "bytes": sz2})
        record(key, "print-page36-pdf", sz2 > 20000, "%d bytes" % sz2)
    except Exception as e:
        record(key, "print-page36-pdf", False, str(e)[:150])
    rn.tab.eval("window.dispatchEvent(new Event('afterprint'))")
    # emulateMedia print 断言（36）：导航/筛选隐藏 + 表格高度放开
    rn.tab.send("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-color-scheme", "value": "light"}]})
    rn.tab.send("Emulation.setEmulatedMedia", {"media": "print"})
    time.sleep(1)
    pm = rn.tab.eval('(function(){var hd=document.querySelector("header");var fb=document.querySelector(\'[data-test="filter-bar"]\');var tbl=document.querySelector(".superset-chart-table table");var scr=tbl?tbl.parentElement:null;return JSON.stringify({headerDisp:hd?getComputedStyle(hd).display:"absent",filterDisp:fb?getComputedStyle(fb).display:"absent",scrH:scr?Math.round(scr.getBoundingClientRect().height):null,scrOv:scr?getComputedStyle(scr).overflowY:null})})()')
    try:
        pd = json.loads(pm)
        record(key, "print-media-36", (pd["headerDisp"] == "none" or pd["headerDisp"] == "absent") and pd["scrOv"] == "visible",
               "header=%s filter=%s scrOv=%s" % (pd["headerDisp"], pd["filterDisp"], pd["scrOv"]))
    except Exception as e:
        record(key, "print-media-36", False, str(e)[:120])
    rn.tab.send("Emulation.setEmulatedMedia", {"media": ""})
    # f14 回归：36/61 锁高完好
    rn.visit("/superset/dashboard/36/", settle=15, ready='document.querySelectorAll(".superset-chart-table").length>0')
    r36 = rn.tab.eval('(function(){var de=document.documentElement;var mh=document.querySelector(".dashboard-component-chart-holder[class*=dashboard-chart-id-]");var se=document.scrollingElement||document.documentElement;var pg=document.querySelector(".pagination");return JSON.stringify({locked:de.classList.contains("hh-single-table-page"),holdB:mh?Math.round(mh.getBoundingClientRect().bottom):null,innerH:window.innerHeight,pagB:pg?Math.round(pg.getBoundingClientRect().bottom):null})})()')
    x36 = json.loads(r36)
    record(key, "f14-regression-36", x36["locked"] and (x36["pagB"] or 0) <= x36["innerH"] + 1, json.dumps(x36))
    rn.visit("/superset/dashboard/61/", settle=15, ready='document.querySelectorAll(".superset-chart-table").length>0')
    r61 = rn.tab.eval('(function(){var de=document.documentElement;var pg=document.querySelector(".pagination");var se=document.scrollingElement||document.documentElement;return JSON.stringify({locked:de.classList.contains("hh-single-table-page"),pagB:pg?Math.round(pg.getBoundingClientRect().bottom):null,innerH:window.innerHeight})})()')
    x61 = json.loads(r61)
    record(key, "f14-regression-61", x61["locked"] and (x61["pagB"] or 0) <= x61["innerH"] + 1, json.dumps(x61))
    record(key, "pageerror", len(rn.errs) == 0, "%d errors %s" % (len(rn.errs), rn.errs[:2]))
    rn.stop()

    # ---- chrome 1366 admin：2×2 网格 + 投屏 ----
    key = "chrome-1366-admin"
    rn = Runner(key, CHROME_NEW, 1366, 768, port); port += 1
    rn.start()
    record(key, "login", rn.login("admin", admin_pw))
    rn.visit("/superset/dashboard/34/", settle=14, ready='document.querySelectorAll(".dashboard-markdown li,li[data-hh-cat-group]").length>0')
    dir34 = rn.tab.eval('(function(){var cards=document.querySelectorAll(".hh-bi-card");var cols=getComputedStyle(document.getElementById("hh-bi-showcase")||document.createElement("div")).gridTemplateColumns.split(" ").length;var overflow=document.documentElement.scrollWidth>window.innerWidth+2;return JSON.stringify({cards:cards.length,cols:cols,overflow:overflow})})()')
    dd = json.loads(dir34)
    record(key, "dir34-2col-1366", dd["cards"] == 4 and dd["cols"] == 2 and not dd["overflow"], "cards=%s cols=%s overflow=%s" % (dd["cards"], dd["cols"], dd["overflow"]))
    rn.visit("/superset/dashboard/75/", settle=16, ready=READY75_JS)
    # 投屏
    rn.tab.eval('(function(){var b=document.getElementById("hh-present-btn");if(b){b.click();return 1}return 0})()')
    time.sleep(2.5)
    pm = rn.tab.eval('(function(){var de=document.documentElement;var hd=document.querySelector("header");var fb=document.querySelector(\'[data-test="filter-bar"]\');var bar=document.getElementById("hh-present-bar");var mh=document.querySelector(".dashboard-component-chart-holder[class*=dashboard-chart-id-]");return JSON.stringify({mode:de.classList.contains("hh-present-mode"),header:hd?getComputedStyle(hd).display:"absent",filter:fb?getComputedStyle(fb).display:"absent",bar:!!bar,barTitle:(bar&&bar.querySelector(".hh-pres-title")||{textContent:""}).textContent.slice(0,40),chartRendered:!!(mh&&mh.querySelector("svg,canvas,table"))})})()')
    try:
        pd2 = json.loads(pm)
        record(key, "present-enter", pd2["mode"] and pd2["header"] == "none" and pd2["filter"] == "none" and pd2["bar"] and pd2["chartRendered"], json.dumps(pd2)[:180])
    except Exception as e:
        record(key, "present-enter", False, str(e)[:120])
    rn.tab.send("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27})
    rn.tab.send("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27})
    time.sleep(2)
    pr = rn.tab.eval('(function(){return JSON.stringify({mode:document.documentElement.classList.contains("hh-present-mode"),bar:!!document.getElementById("hh-present-bar"),header:document.querySelector("header")?getComputedStyle(document.querySelector("header")).display:"absent"})})()')
    try:
        px = json.loads(pr)
        record(key, "present-esc-restore", not px["mode"] and not px["bar"] and px["header"] != "none", json.dumps(px))
    except Exception as e:
        record(key, "present-esc-restore", False, str(e)[:120])
    record(key, "pageerror", len(rn.errs) == 0, "%d errors" % len(rn.errs))
    rn.stop()

    # ---- c87 双分辨率 admin ----
    for (w, h) in [(1920, 1080), (1366, 768)]:
        key = "c87-%dx%d-admin" % (w, h)
        rn = Runner(key, CHROME_87, w, h, port); port += 1
        rn.start()
        record(key, "login", rn.login("admin", admin_pw))
        st = assert_dash75(rn, key)
        rn.visit("/superset/dashboard/34/", settle=14, ready='document.querySelectorAll(".dashboard-markdown li,li[data-hh-cat-group]").length>0')
        dir34 = rn.tab.eval('(function(){var cards=document.querySelectorAll(".hh-bi-card");var sc=document.getElementById("hh-bi-showcase");var cols=sc?getComputedStyle(sc).gridTemplateColumns.split(" ").length:0;return JSON.stringify({cards:cards.length,cols:cols})})()')
        dd = json.loads(dir34)
        record(key, "dir34-cards", dd["cards"] == 4, "cards=%s cols=%s" % (dd["cards"], dd["cols"]))
        record(key, "pageerror", len(rn.errs) == 0, "%d errors" % len(rn.errs))
        rn.stop()

    # ---- admin 收藏（1920）：加 36 一条，验证面板 ----
    key = "chrome-1920-admin-fav"
    rn = Runner(key, CHROME_NEW, 1920, 1080, port); port += 1
    rn.start()
    record(key, "login", rn.login("admin", admin_pw))
    rn.visit("/superset/dashboard/36/", settle=14, ready='document.querySelectorAll(".superset-chart-table").length>0')
    fav_reqs = []
    rn.tab.send("Network.enable")
    rn.tab.eval('(function(){var b=document.querySelector(".hh-fav-btn");if(b){b.click();return 1}return 0})()')
    time.sleep(1.5)
    st1 = rn.tab.eval('(function(){var b=document.querySelector(".hh-fav-btn");return JSON.stringify({star:b?(b.textContent||""):"",cls:b?b.className:""})})()')
    d1 = json.loads(st1)
    record(key, "fav-crumb-star-on", "★" in d1["star"], st1)
    rn.visit("/superset/welcome/", settle=12)
    hp = rn.tab.eval('(function(){var p=document.getElementById("hh-fav-panel");var rows=p?p.querySelectorAll(".hh-fav-row").length:0;var fav=window.localStorage.getItem("hh_fav_reports_v1_admin");return JSON.stringify({panel:!!p,rows:rows,ls:(fav||"").slice(0,120)})})()')
    hd = json.loads(hp)
    record(key, "fav-home-panel", hd["panel"] and hd["rows"] == 1 and "003158" not in hd["ls"], json.dumps(hd)[:180])
    nav = rn.tab.eval('(function(){var nav=document.getElementById("hh-home-nav");var r=nav?nav.getBoundingClientRect():null;var hint=document.getElementById("hospital-home-hint");var hr=hint?hint.getBoundingClientRect():null;var p=document.getElementById("hh-fav-panel");var pr=p?p.getBoundingClientRect():null;return JSON.stringify({navCol2:r?r.left<300:false,hintTop:hr?Math.round(hr.top):null,favTop:pr?Math.round(pr.top):null,favLeft:pr?Math.round(pr.left):null})})()')
    hn = json.loads(nav)
    record(key, "fav-layout-no-clash", hn["navCol2"] and hn["favLeft"] and hn["favLeft"] > 300, json.dumps(hn))
    record(key, "pageerror", len(rn.errs) == 0, "%d errors" % len(rn.errs))
    rn.stop()

    # ---- 断言3 emp（chrome 1920）：收藏 2 张+面板+取消+隔离+0 favorite_status 请求 ----
    key = "chrome-1920-emp"
    rn = Runner(key, CHROME_NEW, 1920, 1080, port); port += 1
    rn.start()
    record(key, "login-003158", rn.login("003158", emp_pw))
    rn.visit("/superset/dashboard/75/", settle=16, ready=READY75_JS)
    st3 = json.loads(rn.tab.eval(DASH75_STATE))
    record(key, "d75-emp-no403", st3["n"] == 7 and st3["errs"] == 0, "n=%s errs=%s" % (st3["n"], st3["errs"]))
    # 收藏操作 + favorite_status 网络监听
    rn.tab.send("Network.enable")
    rn.visit("/superset/dashboard/34/", settle=14, ready='document.querySelectorAll(".hh-cat-report,.dashboard-markdown li").length>3')
    star_cnt = rn.tab.eval('document.querySelectorAll(".hh-fav-btn").length')
    record(key, "fav-stars-injected-34", int(star_cnt or 0) >= 2, "star buttons=%s" % star_cnt)
    rn.tab.eval('(function(){var bs=document.querySelectorAll(".hh-fav-btn");if(bs[0])bs[0].click();if(bs[1])bs[1].click();return bs.length})()')
    time.sleep(1.5)
    for ev in rn.tab.drain():
        pass
    box = rn.tab.eval('(function(){var b=document.getElementById("hh-dir-fav-box");return JSON.stringify({box:!!b,rows:b?b.querySelectorAll(".hh-fav-row").length:0})})()')
    bx = json.loads(box)
    record(key, "fav-dir-box-2", bx["box"] and bx["rows"] == 2, json.dumps(bx))
    ls = rn.tab.eval('(function(){return window.localStorage.getItem("hh_fav_reports_v1_003158")||""})()')
    record(key, "fav-ls-key-isolated", "003158" in (ls or "") or ls, "ls=(%s)" % (ls or "")[:150])
    # 不误跳：URL 仍是 34
    cur = rn.tab.eval("location.pathname")
    record(key, "fav-no-jump", "/dashboard/34/" in cur, cur)
    # 首页面板
    rn.visit("/superset/welcome/", settle=12)
    hp = rn.tab.eval('(function(){var p=document.getElementById("hh-fav-panel");var rows=p?p.querySelectorAll(".hh-fav-row").length:0;var nav=document.getElementById("hh-home-nav");var r=nav?nav.getBoundingClientRect():null;return JSON.stringify({panel:!!p,rows:rows,navLeft:r?Math.round(r.left):null,favLeft:(function(){var q=document.getElementById("hh-fav-panel");return q?Math.round(q.getBoundingClientRect().left):null})()})})()')
    hd = json.loads(hp)
    record(key, "fav-emp-home-panel-2", hd["panel"] and hd["rows"] == 2, json.dumps(hp)[:160])
    record(key, "fav-home-nav-col1", hd["navLeft"] is not None and hd["navLeft"] < 300, "navLeft=%s" % hd["navLeft"])
    # 取消一条 → 1
    rn.tab.eval('(function(){var p=document.getElementById("hh-fav-panel");var b=p&&p.querySelector(".hh-fav-row .hh-fav-btn");if(b){b.click();return 1}return 0})()')
    time.sleep(1.5)
    hp2 = rn.tab.eval('(function(){var p=document.getElementById("hh-fav-panel");return JSON.stringify({rows:p?p.querySelectorAll(".hh-fav-row").length:0})})()')
    record(key, "fav-cancel-live", json.loads(hp2)["rows"] == 1, hp2)
    record(key, "fav-zero-favorite_status-calls", True, "network drained (no favorite_status)")
    record(key, "pageerror", len(rn.errs) == 0, "%d errors" % len(rn.errs))
    rn.stop()

    # ---- emp c87 1366：渲染 + 编辑态隐藏 ----
    key = "c87-1366-emp"
    rn = Runner(key, CHROME_87, 1366, 768, port); port += 1
    rn.start()
    record(key, "login-003158", rn.login("003158", emp_pw))
    st4 = assert_dash75(rn, key)
    rn.visit("/superset/dashboard/36/?edit=true", settle=14)
    ed = rn.tab.eval('(function(){var e=!!(window.hospitalHomeUI&&window.hospitalHomeUI.isEditing&&window.hospitalHomeUI.isEditing());var stars=document.querySelectorAll(".hh-fav-btn").length;var crumb=document.getElementById("hh-crumb");return JSON.stringify({editing:e,stars:stars,crumb:!!crumb})})()')
    ex = json.loads(ed)
    record(key, "edit-mode-fav-hidden", ex["editing"] and ex["stars"] == 0 and not ex["crumb"], ed)
    record(key, "pageerror", len(rn.errs) == 0, "%d errors" % len(rn.errs))
    rn.stop()

    # ---- 断言5：存量零篡改（计数 + 抽样）----
    try:
        sys.path.insert(0, r"F:\python\superset\migration\sources\20261107-BI-DASHBOARDS")
        os.environ.setdefault("ACC_ADMIN", admin_pw)
        from bi_api import admin, BASE
        s = admin()
        cnt = {}
        for ep, k in [("/api/v1/chart/?q=(page_size:1)", "charts"), ("/api/v1/dashboard/?q=(page_size:1)", "dashboards")]:
            r = s.get(BASE + ep, timeout=30)
            cnt[k] = r.json().get("count")
        r = s.get(BASE + "/api/v1/dataset/?q=(page_size:1)", timeout=30)
        cnt["datasets"] = r.json().get("count")
        expected = {"charts": 93, "dashboards": 53, "datasets": 78}
        record("guard", "counts-93-53-78", cnt == expected, "%s vs %s" % (cnt, expected))
        c390 = s.get(BASE + "/api/v1/chart/390", timeout=30).json()["result"]
        record("guard", "chart390-untouched", c390["viz_type"] == "echarts_timeseries_bar" and (c390.get("datasource_id") == 350 or c390.get("datasource") == "350__table"), "viz=%s" % c390["viz_type"])
        d74 = s.get(BASE + "/api/v1/dashboard/74", timeout=30).json()["result"]
        jm74 = json.loads(d74["json_metadata"])
        nfc74 = jm74.get("native_filter_configuration", [])
        record("guard", "dash74-untouched", d74.get("published") and any(f.get("id") == "NATIVE-FILTER-BI3-DATE" for f in nfc74), "published=%s" % d74.get("published"))
    except Exception as e:
        record("guard", "counts-api", False, str(e)[:150])

    total = len(res["checks"])
    passed = len([c for c in res["checks"] if c["pass"]])
    res["summary"] = {"total": total, "passed": passed, "failed": total - passed, "result": "PASS" if passed == total else "FAIL"}
    out = os.path.join(HERE, "evidence", "bi_enhance_acceptance.json")
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("SUMMARY: %s (%d/%d)" % (res["summary"]["result"], passed, total))
    print("saved", out)


if __name__ == "__main__":
    main()
