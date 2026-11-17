# -*- coding: utf-8 -*-
"""20261112-WARMUP-PERF 任务1验收：59/39/58/62 跨度守卫端到端测试（真实 UI 交互）。

场景：
  A  59：日期 44 天 + visit_id 1~99 → 点击查询被拦截（#hdt-visit-msg 红），无 chart/data POST
  B  59：日期 13 天 + visit_id 1~99 → #hdt-span-tip 橙色软提示；点击查询放行（有 POST，随即离开）
  C  59：日期 7 天 + visit_id 1~5  → 无软提示；点击查询放行（有 POST，随即离开）
  D  39：日期 44 天 → #hdt-span-tip 橙色软提示（不提交）
  E  58：分支=门诊 + 日期 44 天 → #hdt-span-tip 橙色软提示（不提交）
  F  62：日期 30 天 → 点击查询被拦截（g4 回归，15 天上限），无 POST
输出 guard-test-<tag>.json。
"""
import argparse
import json
import os
import time

import websocket

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wb_run import Tab, NetTracker, launch, new_tab  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "http://127.0.0.1:18180"

SET_DATE = """(function(fid,a,b){
  var holder=fid?document.querySelector('.hdt-picker[data-filter-id="'+fid+'"]')
                :document.querySelector('.hdt-picker[data-mode=range]');
  if(!holder)return 'no-holder';
  var inp=holder.querySelector('input');
  var fp=inp&&inp._flatpickr;
  if(!fp)return 'no-flatpickr';
  fp.setDate([a,b],true);
  return 'ok '+a+'..'+b+'@'+holder.getAttribute('data-filter-id');
})("%s","%s","%s")"""

SEL_OPT = """(function(id,title){
  var input=document.getElementById(id);
  if(!input)return 'no-input';
  var sel=input.closest('.ant-select');
  if(!sel)return 'no-select';
  sel.dispatchEvent(new MouseEvent('mousedown',{bubbles:true}));
  sel.dispatchEvent(new MouseEvent('click',{bubbles:true}));
  return 'opened';
})("%s","%s")"""

PICK_OPT = """(function(title){
  var dd=document.querySelectorAll('.ant-select-dropdown:not(.ant-select-dropdown-hidden)');
  if(!dd.length)return 'no-dropdown';
  var opts=dd[dd.length-1].querySelectorAll('.ant-select-item-option');
  for(var i=0;i<opts.length;i++){
    var t=(opts[i].getAttribute('title')||opts[i].textContent||'').trim();
    if(t===title){opts[i].dispatchEvent(new MouseEvent('mousedown',{bubbles:true}));opts[i].click();return 'picked '+t;}
  }
  return 'no-option:'+title+'('+opts.length+')';
})("%s")"""



TYPE_SEARCH = """(function(id,q){
  var i=document.getElementById(id);if(!i)return 'no-input';
  i.focus();
  var set=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
  set.call(i,q);
  i.dispatchEvent(new Event('input',{bubbles:true}));
  return 'typed '+q;
})("%s","%s")"""

BRIDGE_SET = """(function(id,val){
  var input=document.getElementById(id);
  if(!input)return 'no-input';
  var k=Object.keys(input).find(function(k){return k.indexOf('__reactFiber')===0;});
  if(!k)return 'no-fiber';
  var f=input[k];
  while(f){var p=f.memoizedProps||{};
    if(p.name===id&&typeof p.onChange==='function'&&('value' in p)){p.onChange(val);return 'set '+id+'='+val;}
    f=f.return;}
  return 'no-bridge';
})("%s","%s")"""

DRAFTS = """(function(){
  var g=window.hospitalVisitGuard||{};
  var d1,d2;
  try{d1=g.dateSpace?null:null;}catch(e){}
  var ui=window.hospitalDateUI;
  var spans=[];
  document.querySelectorAll('.hdt-picker[data-filter-id]').forEach(function(p){
    spans.push({fid:p.getAttribute('data-filter-id'),draft:ui&&ui.draftFor?ui.draftFor(p.getAttribute('data-filter-id')):undefined});
  });
  return JSON.stringify({span:g.dateSpan?g.dateSpan():null,tip:document.getElementById('hdt-span-tip')?document.getElementById('hdt-span-tip').textContent:null,
    msg:document.getElementById('hdt-visit-msg')?document.getElementById('hdt-visit-msg').textContent:null,pickers:spans});
})()"""


def nav(tab, did, wait_s=14):
    tab.send("Page.navigate", {"url": BASE + "/superset/dashboard/%d/" % did})
    time.sleep(2.5)
    for _ in range(30):
        if tab.eval("document.readyState") == "complete":
            break
        time.sleep(0.5)
    # 等筛选条+日历就绪
    for _ in range(wait_s * 2):
        n = tab.eval("(document.querySelectorAll('.hdt-picker[data-filter-id]').length)||0")
        bar = tab.eval("(document.querySelector('[data-test=\"filter-bar\"]')?1:0)")
        if n and bar:
            time.sleep(2.5)  # 日历元数据与 React 草稿稳定
            return True
        time.sleep(1)
    return False


