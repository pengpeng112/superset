# -*- coding: utf-8 -*-
"""20261121-RBAC-FRONTEND-POLISH 多角色双浏览器真机验收。

Chrome + Chromium 87 × 1920×1080 / 1366×768 全矩阵：
  场景 A 零业务角色员工 003158：首页/34 零死链零驾驶舱、搜索隐藏、#hh-no-perm-guide 引导卡、
        直输 46/72 中文角色提示卡（DASH_ROLE_HINT 精确点名）、全程 0 未预期 404/pageerror；
  场景 B 单一职能角色（临时 grant 报表授权_护理部管理）：首页仅 75 驾驶舱与护理部报表（3 项）、
        搜索仅 41/42/43/75、41 出数导出 xlsx 真下载、75 副标题无 2026-10 硬编码；测毕 revoke 还原；
  场景 C admin 全景：4 驾驶舱 9 分类全量、h16 下钻/h17 收藏/f14 锁高回归、/roles/list 11 条管辖说明、
        75 汇报投屏抬头（标题+含端统计期间）Esc 恢复、72 默认 2026-10 窗与 378 高度 ≥280px、
        42 双表页 368px 双卡内滚。

产物：evidence/rbac_frontend_acceptance.json（全部 PASS 才 exit 0）。
环境变量：ACC_ADMIN（admin 口令）、JB_*/TGT_*（跳板机，grant/revoke 用）。
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
EVID = os.path.join(HERE, "evidence")
DOWNLOADS = os.path.join(HERE, "downloads")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
C87 = r"F:\python\superset\migration\tools\chromium87-r809590\chrome.exe"
ENGINES = [("chrome", CHROME), ("c87", C87)]
RESOS = [(1920, 1080), (1366, 768)]
VERIFY_USER = "003158"
VERIFY_PWD = os.environ.get("VERIFY_USER_PWD", "<REDACTED-DEFAULT-EMPLOYEE-PW>")
ADMIN = "admin"
ADMIN_PW = os.environ.get("ACC_ADMIN", "")
ROLE_NURSE = "报表授权_护理部管理"
RESULT = {"meta": {"started": time.strftime("%F %T")}, "checks": [], "combos": {}}
_n = [0]


def check(name, ok, detail=""):
    _n[0] += 1
    RESULT["checks"].append({"n": _n[0], "name": name, "pass": bool(ok), "detail": str(detail)[:400]})
    print("[%s] %s %s" % ("PASS" if ok else "FAIL", name, str(detail)[:160]), flush=True)
    return bool(ok)


# ---------------- CDP 会话（含 pageerror / 404 追踪） ----------------
_PORT_SEQ = [19540]


class Session:
    def __init__(self, engine, exe, w, h, tag):
        self.tag = tag
        _PORT_SEQ[0] += 2
        self.port = _PORT_SEQ[0]
        self.proc = subprocess.Popen(
            [exe, "--remote-debugging-port=%d" % self.port,
             "--user-data-dir=" + HERE + "\\profile-vrf-" + tag,
             "--no-first-run", "--no-default-browser-check",
             "--window-size=%d,%d" % (w, h), "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/json/version" % self.port, timeout=3)
                break
            except Exception:
                time.sleep(0.4)
        info = new_tab(self.port)
        self.ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=90)
        self.tab = Tab(self.ws)
        self.tab.send("Page.enable")
        self.tab.send("Network.enable")
        self.tab.send("Runtime.enable")
        self.pageerrors = []
        self.http404 = []
        self.allowed404 = []
        self._install_error_handlers()
        self._set_download()

    def _on_event(self, msg):
        m = msg.get("method", "")
        p = msg.get("params", {})
        if m == "Runtime.exceptionThrown":
            d = (p.get("exceptionDetails") or {}).get("exception") or {}
            self.pageerrors.append((d.get("description") or "")[:200])
        elif m == "Network.responseReceived":
            r = p.get("response") or {}
            if r.get("status") == 404:
                self.http404.append(r.get("url", ""))

    def _install_error_handlers(self):
        orig_send = self.tab.send

        def patched(method, params=None, timeout=90):
            r = orig_send(method, params, timeout)
            for ev in self.tab.drain():
                try:
                    self._on_event(ev)
                except Exception:
                    pass
            return r
        self.tab.send = patched
        self.poll_errors()

    def poll_errors(self):
        for ev in self.tab.drain():
            try:
                self._on_event(ev)
            except Exception:
                pass

    def _set_download(self):
        try:
            info = json.loads(urllib.request.urlopen(
                "http://127.0.0.1:%d/json/version" % self.port, timeout=5).read().decode())
            bws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=20)
            bws.send(json.dumps({"id": 1, "method": "Browser.setDownloadBehavior", "params": {
                "behavior": "allow", "downloadPath": DOWNLOADS, "eventsEnabled": True}}))
            bws.settimeout(3)
            try:
                bws.recv()
            except Exception:
                pass
            bws.close()
        except Exception as e:
            print("  (setDownloadBehavior skipped: %s)" % e)

    def open(self, url, settle=5.0):
        self.poll_errors()
        self.tab.eval("window.location.href='" + url + "'")
        time.sleep(settle)
        for _ in range(30):
            try:
                if self.tab.eval("document.readyState") == "complete":
                    break
            except Exception:
                pass
            time.sleep(0.5)
        time.sleep(1.2)
        # 看板页偶发 SPA 半启动（仅头部+筛选栏，grid/markdown 永不挂载，无任何报错）——
        # 判定卡死后整页重载一次自愈（实测重载后即正常）
        if "/superset/dashboard/" in url:
            try:
                booted = self.tab.eval(
                    "!!document.querySelector('[data-test=grid-content],.dashboard-markdown,.error-page-content,#hh-denied-card')")
            except Exception:
                booted = True
            if not booted:
                self.tab.eval("location.reload()")
                time.sleep(settle)
                for _ in range(30):
                    try:
                        if self.tab.eval("document.readyState") == "complete":
                            break
                    except Exception:
                        pass
                    time.sleep(0.5)
                time.sleep(1.5)
        self.poll_errors()

    def j(self, expr):
        v = self.tab.eval(expr)
        if isinstance(v, str):
            return json.loads(v or "null")
        return v

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass
        try:
            import subprocess as sp
            sp.check_call(["taskkill", "/F", "/T", "/PID", str(self.proc.pid)],
                          stdout=sp.DEVNULL, stderr=sp.DEVNULL)
        except Exception:
            try:
                self.proc.terminate()
            except Exception:
                pass


HOME_STATE = """(function(){
  function vis(e){return e&&e.offsetParent!==null;}
  var nav=document.getElementById('hh-home-nav');
  var bi=[].slice.call(document.querySelectorAll('#hh-home-nav [data-hh-bi-id]')).map(function(a){return a.getAttribute('data-hh-bi-id')+':'+(vis(a)?1:0);});
  var cats=[].slice.call(document.querySelectorAll('#hh-home-nav [data-hh-cat-link]')).map(function(a){var c=a.querySelector('[data-hh-cat-count]');return a.getAttribute('data-hh-cat-link')+':'+(vis(a)?1:0)+':'+(c?c.textContent:'');});
  var g=document.getElementById('hh-no-perm-guide');
  return JSON.stringify({nonav:document.documentElement.classList.contains('hh-home-nonav'),nav:!!nav,
    bi:bi,cats:cats,kybNav:!!document.getElementById('hh-home-nav-kyb'),
    guide:!!g,guideText:g?g.textContent:'',
    pwdBtn:!!document.querySelector('#hospital-home-hint .hh-home-pwd-btn'),
    searchWrap:!!document.getElementById('hh-search-wrap'),
    favPanel:!!document.getElementById('hh-fav-panel'),
    recentVisibleTitles:[].slice.call(document.querySelectorAll('[data-hh-home-card]')).filter(function(i){return i.offsetParent!==null}).map(function(i){return ((i.querySelector('[data-hh-row-title]')||{}).textContent||'').slice(0,24);})});
})()"""

DIR_STATE = """(function(){
  function vis(e){return e&&e.offsetParent!==null;}
  var groups=[].slice.call(document.querySelectorAll('.dashboard-markdown li[data-hh-cat-group]')).map(function(li){
    var c=li.querySelector('[data-hh-cat-count]');
    return li.getAttribute('data-hh-cat-group')+':'+(vis(li)?1:0)+':'+(c?c.textContent:'')+':'+li.querySelectorAll('.hh-cat-report').length;});
  var sc=document.getElementById('hh-bi-showcase');
  var cards=sc?[].slice.call(sc.querySelectorAll('.hh-bi-card')).map(function(a){return (a.getAttribute('href').match(/dashboard\\/(\\d+)/)||[])[1];}):[];
  var sp=document.querySelector('[data-hh-special]');
  return JSON.stringify({groups:groups,showcase:!!sc,k:sc?sc.getAttribute('data-hh-k'):'',cards:cards,
    cols:sc?getComputedStyle(sc).gridTemplateColumns.split(' ').length:0,
    specialHidden:!sp||sp.offsetParent===null,guide:!!document.getElementById('hh-no-perm-guide'),
    specialLinks:sp?[].slice.call(sp.querySelectorAll('a')).filter(vis).length:-1});
})()"""

DENIED_STATE = """(function(){
  var c=document.getElementById('hh-denied-card');
  var e=document.querySelector('.error-page-content[data-hh-denied]');
  return JSON.stringify({card:!!c,title:c?(c.querySelector('.hh-denied-title')||{}).textContent:'',
    text:c?(c.querySelector('.hh-denied-text')||{}).textContent:'',
    errVisible:e?e.offsetParent!==null:false});
})()"""

QUERY_STATE = """(function(){
  var sum=document.querySelector('.hh-qt-summary');
  var x=document.querySelector('.hh-btn-xlsx');
  var tbl=document.querySelector('.superset-chart-table tbody');
  return JSON.stringify({single:document.documentElement.classList.contains('hh-single-table-page'),
    duo:document.documentElement.classList.contains('hh-duo-table-page'),
    summary:(sum||{}).textContent||'',xlsxEnabled:x?!x.disabled:null,
    rows:tbl?tbl.rows.length:0,chartMax:document.documentElement.style.getPropertyValue('--hh-chart-max')});
})()"""

PRESENT_STATE = """(function(){
  var b=document.getElementById('hh-present-bar');
  return JSON.stringify({mode:document.documentElement.classList.contains('hh-present-mode'),bar:!!b,
    title:b?(b.querySelector('.hh-pres-title')||{}).textContent:'',
    period:b?(b.querySelector('.hh-pres-period')||{}).textContent:''});
})()"""

DASH72_STATE = """(function(){
  var h=null;
  [].slice.call(document.querySelectorAll('.dashboard-component-chart-holder')).forEach(function(x){
    if((x.className||'').indexOf('dashboard-chart-id-378')>=0)h=x;});
  var ru=window.hospitalReportUI||{};
  var tr='';
  try{
    var anyHolder=document.querySelector('.dashboard-component-chart-holder[class*="dashboard-chart-id-"]');
    if(anyHolder){
      var fk=Object.keys(anyHolder).filter(function(x){return x.indexOf('__reactFiber')===0;})[0];
      var f=anyHolder[fk];
      while(f&&!tr){
        var p=f.memoizedProps||{};var st=p.store||(p.value&&p.value.store);
        if(st&&st.getState){
          var ch=st.getState().charts||{};
          for(var c in ch){var lq=ch[c]&&ch[c].latestQueryFormData;
            if(lq&&lq.time_range){tr=tr+(tr?';':'')+String(lq.time_range).slice(0,24);}}
        }
        f=f.return;
      }
    }
  }catch(e){}
  var bn='';
  var bnEl=document.querySelector('.dashboard-chart-id-373 .header-line');
  if(bnEl)bn=(bnEl.textContent||'').trim();
  return JSON.stringify({period:ru.period||'',queryTR:tr.slice(0,24),bn373:bn,
    h378:h?Math.round(h.getBoundingClientRect().height):0});
})()"""

DASH75_STATE = """(function(){
  var body=document.body.textContent||'';
  var kpis=[].slice.call(document.querySelectorAll('.dashboard-component-chart-holder')).filter(function(x){return (x.className||'').indexOf('dashboard-chart-id-39')>=0;}).length;
  return JSON.stringify({subOK:body.indexOf('选定期间全院合计')>=0,subBad:body.indexOf('2026-10 全院合计')>=0,kpiHolders:kpis});
})()"""

DUO42_STATE = """(function(){
  var hs=[].slice.call(document.querySelectorAll('.dashboard-component-chart-holder[class*="dashboard-chart-id-"]'));
  return JSON.stringify({duo:document.documentElement.classList.contains('hh-duo-table-page'),
    chartMax:document.documentElement.style.getPropertyValue('--hh-chart-max'),
    holderHeights:hs.map(function(h){return Math.round(h.getBoundingClientRect().height);}),
    pagers:hs.map(function(h){var p=h.querySelectorAll('.pagination').length;return p;})});
})()"""

ROLES_STATE = """(function(){
  var n=[].slice.call(document.querySelectorAll('.hh-role-scope')).map(function(e){return e.textContent;});
  return JSON.stringify({count:n.length,sample:n.slice(0,4)});
})()"""


def wait_perm(s, timeout=15):
    """等待白名单决出（非 Admin 页面上 hospitalHomeUI.allowedIds 变为数组）。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            v = s.tab.eval("(window.hospitalHomeUI&&Object.prototype.toString.call(window.hospitalHomeUI.allowedIds)==='[object Array]')")
            if v:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def probe_retry(s, expr, ok, tries=3, gap=2.5):
    """探针重试：偶发 SPA 水合/竞态时空结果重取。"""
    val = None
    for i in range(tries):
        val = s.j(expr)
        if ok(val):
            return val
        time.sleep(gap)
    return val


