# -*- coding: utf-8 -*-
"""二分定位 /72 No-filter 行为的肇事 JS：临时换旧版（f15 / h17 / 20261009d）逐个测。"""
import base64
import gzip
import os
import sys
import time

sys.path.insert(0, r"F:\python\superset\migration\tools")
import remote_exec
from remote_exec import run

import verify_rbac_frontend_polish as V  # noqa: E402

BEFORE = r"F:\python\superset\migration\sources\20261121-RBAC-FRONTEND-POLISH\before-assets"
CURRENT = r"F:\python\superset\offline-bundle\custom"
TARGETS = [
    ("report-ui.js", os.path.join(BEFORE, "report-ui.js"), "/home/superset/custom/report-ui.js"),
    ("home-ui.js", os.path.join(BEFORE, "home-ui.js"), "/home/superset/custom/home-ui.js"),
    ("roles-zh.js", os.path.join(BEFORE, "roles-zh.js"), "/home/superset/custom/roles-zh.js"),
]


def put(tgt, local, remote):
    with open(local, "rb") as f:
        data = base64.b64encode(gzip.compress(f.read(), 9)).decode("ascii")
    rc, out, err = run(tgt, "base64 -d <<'__HHB64__' | gunzip > %s\n%s\n__HHB64__\nmd5sum %s" % (remote, data, remote), timeout=300)
    assert rc == 0, out + err
    rc, out, err = run(tgt, "docker exec superset-nginx nginx -s reload", timeout=60)
    time.sleep(1)


def put_current(tgt, name):
    local = os.path.join(CURRENT, name)
    remote = "/home/superset/custom/" + name
    with open(local, "rb") as f:
        data = base64.b64encode(gzip.compress(f.read(), 9)).decode("ascii")
    rc, out, err = run(tgt, "base64 -d <<'__HHB64__' | gunzip > %s\n%s\n__HHB64__\nmd5sum %s" % (remote, data, remote), timeout=300)
    rc, out, err = run(tgt, "docker exec superset-nginx nginx -s reload", timeout=60)
    time.sleep(1)


def test_72_window(tag):
    s = V.Session("chrome", V.CHROME, 1920, 1080, "bisect-" + tag)
    try:
        assert s.tab.login("admin", V.ADMIN_PW)
        s.open(V.BASE + "/superset/dashboard/72/", 10.0)
        time.sleep(5)
        tr = s.tab.eval(r"""(function(){
          var g=document.querySelector('[data-test="grid-content"]');
          if(!g)return 'no-grid';
          var k=Object.keys(g).filter(function(x){return x.indexOf('__reactFiber')===0;})[0];
          var f=g[k];
          while(f){var p=f.memoizedProps||{};var st=p.store||(p.value&&p.value.store);
            if(st&&st.getState){var ch=st.getState().charts||{};
              for(var c in ch){var t=(ch[c]&&ch[c].latestQueryFormData||{}).time_range;
                if(t)return String(t).slice(0,24);}}
            f=f.return;}
          return 'none';})()""")
        kpi = s.tab.eval(r"""(function(){var h=document.querySelector('.dashboard-chart-id-373');return h?(h.textContent||'').replace(/\s+/g,' ').slice(0,30):'';})()""")
        print("  [%s] first-chart TR=%r KPI373=%r" % (tag, tr, kpi), flush=True)
        return tr
    finally:
        s.close()


def main():
    jb, tgt = remote_exec.connect()
    try:
        print("baseline (h18/f16/d2):", flush=True)
        test_72_window("base")
        for name, local, remote in TARGETS:
            print("swap OLD %s ..." % name, flush=True)
            put(tgt, local, remote)
            tr = test_72_window("old-" + name)
            if tr and tr.find("2026-10-01") >= 0:
                print(">>> CULPRIT: %s（换回旧版后 72 默认窗恢复 2026-10）" % name, flush=True)
            put_current(tgt, name)
            print("restored current %s" % name, flush=True)
    finally:
        tgt.close()
        jb.close()


if __name__ == "__main__":
    main()