def click_apply(tab):
    return tab.eval("(function(){var b=document.querySelector('[data-test=\"filter-bar__apply-button\"]');if(!b)return 'no-btn';if(b.disabled)return 'disabled';b.click();return 'clicked';})()")


def read_state(tab):
    return json.loads(tab.eval(DRAFTS))


def open_select(tab, fid):
    return tab.eval("""(function(id){
      var i=document.getElementById(id);if(!i)return 'no-input';
      var s=i.closest('.ant-select').querySelector('.ant-select-selector');
      if(!s)return 'no-selector';
      ['pointerdown','mousedown','pointerup','mouseup','click'].forEach(function(t){
        s.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window}));});
      return 'opened';})("%s")""" % fid)


def pick_option(tab, title, tries=24):
    """在下拉里找并点选目标项；虚拟列表按步滚动。"""
    r = "not-run"
    for _ in range(tries):
        r = tab.eval("""(function(title){
          var dd=document.querySelectorAll('.ant-select-dropdown:not(.ant-select-dropdown-hidden)');
          if(!dd.length)return 'no-dropdown';
          var d=dd[dd.length-1];
          var opts=d.querySelectorAll('.ant-select-item-option');
          for(var j=0;j<opts.length;j++){
            if((opts[j].textContent||'').trim()===title){
              ['pointerdown','mousedown','pointerup','mouseup','click'].forEach(function(t){
                opts[j].dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window}));});
              return 'picked '+title;}}
          var h=d.querySelector('.rc-virtual-list-holder');
          if(h)h.scrollTop=h.scrollTop+120;
          return 'scroll:'+opts.length;})("%s")""" % title)
        if r.startswith("picked") or r.startswith("no-input"):
            return r
        time.sleep(0.4)
    return r


def set_visit(tab, low, high):
    open_select(tab, "NATIVE_FILTER-P59-V1")
    time.sleep(0.8)
    tab.eval(TYPE_SEARCH % ("NATIVE_FILTER-P59-V1", str(low)))
    time.sleep(0.6)
    p1 = pick_option(tab, str(low), tries=8)
    time.sleep(1.0)
    open_select(tab, "NATIVE_FILTER-P59-V2")
    time.sleep(0.8)
    tab.eval(TYPE_SEARCH % ("NATIVE_FILTER-P59-V2", str(high)))
    time.sleep(0.6)
    p2 = pick_option(tab, str(high), tries=8)
    time.sleep(2.0)
    return (p1, p2)


def flush(tracker, tab):
    tab.eval("1+1")
    tracker.poll()


def count_posts(tab, tracker, secs=3.5):
    t0 = time.time()
    while time.time() - t0 < secs:
        tab.eval("1+1")
        tracker.poll()
        time.sleep(0.5)
    return tracker.snapshot()["sent"]