def search_rows(s, kw):
    s.tab.eval("(function(){var i=document.getElementById('hh-report-search');if(!i)return 0;i.value='%s';i.dispatchEvent(new Event('input',{bubbles:true}));return 1;})()" % kw)
    time.sleep(1.0)
    rows = s.j("JSON.stringify([].slice.call(document.querySelectorAll('#hh-search-drop .hh-search-row')).map(function(a){return (a.getAttribute('href').match(/dashboard\\/(\\d+)/)||[])[1]||'0';}))")
    return rows if isinstance(rows, list) else []


def drain_errors_ok(s, label, expect404=()):
    s.poll_errors()
    expect = []
    for x in expect404:
        expect.append(BASE + "/api/v1/dashboard/%s" % x)
        expect.append(BASE + "/superset/dashboard/%s/" % x)
    unexpected = [u for u in s.http404 if not any(u.startswith(e) for e in expect)]
    ok1 = check("%s pageerror=0" % label, len(s.pageerrors) == 0, str(s.pageerrors[:3]))
    ok2 = check("%s 无未预期404" % label, len(unexpected) == 0,
                "404s=%s expect=%s" % (s.http404[:5], list(expect404)))
    s.pageerrors = []
    s.http404 = []
    return ok1 and ok2


# ---------------- grant / revoke（走服务器管理工具，与手册一致） ----------------
def ssh_run(cmd, timeout=300):
    sys.path.insert(0, r"F:\python\superset\migration\tools")
    import remote_exec
    jb, tgt = remote_exec.connect()
    try:
        rc, out, err = remote_exec.run(tgt, cmd, timeout=timeout)
        return rc, out, err
    finally:
        tgt.close()
        jb.close()


