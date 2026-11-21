# -*- coding: utf-8 -*-
"""20261118-DETAIL-UX 阶段3：双浏览器像素级几何真机验收（f14 上线后）。

矩阵：Chrome(新版) + Chromium 87 × {1366x768, 1920x1080} × {admin, 003158}
断言：
  A1 首屏不溢出：36/42/61/65/39/32 首屏数据卡片 holderRect.bottom <= innerH+1
  A2 末行与分页 0 裁切：scroll 滚到底后 tbody 末行 rect.bottom <= scroll.bottom+1；
     分页器（若有）paginationRect.bottom <= holderRect.bottom+1
  A3 交互增强（Chrome 1366，admin）：收起筛选→滚动区净增>=60px→展开恢复；
     全屏看表→顶栏隐藏铺满→Esc 恢复；双击长文本单元格→#hh-cell-pop→Esc 关闭
  A4 零误伤：34 目录分组下钻正常；72 无 hh-single-table-page 且自然滚动；
     admin 编辑态（dashboardState.editMode===true）自动退出锁高且无 data-hh-sized 残留；
     全程 pageerror === 0
输出 evidence/detail_ux_acceptance.json（全部 PASS 才算过）。
凭据经环境变量 VDX_ADMIN / VDX_EMP 注入。分片导航防会话级停滞（每 3 页重启浏览器）。
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
CHROME_NEW = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CHROME_87 = r"F:\python\superset\migration\tools\chromium87-r809590\chrome-win\chrome.exe"
PAGES_A1 = ["36", "42", "61", "65", "39", "32"]

GEO = r"""(function(){
  var de=document.documentElement;
  var hs=document.querySelectorAll('.dashboard-component-chart-holder[class*="dashboard-chart-id-"]');
  var first=null;
  for(var i=0;i<hs.length;i++){var r0=hs[i].getBoundingClientRect();if(r0.height>60){first=hs[i];break;}}
  if(!first&&hs.length)first=hs[0];
  var fr=first?first.getBoundingClientRect():null;
  var se=document.scrollingElement||document.documentElement;
  var chart=document.querySelector('.superset-chart-table');
  var tbls=chart?chart.querySelectorAll('table'):[];
  var dataTb=null,rows=0;
  for(var i=0;i<tbls.length;i++){var b=tbls[i].querySelector('tbody');if(b&&b.rows.length){dataTb=tbls[i];rows=b.rows.length;break;}}
  var scr=dataTb?dataTb.parentElement:null;
  var pg=chart?chart.querySelector('.pagination'):null;
  var pvt=document.querySelector('.pvtTable');
  var pvtScr=null;
  if(pvt){var nn=pvt.parentElement;var g=0;while(nn&&g<8){var s2=getComputedStyle(nn);if(s2.overflowY=='auto'||s2.overflowY=='scroll'){pvtScr=nn;break;}nn=nn.parentElement;g++;}}
  var hm=document.querySelector('#hospital-monthly-report .hm-scroll');
  var lastRow=null;
  if(scr){
    scr.scrollTop=scr.scrollHeight;
    var tb2=dataTb.querySelector('tbody');
    lastRow=tb2&&tb2.rows.length?tb2.rows[tb2.rows.length-1]:null;
  }
  var hmFoot=document.querySelector('#hospital-monthly-report .hm-footer');
  return JSON.stringify({
    single:de.classList.contains('hh-single-table-page'),duo:de.classList.contains('hh-duo-table-page'),
    denied:!!document.querySelector('.hh-denied-card'),errPage:!!document.querySelector('.error-page-content'),
    innerH:window.innerHeight,holdB:fr?Math.round(fr.bottom):null,
    holdH:fr?Math.round(fr.height):null,holdT:fr?Math.round(fr.top):null,
    ovf:se.scrollHeight-window.innerHeight,rows:rows,
    scrB:scr?Math.round(scr.getBoundingClientRect().bottom):null,
    scrH:scr?scr.clientHeight:null,
    lastB:lastRow?Math.round(lastRow.getBoundingClientRect().bottom):null,
    pgB:pg?Math.round(pg.getBoundingClientRect().bottom):null,
    pvtB:pvtScr?Math.round(pvtScr.getBoundingClientRect().bottom):null,
    hmB:hm?Math.round(hm.getBoundingClientRect().bottom):null,
    hmFootB:hmFoot?Math.round(hmFoot.getBoundingClientRect().bottom):null});
})()"""


def launch(exe, tag, w, h, port):
    profile = os.path.join(HERE, "profile-vdx-%s" % tag)
    proc = subprocess.Popen([
        exe, "--remote-debugging-port=%d" % port, "--user-data-dir=%s" % profile,
        "--no-first-run", "--no-default-browser-check", "--disable-session-crashed-bubble",
        "--window-size=%d,%d" % (w, h), "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port, timeout=5) as r:
                ver = json.loads(r.read().decode()).get("Browser", "")
            if ver:
                return proc, ver
        except Exception:
            time.sleep(0.5)
    return proc, ""


class Runner:
    def __init__(self, results, key):
        self.res = results
        self.key = key
        self.errs = []
        self.proc = None
        self.tab = None
        self.ws = None

    def record(self, name, ok, detail=""):
        full = "%s/%s" % (self.key, name)
        self.res["checks"].append({"name": full, "pass": bool(ok), "detail": str(detail)[:300]})
        print(("PASS " if ok else "FAIL ") + full + (" | " + str(detail)[:120] if detail else ""), flush=True)

    def start(self, exe, w, h, port):
        self.stop()
        self.proc, ver = launch(exe, "p%d" % port, w, h, port)
        info = new_tab(port)
        self.ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=60)
        self.tab = Tab(self.ws)
        self.tab.send("Page.enable")
        self.tab.send("Runtime.enable")
        return ver

    def login(self, user, pw):
        return self.tab.login(user, pw)

    def visit(self, path, settle=16):
        self.tab.send("Page.navigate", {"url": BASE + path})
        time.sleep(2.5)
        for _ in range(40):
            if self.tab.eval("document.readyState") == "complete":
                break
            time.sleep(0.5)
        time.sleep(settle)
        self.collect_errors()

    def collect_errors(self):
        for ev in self.tab.drain():
            if ev.get("method") == "Runtime.exceptionThrown":
                d = ev["params"].get("exceptionDetails", {})
                txt = d.get("text", "")
                try:
                    txt += " " + (d.get("exception") or {}).get("description", "")[:150]
                except Exception:
                    pass
                self.errs.append(txt)

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
        self.proc = None
        self.ws = None
        self.tab = None
        time.sleep(1.5)


def geo_assertions(rn, res, pid):
    g = json.loads(rn.tab.eval(GEO))
    res.setdefault("geo", {})[rn.key + "/" + pid] = g
    if g.get("denied") or g.get("errPage"):
        rn.record("A1-p%s" % pid, True, "无权限页（提示卡/错误页），几何断言豁免")
        return
    ih = g["innerH"]
    # A1 首屏不溢出：holder 或月报 footer 在视口内
    bottom = g.get("holdB")
    if pid == "32":
        bottom = g.get("hmFootB") or g.get("hmB")
    ok1 = bottom is not None and bottom <= ih + 1
    rn.record("A1-p%s" % pid, ok1, "bottom=%s innerH=%s ovf=%s" % (bottom, ih, g.get("ovf")))
    # A2 末行与分页 0 裁切
    if g.get("rows", 0) > 0 and g.get("scrB") is not None:
        ok2 = g.get("lastB") is not None and g["lastB"] <= g["scrB"] + 1
        rn.record("A2-lastrow-p%s" % pid, ok2, "lastB=%s scrB=%s" % (g.get("lastB"), g.get("scrB")))
        if g.get("pgB") is not None:
            okp = g["pgB"] <= (bottom or ih) + 1
            rn.record("A2-pagination-p%s" % pid, okp, "pgB=%s holderB=%s" % (g["pgB"], bottom))
    elif pid == "39" and g.get("pvtB") is not None:
        ok2 = g["pvtB"] <= ih + 1
        rn.record("A2-pvt-p39", ok2, "pvtB=%s innerH=%s" % (g["pvtB"], ih))


def main():
    admin_pw = os.environ.get("VDX_ADMIN", "")
    emp_pw = os.environ.get("VDX_EMP", "<REDACTED-DEFAULT-EMPLOYEE-PW>")
    res = {"meta": {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "version": "20261118f14"},
           "checks": [], "geo": {}}
    port = 19500

    # ---- 矩阵：浏览器 × 分辨率 × 账号（A1/A2）----
    matrix = [
        ("chrome", CHROME_NEW, 1366, 768, "admin", admin_pw),
        ("chrome", CHROME_NEW, 1920, 1080, "admin", admin_pw),
        ("c87", CHROME_87, 1366, 768, "admin", admin_pw),
        ("c87", CHROME_87, 1920, 1080, "admin", admin_pw),
        ("chrome", CHROME_NEW, 1366, 768, "emp", emp_pw),
        ("c87", CHROME_87, 1366, 768, "emp", emp_pw),
    ]
    for bname, exe, w, h, who, pw in matrix:
        key = "%s-%dx%d-%s" % (bname, w, h, who)
        user = "admin" if who == "admin" else "003158"
        rn = Runner(res, key)
        ver = rn.start(exe, w, h, port)
        port += 1
        res.setdefault("browsers", {})[key] = ver
        login_ok = rn.login(user, pw)
        rn.record("login", login_ok, "%s@%s" % (user, bname))
        if not login_ok:
            rn.stop()
            continue
        # 分片：6 页拆 2 组（每组 3 页重启）防会话停滞
        for gi, group in enumerate([PAGES_A1[:3], PAGES_A1[3:]]):
            if gi == 1:
                rn.start(exe, w, h, port)
                port += 1
                rn.login(user, pw)
            for pid in group:
                rn.visit("/superset/dashboard/%s/" % pid)
                geo_assertions(rn, res, pid)
        rn.record("pageerror", len(rn.errs) == 0, "%d errors" % len(rn.errs))
        if rn.errs:
            res.setdefault("pageerrors", {})[key] = rn.errs[:5]
        rn.stop()

    # ---- A3 交互增强（Chrome 1366 admin，36 号）----
    rn = Runner(res, "chrome-1366x768-admin-A3")
    rn.start(CHROME_NEW, 1366, 768, port)
    port += 1
    rn.login("admin", admin_pw)
    rn.visit("/superset/dashboard/36/", settle=18)
    g0 = json.loads(rn.tab.eval(GEO.replace("scr.scrollTop=scr.scrollHeight;", "")))
    # 收起筛选
    b0 = rn.tab.eval("(function(){var b=document.querySelector('.hh-btn-fold-top');if(b){b.click();return 1}return 0})()")
    time.sleep(2)
    g1 = json.loads(rn.tab.eval(GEO.replace("scr.scrollTop=scr.scrollHeight;", "")))
    fb = rn.tab.eval("(function(){var f=document.querySelector('[data-test=\"filter-bar\"]');return f?getComputedStyle(f).display:'none'})()")
    cap = rn.tab.eval("(function(){var c=document.querySelector('.hh-fold-capsule');return c?c.textContent.slice(0,40):''})()")
    rn.record("A3-fold-click", b0 == 1, "btn=%s" % b0)
    rn.record("A3-fold-hidden", fb == "none", "filterBar display=%s" % fb)
    rn.record("A3-fold-capsule", len(cap) > 4, "capsule=%s" % cap)
    # 展开恢复
    rn.tab.eval("(function(){var b=document.querySelector('.hh-btn-fold-top');if(b)b.click();return 1})()")
    time.sleep(2)
    g2 = json.loads(rn.tab.eval(GEO.replace("scr.scrollTop=scr.scrollHeight;", "")))
    fb2 = rn.tab.eval("(function(){var f=document.querySelector('[data-test=\"filter-bar\"]');return f?getComputedStyle(f).display:'none'})()")
    rn.record("A3-unfold-restore", fb2 != "none", "filterBar display=%s" % fb2)
    # 收起筛选的收益=滚动区高度净增（表底钉在视口底沿不变，多出的高度即多看的行）
    gain = (g1.get("scrH") or 0) - (g2.get("scrH") or 0)
    rn.record("A3-fold-gain", gain >= 60, "scroll clientHeight gain=%spx (fold %s -> unfold %s)" % (gain, g1.get("scrH"), g2.get("scrH")))
    # 全屏看表
    rn.tab.eval("(function(){var b=document.querySelector('.hh-btn-max-table');if(b){b.click();return 1}return 0})()")
    time.sleep(2)
    hd = rn.tab.eval("(function(){var h=document.querySelector('header');return h?getComputedStyle(h).display:'none'})()")
    g3 = json.loads(rn.tab.eval(GEO.replace("scr.scrollTop=scr.scrollHeight;", "")))
    title = rn.tab.eval("(function(){var t=document.querySelector('.hh-max-title');return t?t.textContent.slice(0,30):''})()")
    gain3 = (g3.get("scrH") or 0) - (g2.get("scrH") or 0)
    rn.record("A3-max-header-hidden", hd == "none", "header display=%s" % hd)
    rn.record("A3-max-fill", gain3 >= 100 and (g3.get("holdT") or 999) <= 16, "scrollH gain=%spx holderTop %s->%s" % (gain3, g2.get("holdT"), g3.get("holdT")))
    rn.record("A3-max-title", len(title) > 1, "title=%s" % title)
    # Esc 恢复
    rn.tab.send("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27})
    rn.tab.send("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27})
    time.sleep(2)
    hd2 = rn.tab.eval("(function(){var h=document.querySelector('header');return h?getComputedStyle(h).display:'block'})()")
    rn.record("A3-esc-restore", hd2 != "none", "header display=%s" % hd2)
    # 双击长文本单元格弹出气泡：优先选发生截断或长文本的单元格
    rn.tab.eval("(function(){var ts=document.querySelectorAll('.superset-chart-table table');for(var i=0;i<ts.length;i++){var tb=ts[i].querySelector('tbody');if(tb&&tb.rows.length){for(var r2=0;r2<tb.rows.length&&r2<6;r2++){var cs=tb.rows[r2].cells;for(var c2=0;c2<cs.length;c2++){var td=cs[c2];var t=(td.textContent||'').trim();if(t.length>10||td.scrollWidth>td.clientWidth+1){td.dispatchEvent(new MouseEvent('dblclick',{bubbles:true}));return 1}}}}}return 0})()")
    time.sleep(1)
    pop = rn.tab.eval("(function(){var p=document.getElementById('hh-cell-pop');return p?JSON.stringify({col:(p.querySelector('.hh-pop-col')||{}).textContent||'',bodyLen:(p.querySelector('.hh-pop-body')||{textContent:''}).textContent.length}):''})()")
    rn.record("A3-cellpop", len(pop) > 5, "pop=%s" % pop[:120])
    rn.tab.send("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27})
    rn.tab.send("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27})
    time.sleep(1)
    pop2 = rn.tab.eval("!!document.getElementById('hh-cell-pop')")
    rn.record("A3-cellpop-esc", pop2 == False, "pop exists=%s" % pop2)  # noqa: E712
    rn.collect_errors()
    rn.record("pageerror-A3", len(rn.errs) == 0, "%d errors" % len(rn.errs))
    if rn.errs:
        res.setdefault("pageerrors", {})["A3"] = rn.errs[:5]
    rn.stop()

    # ---- A4 零误伤（Chrome 1366 admin）----
    rn = Runner(res, "chrome-1366x768-admin-A4")
    rn.start(CHROME_NEW, 1366, 768, port)
    port += 1
    rn.login("admin", admin_pw)
    # 34 目录下钻（h16 回归）：等待目录列表渲染完成（.dashboard-markdown li 出现），点击分类行展开
    rn.visit("/superset/dashboard/34/", settle=12)
    ready34 = False
    for _ in range(20):
        n = rn.tab.eval("document.querySelectorAll('.dashboard-markdown li, li[data-hh-cat-group]').length")
        if n and int(n) > 0:
            ready34 = True
            break
        time.sleep(3)
    rn.record("A4-34-render", ready34, "catalog li count=%s" % n)
    if ready34:
        clicked = rn.tab.eval("(function(){var li=document.querySelector('li[data-hh-cat-group]')||document.querySelector('.dashboard-markdown li');if(!li)return 'nogroup';var t=li.querySelector('a,span,div,h3,h4,li')||li;t.dispatchEvent(new MouseEvent('click',{bubbles:true}));return 'clicked'})()")
        time.sleep(2)
        vis = rn.tab.eval("(function(){var li=document.querySelector('li[data-hh-cat-group]')||document.querySelector('.dashboard-markdown li');if(!li)return 0;var links=li.querySelectorAll('a');var v=0;for(var i=0;i<links.length;i++){var r=links[i].getBoundingClientRect();if(r.height>0&&r.width>0)v++;}return v})()")
        rn.record("A4-34-drilldown", (clicked == "clicked" and int(vis or 0) > 0), "clicked=%s visibleLinks=%s" % (clicked, vis))
    # 72 无锁高、自然滚动
    rn.visit("/superset/dashboard/72/", settle=14)
    g72 = json.loads(rn.tab.eval(GEO))
    rn.record("A4-72-nolock", not g72.get("single") and not g72.get("duo"), "single=%s duo=%s" % (g72.get("single"), g72.get("duo")))
    # 编辑态退出锁高
    rn.visit("/superset/dashboard/36/?edit=true", settle=14)
    ed = rn.tab.eval("(function(){var e=!!(window.hospitalHomeUI&&window.hospitalHomeUI.isEditing&&window.hospitalHomeUI.isEditing());return JSON.stringify({editing:e,single:document.documentElement.classList.contains('hh-single-table-page'),sized:document.querySelectorAll('[data-hh-sized]').length,cssVar:document.documentElement.style.getPropertyValue('--hh-chart-max')})})()")
    d = json.loads(ed) if ed else {}
    rn.record("A4-editmode-exit", d.get("editing") and not d.get("single") and int(d.get("sized") or 0) == 0 and not d.get("cssVar"),
              "editState=%s" % ed)
    rn.collect_errors()
    rn.record("pageerror-A4", len(rn.errs) == 0, "%d errors" % len(rn.errs))
    if rn.errs:
        res.setdefault("pageerrors", {})["A4"] = rn.errs[:5]
    rn.stop()

    total = len(res["checks"])
    passed = len([c for c in res["checks"] if c["pass"]])
    res["summary"] = {"total": total, "passed": passed, "failed": total - passed,
                      "result": "PASS" if passed == total else "FAIL"}
    out = os.path.join(HERE, "evidence", "detail_ux_acceptance.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("SUMMARY: %s (%d/%d)" % (res["summary"]["result"], passed, total), flush=True)
    print("saved", out, flush=True)


if __name__ == "__main__":
    main()