def run(tag, exe, port, admin):
    proc, ver = launch(exe, tag + "-gt", port)
    info = new_tab(port)
    ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=30)
    tab = Tab(ws)
    tab.send("Page.enable")
    tab.send("Network.enable", {"maxPostDataSize": 262144})
    tr = NetTracker(tab)
    ok = tab.login("admin", admin)
    results = {"browser": ver, "login": ok, "cases": []}

    def case(name, checks):
        row = {"case": name, "checks": checks, "pass": all(c[1] for c in checks)}
        results["cases"].append(row)
        print(("PASS " if row["pass"] else "FAIL ") + name + " " +
              "; ".join("%s=%s" % (c[0], "ok" if c[1] else "BAD:" + str(c[2])) for c in checks), flush=True)

    # --- 场景 A：59 拦截 ---
    if nav(tab, 59):
        tab.eval(SET_DATE % ("NATIVE_FILTER-P59-DATE", "2026-10-01", "2026-11-13"))
        time.sleep(1.0)
        setres = set_visit(tab, 1, 99)
        st = read_state(tab)
        flush(tr, tab)
        tr.reset()
        click = click_apply(tab)
        posts = count_posts(tab, tr)
        # 拦截后允许筛选条自身内务请求（filter_select 选项/filter_time 预览），
        # 但不得出现任何图表查询 POST（slice 321 = 44 天 PIVOT 慢查询）
        query_posts = 0
        qdetails = []
        for rid, rec in tr.done.items():
            try:
                j = json.loads(rec.get("post") or "{}")
                fd = j.get("form_data") or {}
                if fd.get("slice_id") or fd.get("viz_type") not in ("filter_select", "filter_time"):
                    query_posts += 1
                    qdetails.append("%s/%s" % (fd.get("viz_type"), fd.get("slice_id")))
            except Exception:
                pass
        case("A-59-block-44d", [
            ("guard_v", tab.eval("(window.hospitalVisitGuard||{}).version") == "20261112g5", tab.eval("(window.hospitalVisitGuard||{}).version")),
            ("visit_set", all(str(s).startswith("picked") for s in setres), setres),
            ("span44", isinstance(st.get("span"), dict) and st["span"].get("days", 0) > 31, st.get("span")),
            ("click", click == "clicked", click),
            ("blocked_msg", (st.get("msg") or "") != "" or (read_state(tab).get("msg") or "") != "", read_state(tab).get("msg")),
            ("msg_text", (read_state(tab).get("msg") or "").find("31") >= 0, read_state(tab).get("msg")),
            ("no_query_post", query_posts == 0, qdetails),
        ])
    else:
        case("A-nav59", [("nav", False, "timeout")])

    # --- 场景 B：59 软提示 + 放行 ---
    tab.eval(SET_DATE % ("NATIVE_FILTER-P59-DATE", "2026-11-01", "2026-11-13"))
    time.sleep(2.5)
    st = read_state(tab)
    tip_b = st.get("tip") or ""
    flush(tr, tab)
    tr.reset()
    click = click_apply(tab)
    posts = count_posts(tab, tr, secs=4.0)
    case("B-59-soft-13d-wide-visit", [
        ("tip_shown", tip_b.find("耐心等待") >= 0 and tip_b.find("20~50") >= 0, tip_b),
        ("tip_orange", tab.eval("(function(){var t=document.getElementById('hdt-span-tip');return t?getComputedStyle(t).color:''})()").find("212, 107, 8") >= 0,
         tab.eval("(function(){var t=document.getElementById('hdt-span-tip');return t?getComputedStyle(t).color:''})()")),
        ("click", click == "clicked", click),
        ("post_fired", posts >= 1, posts),  # 不拦截：慢查询请求已发出
    ])
    try:
        tab.send("Page.navigate", {"url": "about:blank"})  # 立即离开，终止等待
    except Exception:
        pass
    time.sleep(4.0)

    # --- 场景 C：59 窄跨度无提示 + 放行 ---
    if nav(tab, 59):
        tab.eval(SET_DATE % ("NATIVE_FILTER-P59-DATE", "2026-11-07", "2026-11-13"))
        time.sleep(1.0)
        setres = set_visit(tab, 1, 5)
        st = read_state(tab)
        flush(tr, tab)
        tr.reset()
        click = click_apply(tab)
        posts = count_posts(tab, tr, secs=4.0)
        case("C-59-clean-7d", [
            ("tip_empty", not (st.get("tip") or ""), st.get("tip")),
            ("click", click == "clicked", click),
            ("post_fired", posts >= 1, posts),
        ])
        try:
            tab.send("Page.navigate", {"url": "about:blank"})
        except Exception:
            pass
        time.sleep(4.0)

    # --- 场景 D：39 软提示（不提交） ---
    if nav(tab, 39):
        tab.eval(SET_DATE % ("NATIVE_FILTER-UI-39-COMPAT-Z06-DATE", "2026-10-01", "2026-11-13"))
        time.sleep(1.5)
        st = read_state(tab)
        case("D-39-soft-44d", [
            ("tip_shown", (st.get("tip") or "").find("20~60") >= 0, st.get("tip")),
        ])
    # --- 场景 E：58 分支+大跨度软提示（不提交） ---
    if nav(tab, 58):
        tab.eval(open_select(tab, "NATIVE_FILTER-P58-BRANCH") and "1")
        time.sleep(1.0)
        br = pick_option(tab, "门诊")
        time.sleep(1.5)
        tab.eval(SET_DATE % ("", "2026-10-01", "2026-11-13"))
        time.sleep(1.5)
        st = read_state(tab)
        case("E-58-soft-44d", [
            ("branch_set", str(br).startswith("picked"), br),
            ("tip_shown", (st.get("tip") or "").find("20~60") >= 0, st.get("tip")),
        ])
    # --- 场景 F：62 g4 拦截回归 ---
    if nav(tab, 62):
        tab.eval(SET_DATE % ("", "2026-10-15", "2026-11-13"))
        time.sleep(1.0)
        flush(tr, tab)
        flush(tr, tab)
        tr.reset()
        click = click_apply(tab)
        posts = count_posts(tab, tr)
        st = read_state(tab)
        case("F-62-block-30d-regression", [
            ("click", click == "clicked", click),
            ("blocked_msg", (read_state(tab).get("msg") or "").find("15 天") >= 0, read_state(tab).get("msg")),
            ("no_post", posts == 0, posts),
        ])

    ws.close()
    proc.terminate()
    time.sleep(1.5)
    proc.kill()
    out = os.path.join(HERE, "guard-test-%s.json" % tag)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    npass = sum(1 for c in results["cases"] if c["pass"])
    print("saved %s  %d/%d cases pass" % (out, npass, len(results["cases"])), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--exe", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--admin", default=os.environ.get("ACC_ADMIN", ""))
    a = ap.parse_args()
    run(a.tag, a.exe, a.port, a.admin)