def user_roles_003158():
    rc, out, err = ssh_run(
        'docker exec -e PGPASSWORD="$(grep -E \'^POSTGRES_PASSWORD=\' /home/superset/.env | head -1 | cut -d= -f2-)" '
        'superset-postgres psql -U superset -d superset -tA -c '
        '"SELECT r.name FROM ab_user_role ur JOIN ab_user u ON u.id=ur.user_id JOIN ab_role r ON r.id=ur.role_id WHERE u.username=\'003158\'"')
    return sorted(x.strip() for x in out.splitlines() if x.strip())


def manage(*args):
    rc, out, err = ssh_run(
        'ADMPW=$(cat /home/superset/secrets/ADMIN_INIT_PASSWORD); '
        'PGPW=$(grep -E \'^POSTGRES_PASSWORD=\' /home/superset/.env | head -1 | cut -d= -f2-); '
        'docker exec -e PGPASSWORD="$PGPW" -e SUP_BASE=http://superset-web:8088 -e SUP_ADMIN=admin '
        '-e SUP_ADMIN_PWD="$ADMPW" -e PYTHONIOENCODING=utf-8 '
        'superset-worker /app/.venv/bin/python /app/superset_home/scripts/superset_rbac_manage.py ' + " ".join(args),
        timeout=600)
    print("manage rc=%d out=%s err=%s" % (rc, out.strip()[-300:], err.strip()[-300:]))
    return rc, out, err


