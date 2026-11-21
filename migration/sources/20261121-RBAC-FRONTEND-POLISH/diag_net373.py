# -*- coding: utf-8 -*-
"""抓 /72 页面 chart/data 网络响应体：浏览器收到的 373 值与请求 TR。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_rbac_frontend_polish as V


def main():
    s = V.Session("chrome", V.CHROME, 1920, 1080, "diag-net")
    recs = {}
    try:
        assert s.tab.login("admin", V.ADMIN_PW)
        orig = s.tab.send

        def send2(method, params=None, timeout=90):
            r = orig(method, params, timeout)
            for ev in s.tab.drain():
                if ev.get("method") == "Network.requestWillBeSent":
                    req = ev["params"].get("request", {})
                    if "/api/v1/chart/data" in req.get("url", ""):
                        recs[ev["params"]["requestId"]] = {"tr": "", "val": None, "post": req.get("postData", "")[:80]}
                        try:
                            body = json.loads(req.get("postData", "{}"))
                            trs = set()
                            for q in body.get("queries", []):
                                trs.add(str(q.get("time_range", "")))
                            recs[ev["params"]["requestId"]]["tr"] = ",".join(sorted(trs))
                            sid = (body.get("form_data") or {}).get("slice_id")
                            recs[ev["params"]["requestId"]]["sid"] = sid
                        except Exception:
                            pass
                elif ev.get("method") == "Network.loadingFinished":
                    rid = ev["params"]["requestId"]
                    if rid in recs and recs[rid].get("sid") == 373:
                        try:
                            b = orig("Network.getResponseBody", {"requestId": rid}, timeout=20)
                            txt = b.get("body", "")
                            if b.get("base64Encoded"):
                                import base64 as b64
                                txt = b64.b64decode(txt).decode("utf-8", "replace")
                            j = json.loads(txt)
                            recs[rid]["val"] = (j.get("result") or [{}])[0].get("data")
                            recs[rid]["cached"] = (j.get("result") or [{}])[0].get("is_cached")
                        except Exception as e:
                            recs[rid]["val"] = "ERR %s" % e
            return r
        s.tab.send = send2
        s.open(V.BASE + "/superset/dashboard/72/", 12.0)
        time.sleep(10)
        for rid, r in recs.items():
            if r.get("sid") == 373 or "sid" not in r:
                print(r)
    finally:
        s.close()


if __name__ == "__main__":
    main()