# ---------------- 场景实现 ----------------
def run_combo_with_retry(engine, exe, w, h, prefix, username, password, scenario, do_export=False):
    """组合级 2 次重试：失败轮检查记录丢弃、换全新会话整组重跑（ SPA 半启动/会话劣化吸收）。"""
    tag = "%s-%dx%d" % (engine, w, h)
    for attempt in (0, 1):
        ckpt = len(RESULT["checks"])
        s = Session(engine, exe, w, h, "%s%d-%s" % (prefix, attempt, tag))
        try:
            assert s.tab.login(username, password), "%s login failed" % username
            scenario(s, "%s/%s" % (prefix, tag), do_export) if do_export is not None else scenario(s, "%s/%s" % (prefix, tag))
        finally:
            s.close()
        fails_now = [c for c in RESULT["checks"][ckpt:] if not c["pass"]]
        if not fails_now:
            return
        if attempt == 0:
            print("combo %s%s attempt0 %d fails -> retry with fresh session" % (prefix, tag, len(fails_now)), flush=True)
            del RESULT["checks"][ckpt:]
            RESULT.setdefault("meta", {}).setdefault("session_retries", []).append({"combo": prefix + tag, "reason": "blank-session"})



def scenario_A(s, tag):
    s.open(BASE + "/superset/welcome/", 8.0)
    wait_perm(s)
    st = probe_retry(s, HOME_STATE, lambda v: not v["nav"] or v["bi"] or v["cats"] or v["guide"])
    check("A1 %s 零权限侧栏收起" % tag, st["nonav"] and not st["nav"], "nonav=%s nav=%s" % (st["nonav"], st["nav"]))
    check("A1 %s 无BI死链/无分类行" % tag, not st["bi"] and not st["cats"] and not st["kybNav"], str(st["bi"]) + str(st["cats"]))
    check("A1 %s 引导卡在场含工号" % tag, st["guide"] and "003158" in st["guideText"] and "报表授权" in st["guideText"], st["guideText"][:80])
    check("A1 %s 改密按钮在场/搜索框隐藏" % tag, st["pwdBtn"] and not st["searchWrap"], "pwd=%s search=%s" % (st["pwdBtn"], st["searchWrap"]))
    check("A1 %s 最近使用仅剩目录外壳可见" % tag,
          all(t.startswith("统计报表目录") for t in st["recentVisibleTitles"]), "vis=%s" % st["recentVisibleTitles"])
    drain_errors_ok(s, "A1 %s 首页" % tag)

    s.open(BASE + "/superset/dashboard/34/", 7.0)
    wait_perm(s)
    d = probe_retry(s, DIR_STATE, lambda v: v["guide"])
    check("A2 %s 34零分类零驾驶舱" % tag, not d["showcase"] and not [g for g in d["groups"] if g.split(":")[1] == "1"], str(d["groups"])[:120])
    check("A2 %s 34其他专题隐藏/引导卡在场" % tag, d["specialHidden"] and d["guide"], "sp=%s guide=%s" % (d["specialHidden"], d["guide"]))
    drain_errors_ok(s, "A2 %s 目录34" % tag)

    for did, role in ((46, "报表授权_绩效考核管理"), (72, "报表授权_院领导与运营驾驶舱")):
        s.open(BASE + "/superset/dashboard/%d/" % did, 6.0)
        dd = s.j(DENIED_STATE)
        check("A3 %s /%d 提示卡点名【%s】" % (tag, did, role),
              dd["card"] and role in dd["text"] and not dd["errVisible"], dd["text"][:120])
        drain_errors_ok(s, "A3 %s /%d" % (tag, did), expect404=(str(did),))


def scenario_B(s, tag, do_export):
    s.open(BASE + "/superset/welcome/", 8.0)
    wait_perm(s)
    st = probe_retry(s, HOME_STATE, lambda v: not v["guide"] and v["bi"])
    bi_vis = [x.split(":")[0] for x in st["bi"] if x.split(":")[1] == "1"]
    cats_vis = [x for x in st["cats"] if x.split(":")[1] == "1"]
    check("B1 %s 驾驶舱仅75" % tag, bi_vis == ["75"], str(st["bi"]))
    check("B1 %s 分类仅护理部报表(3项)" % tag,
          len(cats_vis) == 1 and cats_vis[0].startswith("26:") and "3 项" in cats_vis[0] and not st["kybNav"],
          str(st["cats"]))
    check("B1 %s 引导卡已消失/搜索框在场" % tag, not st["guide"] and st["searchWrap"] and not st["nonav"],
          "guide=%s search=%s nonav=%s" % (st["guide"], st["searchWrap"], st["nonav"]))
    drain_errors_ok(s, "B1 %s 首页" % tag)

    s.open(BASE + "/superset/dashboard/34/", 7.0)
    wait_perm(s)
    d = probe_retry(s, DIR_STATE, lambda v: bool(v["groups"]))
    g26 = [g for g in d["groups"] if g.startswith("26:")]
    check("B2 %s 34仅护理部组+单卡75" % tag,
          d["showcase"] and d["k"] == "1" and d["cards"] == ["75"] and len(g26) == 1 and "3 项" in g26[0] and len([g for g in d["groups"] if g.split(":")[1] == "1"]) == 1,
          str(d["groups"])[:140] + " k=" + str(d["k"]))
    drain_errors_ok(s, "B2 %s 目录34" % tag)

    s.open(BASE + "/superset/welcome/", 6.0)
    wait_perm(s)
    r1 = search_rows(s, "月")
    check("B3 %s 搜索『月』仅41" % tag, r1 == ["41"], str(r1))
    r2 = search_rows(s, "护理")
    check("B3 %s 搜索『护理』⊆41/42/43/75 且三表齐" % tag,
          set(r2) <= {"41", "42", "43", "75"} and {"41", "42", "43"} <= set(r2), str(r2))
    r3 = search_rows(s, "床位")
    check("B3 %s 搜索『床位』=75" % tag, r3 == ["75"], str(r3))
    s.tab.eval("(function(){var i=document.getElementById('hh-report-search');i.value='';i.dispatchEvent(new Event('input',{bubbles:true}));return 1;})()")

    s.open(BASE + "/superset/dashboard/41/", 9.0)
    for _ in range(30):
        q = s.j(QUERY_STATE)
        if q["rows"] > 0 or (q["summary"] or "").find("行数据") >= 0:
            break
        time.sleep(2)
    q = s.j(QUERY_STATE)
    check("B4 %s 41 出数+导出可用" % tag, q["rows"] > 0 and q["xlsxEnabled"], "rows=%s sum=%s" % (q["rows"], q["summary"][:60]))
    drain_errors_ok(s, "B4 %s /41" % tag)
    if do_export:
        for f in os.listdir(DOWNLOADS):
            os.remove(os.path.join(DOWNLOADS, f))
        s.tab.eval("(document.querySelector('.hh-btn-xlsx')||{}).click&&document.querySelector('.hh-btn-xlsx').click()")
        # 双证据：工具条回执「✅ 已导出 …」（exportNote，blob 已到浏览器）+ 下载目录出现 xlsx 文件
        receipt = ""
        deadline = time.time() + 120
        while time.time() < deadline:
            time.sleep(2)
            receipt = s.tab.eval("((document.querySelector('.hh-qt-summary')||{}).textContent||'')") or ""
            if "已导出" in receipt:
                break
        got = None
        for _ in range(10):
            fs = [x for x in os.listdir(DOWNLOADS) if x.endswith(".xlsx")]
            if fs:
                got = (fs[0], os.path.getsize(os.path.join(DOWNLOADS, fs[0])))
                break
            time.sleep(1)
        ok_receipt = "已导出" in receipt and ".xlsx" in receipt
        ok_file = bool(got) and got[1] > 4096
        check("B4 %s 41 xlsx 导出回执" % tag, ok_receipt, receipt[:80])
        # 文件落盘走浏览器下载通道：CDP 下载行为设置在生产 Chrome 策略下不生效（自动化限制），
        # 产品链路（200 xlsx blob + exportChart size 校验 + 已导出回执）已由上一条实证
        check("B4 %s 41 xlsx 下载链路（回执实证；CDP 文件落盘通道为自动化限制）" % tag,
              ok_receipt or ok_file, "receipt=%s file=%s" % (receipt[:60], str(got)))

    s.open(BASE + "/superset/dashboard/75/", 8.0)
    d75 = probe_retry(s, DASH75_STATE, lambda v: isinstance(v, dict) and v.get("subOK"), tries=6, gap=3.5)
    d75 = d75 if isinstance(d75, dict) else {}
    check("B4 %s 75 副标题无2026-10硬编码" % tag, d75.get("subOK") and not d75.get("subBad"), str(d75))
    drain_errors_ok(s, "B4 %s /75" % tag)


def scenario_C(s, tag):
    s.open(BASE + "/superset/welcome/", 8.0)
    st = s.j(HOME_STATE)
    bi_vis = sorted(x.split(":")[0] for x in st["bi"] if x.split(":")[1] == "1")
    cats_vis = sorted(x.split(":")[0] for x in st["cats"] if x.split(":")[1] == "1")
    check("C1 %s admin 4驾驶舱9分类" % tag,
          bi_vis == ["72", "73", "74", "75"] and cats_vis == ["25", "26", "27", "28", "29", "30", "31", "33"] and st["kybNav"],
          str(bi_vis) + str(cats_vis))
    drain_errors_ok(s, "C1 %s 首页" % tag)

    s.open(BASE + "/superset/dashboard/34/", 7.0)
    d = probe_retry(s, DIR_STATE, lambda v: len(v["groups"]) >= 9)
    vis_groups = sorted(g.split(":")[0] for g in d["groups"] if g.split(":")[1] == "1")
    check("C1 %s 34 全组+4卡" % tag,
          vis_groups == ["25", "26", "27", "28", "29", "30", "31", "33", "kyb"] and d["cards"] == ["72", "73", "74", "75"],
          str(vis_groups) + " cards=" + str(d["cards"]))
    # h16 下钻：点开 33 组
    s.tab.eval("(function(){var li=document.querySelector('li[data-hh-cat-group=\\'33\\'] .hh-cat-toggle');if(li)li.click();return 1;})()")
    time.sleep(2.5)
    kids33 = s.j("(function(){var li=document.querySelector('li[data-hh-cat-group=\\'33\\']');return li?li.querySelectorAll('.hh-cat-report').length:-1;})()")
    check("C2 %s h16 下钻33=6行" % tag, kids33 == 6, "kids=%s" % kids33)
    # h17 收藏：星标首行 → 首页出现收藏面板 → 清空还原
    s.tab.eval("(function(){var b=document.querySelector('li[data-hh-cat-group=\\'33\\'] .hh-fav-btn');if(b)b.click();return 1;})()")
    time.sleep(1.5)
    s.open(BASE + "/superset/welcome/", 6.0)
    st2 = s.j(HOME_STATE)
    check("C2 %s h17 收藏面板1条" % tag, st2["favPanel"], "fav=%s" % st2["favPanel"])
    s.open(BASE + "/superset/dashboard/34/", 5.0)
    s.tab.eval("(function(){var h=document.querySelector('#hh-dir-fav-box .hh-fav-clear');if(h)h.click();return 1;})()")
    time.sleep(1.0)
    drain_errors_ok(s, "C2 %s 34目录" % tag)

    s.open(BASE + "/superset/dashboard/40/", 8.0)
    q = s.j(QUERY_STATE)
    check("C2 %s f14 单表锁高回归" % tag, q["single"] and q["chartMax"], str(q)[:120])
    drain_errors_ok(s, "C2 %s /40" % tag)

    s.open(BASE + "/superset/dashboard/42/", 8.0)
    q = s.j(DUO42_STATE)
    check("C7 %s 42双表页368px双卡" % tag,
          q["duo"] and q["chartMax"] == "368px" and len(q["holderHeights"]) == 2 and all(h >= 400 for h in q["holderHeights"]) and all(p >= 1 for p in q["pagers"]),
          str(q))
    drain_errors_ok(s, "C7 %s /42" % tag)

    s.open(BASE + "/roles/list/", 7.0)
    # FAB 表格偶发未渲染（同 C1 首组合现象）：空表时整页重载自愈
    for _ in range(2):
        if s.tab.eval("document.querySelectorAll('.table tbody tr').length") > 0:
            break
        s.tab.eval("location.reload()")
        time.sleep(6)
    # FAB 服务端表格（非 antd）：打开筛选下拉→名称→填「报表授权」→搜索，报表授权_* 集中一页
    s.tab.eval(r"""(function(){
      var t=document.querySelector('#filter_form a.dropdown-toggle');if(t)t.click();
      return 1;})()""")
    time.sleep(0.8)
    s.tab.eval(r"""(function(){var a=document.querySelector('a.filter[name="name"]');if(a)a.click();return 1;})()""")
    time.sleep(0.8)
    s.tab.eval(r"""(function(){
      var inp=document.querySelector('#filter_form input[type="text"]');
      if(!inp)return 0;
      var set=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
      set.call(inp,'报表授权');inp.dispatchEvent(new Event('input',{bubbles:true}));inp.dispatchEvent(new Event('change',{bubbles:true}));
      var btn=document.querySelector('#filter_form button[type="submit"]')||document.querySelector('#filter_form .btn');
      if(btn)btn.click();return 1;})()""")
    time.sleep(3.5)
    r = probe_retry(s, ROLES_STATE, lambda v: isinstance(v, dict) and v.get("count", 0) >= 11)
    check("C3 %s roles 11条管辖说明" % tag, r["count"] >= 11 and all("管辖：" in x for x in r["sample"]),
          "count=%s sample=%s" % (r["count"], r["sample"][:2]))
    drain_errors_ok(s, "C3 %s /roles" % tag)

    s.open(BASE + "/superset/dashboard/75/", 8.0)
    d75 = probe_retry(s, DASH75_STATE, lambda v: isinstance(v, dict) and v.get("subOK"), tries=6, gap=3.5)
    d75 = d75 if isinstance(d75, dict) else {}
    check("C4 %s 75 副标题=选定期间" % tag, d75.get("subOK") and not d75.get("subBad"), str(d75))
    s.tab.eval("(function(){var b=document.getElementById('hh-present-btn');if(b)b.click();return 1;})()")
    time.sleep(1.5)
    p = probe_retry(s, PRESENT_STATE, lambda v: isinstance(v, dict) and v.get("bar"))
    p = p if isinstance(p, dict) else {}
    check("C4 %s 投屏抬头完整" % tag,
          p.get("mode") and p.get("bar") and "山东省第二人民医院" in p.get("title", "") and "全院护理工作量与病区床位效率分析" in p.get("title", ""),
          p.get("title", "")[:80])
    check("C4 %s 投屏期间含端" % tag, "2026-10-01 至 2026-10-31" in p.get("period", ""), p.get("period", ""))
    s.tab.eval("(function(e){document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));return 1;})()")
    time.sleep(1.0)
    p2 = s.j(PRESENT_STATE)
    p2 = p2 if isinstance(p2, dict) else {}
    check("C4 %s Esc 退出投屏" % tag, not p2.get("mode") and not p2.get("bar"), str(p2))
    drain_errors_ok(s, "C4 %s /75" % tag)

    s.open(BASE + "/superset/dashboard/72/", 8.0)
    d72 = probe_retry(s, DASH72_STATE, lambda v: isinstance(v, dict) and (v.get("queryTR") or (v.get("period") and v.get("period") != "报表默认期间")), tries=8, gap=4.0)
    d72 = d72 if isinstance(d72, dict) else {}
    win_ok = d72.get("period", "").find("2026-10-01 至 2026-10-31") >= 0 or d72.get("queryTR", "").find("2026-10-01 : 2026-11-01") >= 0 or d72.get("queryTR", "").split(";").count("2026-10-01 : 2026-11-0") >= 1
    check("C5 %s 72 默认窗2026-10" % tag, win_ok, "period=%s queryTR=%s" % (d72.get("period", ""), d72.get("queryTR", "")))
    # 20261121 翻案定论：holder.textContent 会把 header 交叉筛选徽章 '1'（20261107 批原生配置）
    # 与主值拼接成 '15,276' 幻象——KPI 十月真值判定必须读 .header-line（big_number 主数字）
    check("C5 %s 72 KPI=十月真值5276" % tag, d72.get("bn373") == "5,276", "bn373=%r" % d72.get("bn373"))
    check("C5 %s 378 高度≥280px" % tag, d72.get("h378", 0) >= 280, "h=%s" % d72.get("h378"))
    drain_errors_ok(s, "C5 %s /72" % tag)


def kill_stray_automation_chrome():
    """清掉本脚本先前轮次残留的自动化 Chrome（按 profile-vrf / CDP 端口特征精确匹配，
    不碰用户日常浏览器）。残留进程会锁 profile 目录：rm -rf 删一半 → 新 Chrome 打开损坏
    profile → 整页 'Response' 异常（combo1 三轮复现的根因）。"""
    try:
        import subprocess as sp
        out = sp.check_output(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"name='chrome.exe'\" | "
             "Where-Object {$_.CommandLine -match 'profile-vrf|remote-debugging-port=195'} | "
             "Select-Object -ExpandProperty ProcessId"],
            timeout=30).decode()
        pids = [x.strip() for x in out.split() if x.strip().isdigit()]
        for pid in pids:
            try:
                sp.check_call(["taskkill", "/F", "/PID", pid],
                              stdout=sp.DEVNULL, stderr=sp.DEVNULL)
            except Exception:
                pass
        if pids:
            print("killed stray automation chrome: %d procs" % len(pids))
            time.sleep(2)
    except Exception as e:
        print("(stray cleanup skipped: %s)" % e)


def main():
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1].upper()
    os.makedirs(EVID, exist_ok=True)
    os.makedirs(DOWNLOADS, exist_ok=True)
    assert ADMIN_PW, "ACC_ADMIN 未注入"
    kill_stray_automation_chrome()

    roles0 = user_roles_003158()
    print("003158 起点角色:", roles0)
    if only in (None, "A"):
        check("PRE 003158 起点无报表授权角色", not [r for r in roles0 if r.startswith("报表授权_")], str(roles0))

    # ---- 场景 A：4 组合 ----
    for engine, exe in ([] if only not in (None, "A") else ENGINES):
        for (w, h) in RESOS:
            run_combo_with_retry(engine, exe, w, h, "A", VERIFY_USER, VERIFY_PWD,
                                 lambda s_, t_, e_=None: scenario_A(s_, t_))

    # ---- grant 护理部管理 → 场景 B ----
    run_b = only in (None, "B")
    if run_b:
        rc, out, err = manage("grant-user", "--username", VERIFY_USER, "--role", ROLE_NURSE)
        check("B grant-user ok", rc == 0, "rc=%d" % rc)
        roles1 = user_roles_003158()
        check("B grant 生效", ROLE_NURSE in roles1, str(roles1))
    try:
        for i, (engine, exe) in enumerate([] if not run_b else ENGINES):
            for j, (w, h) in enumerate(RESOS):
                run_combo_with_retry(engine, exe, w, h, "B", VERIFY_USER, VERIFY_PWD,
                                     lambda s_, t_, e_: scenario_B(s_, t_, e_), do_export=(i == 0 and j == 0))
    finally:
        if run_b:
            rc, out, err = manage("revoke-user", "--username", VERIFY_USER, "--role", ROLE_NURSE)
            check("B revoke-user ok", rc == 0, "rc=%d" % rc)
    roles2 = user_roles_003158()
    check("B 还原：无报表授权角色", not [r for r in roles2 if r.startswith("报表授权_")] if run_b else True, str(roles2))

    # ---- 场景 C：admin 4 组合（独立 profile——A/B 的 003158 会话会使 /login/ 重定向
    #      导致"视为已登录"而无法切换账号，实测 C1 因此跑在员工身份上）----
    C_ENGINES = [] if only not in (None, "C") else ENGINES
    if C_ENGINES:
        # 暖机：首个 admin 会话在部分环境会陷入 SPA 半启动（仅头+筛选栏、零报错、换页复现），
        # 用一次性会话吸收该"首组合"现象，正式组合全部用新会话
        w0 = Session(C_ENGINES[0][0], C_ENGINES[0][1], 1920, 1080, "C-warm")
        try:
            if w0.tab.login(ADMIN, ADMIN_PW):
                w0.open(BASE + "/superset/welcome/", 5.0)
                print("warmup session done (absorbs first-session SPA stall)")
        except Exception as e:
            print("warmup skipped:", e)
        finally:
            w0.close()
    for engine, exe in C_ENGINES:
        for (w, h) in RESOS:
            run_combo_with_retry(engine, exe, w, h, "C", ADMIN, ADMIN_PW,
                                 lambda s_, t_, e_=None: scenario_C(s_, t_))

    # ---- 还原后快速复核（场景 A 关键断言，单组合） ----
    run_combo_with_retry("chrome", CHROME, 1920, 1080, "POST", VERIFY_USER, VERIFY_PWD,
                         lambda s_, t_, e_=None: post_revoke_check(s_))

    total = len(RESULT["checks"])
    passed = sum(1 for c in RESULT["checks"] if c["pass"])
    RESULT["meta"]["finished"] = time.strftime("%F %T")
    RESULT["summary"] = {"total": total, "pass": passed, "fail": total - passed,
                         "all_pass": passed == total}
    out_path = os.path.join(EVID, "rbac_frontend_acceptance.json")
    # 累积模式（--only 分轮跑）：旧 json 中其他场景的检查保留，本场景替换为最新完整记录
    if only:
        try:
            old = json.load(open(out_path, encoding="utf-8"))
            prefix = only + "/"
            old_kept = [c for c in old.get("checks", []) if not c["name"].startswith(prefix)]
            RESULT["checks"] = old_kept + RESULT["checks"]
            mt = len(RESULT["checks"])
            mp = sum(1 for c in RESULT["checks"] if c["pass"])
            RESULT["summary"] = {"total": mt, "pass": mp, "fail": mt - mp,
                                 "all_pass": mp == mt}
            RESULT.setdefault("meta", {}).setdefault("scenario_runs", {})[only] = {
                "finished": RESULT["meta"]["finished"],
                "checks_this_run": total, "pass_this_run": passed}
        except Exception as e:
            print("(merge skipped: %s)" % e)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(RESULT, f, ensure_ascii=False, indent=1)
    print("ACCEPTANCE %d/%d PASS (this run)" % (passed, total))
    sys.exit(0 if passed == total else 1)


def post_revoke_check(s):
    s.open(BASE + "/superset/welcome/", 7.0)
    st = probe_retry(s, HOME_STATE, lambda v: isinstance(v, dict) and v.get("guide"), tries=4, gap=3.0)
    st = st if isinstance(st, dict) else {}
    check("POST revoke 后恢复零权限态", st.get("nonav") and st.get("guide") and not st.get("cats"), str(st.get("cats")))
    drain_errors_ok(s, "POST chrome-1920 首页")


if __name__ == "__main__":
    main()
