# -*- coding: utf-8 -*-
"""20261107-BI-DASHBOARDS 前端三件升级：home-ui 20261107h8 / report-ui 20261107f12 / report-dates 20261107d14。
绝对增量：只新增 BI 分区/入口条/适配逻辑，不动既有功能。执行后 node --check 校验。"""
import io
import re

ROOT = "F:/python/superset/offline-bundle/custom/"
BI_LINKS_JS = ("var BI_LINKS=["
               "['全院医疗运营核心指标总览','/superset/dashboard/72/','KPI 总览 · 科室 TOP15 · 转归构成'],"
               "['门急诊流量与窗口负荷监测中心','/superset/dashboard/73/','四窗口人次 · 分时段波峰'],"
               "['手术与住院医疗质量可视化分析','/superset/dashboard/74/','手术分布 · 病区质量排行']];")


def patch(path, subs, expect_versions):
    p = ROOT + path
    s = io.open(p, encoding="utf-8").read()
    for old, new in subs:
        assert old in s, "NOT FOUND in %s: %r" % (path, old[:80])
        s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8", newline="").write(s)
    for v in expect_versions:
        assert v in s, "version missing: %s" % v
    print("patched", path, "→", expect_versions)


# ---------- home-ui.js → 20261107h8 ----------
home_subs = [
# 版本号
    ("hospitalHomeUI={version:'20261104h7'}", "hospitalHomeUI={version:'20261107h8'}"),
    # BI 常量（QUERY_SUMMARY 行后）
    ("var GENERIC_DESC='设置查询条件，查看报表结果';",
     "var GENERIC_DESC='设置查询条件，查看报表结果';\n"
     "  /* 可视化驾驶舱（20261107h8）：3 个 BI 看板已 published+Gamma，全员可见 */\n"
     "  " + BI_LINKS_JS),
    # buildNav：工作台之后插入 BI 分区
    ("""    var work=node('a','hh-home-nav-item hh-home-nav-active','工作台');
    work.href='/superset/welcome/';work.setAttribute('aria-current','page');work.title='工作台';
    nav.appendChild(work);
    nav.appendChild(node('div','hh-home-nav-section','报表分类'));""",
     """    var work=node('a','hh-home-nav-item hh-home-nav-active','工作台');
    work.href='/superset/welcome/';work.setAttribute('aria-current','page');work.title='工作台';
    nav.appendChild(work);
    /* 📊 可视化驾驶舱（20261107h8）：置顶分区，工作台下方、报表分类上方 */
    nav.appendChild(node('div','hh-home-nav-section hh-home-nav-section-bi','可视化驾驶舱'));
    Array.prototype.forEach.call(BI_LINKS,function(b){
      var a=node('a','hh-home-nav-item hh-home-nav-bi');a.href=b[1];a.title=b[0];
      a.appendChild(node('span','hh-home-nav-label',b[0]));
      a.appendChild(node('span','hh-home-nav-count','BI'););
      a.setAttribute('data-hh-bi-link',b[1]);nav.appendChild(a);
    });
    nav.appendChild(node('div','hh-home-nav-section','报表分类'));"""),
    # directoryTree：末尾追加 BI showcase（在 kybGroup(); 之前）
    ("""    kybGroup();
    ensureDirectorySearch();
    applyDirectoryFilter();
  }""",
     """    kybGroup();
    ensureBiShowcase();
    ensureDirectorySearch();
    applyDirectoryFilter();
  }
  /* 34 目录顶部：可视化驾驶舱三列入口条（20261107h8） */
  function ensureBiShowcase(){
    var md=document.querySelector('.dashboard-markdown');if(!md)return;
    var old=document.getElementById('hh-bi-showcase');
    if(old&&old.parentElement===md)return;
    if(old)old.remove();
    var box=node('div');box.id='hh-bi-showcase';box.className='hh-bi-showcase';
    Array.prototype.forEach.call(BI_LINKS,function(b){
      var a=node('a','hh-bi-card');a.href=b[1];a.title=b[0];
      var t=node('span','hh-bi-card-title','📊 '+b[0]);
      var d=node('span','hh-bi-card-desc',b[2]);
      a.appendChild(t);a.appendChild(d);box.appendChild(a);
    });
    var list=md.querySelector('ul');
    var wrap=md.querySelector('#hh-dir-search-wrap');
    if(wrap&&wrap.parentElement===md)wrap.insertBefore(box,wrap.firstChild.nextSibling?wrap.childNodes[1]:null)||0;
    if(!box.parentElement){
      if(list)md.insertBefore(box,list);
      else md.appendChild(box);
    }
  }"""),
]
# ensureBiShowcase 中插入位置更稳妥：搜索框 wrap 之后
home_subs[-1] = (home_subs[-1][0], home_subs[-1][1].replace(
    "if(wrap&&wrap.parentElement===md)wrap.insertBefore(box,wrap.firstChild.nextSibling?wrap.childNodes[1]:null)||0;\n    if(!box.parentElement){",
    "if(wrap&&wrap.parentElement===md&&wrap.nextSibling){md.insertBefore(box,wrap.nextSibling);}\n    if(!box.parentElement){"))

patch("home-ui.js", home_subs, ["20261107h8"])

# ---------- report-ui.js → 20261107f12 ----------
report_subs = [
    ("/* 报表目录与查询页显示增强。仅作用于已迁移页面；不修改查询结果和访问权限。",
     "/* 报表目录与查询页显示增强。仅作用于已迁移页面；不修改查询结果和访问权限。\n"
     "   20261107f12（BI-DASHBOARDS 批）：看板 72/73/74（可视化 BI 驾驶舱）接入查询页体系——明亮底色、\n"
     "   面包屑固定「报表目录/可视化驾驶舱/标题」、卡片白底细边框圆角（html.hh-bi-page）；\n"
     "   sliceTitleDedup 与 .hh-query-toolbar 仅在单图表页触发（多图表 BI 看板自动跳过，保留子图标题）。"),
    ("window.hospitalReportUI = { version: '20261106f11' };",
     "window.hospitalReportUI = { version: '20261107f12' };\n"
     "  var BI_DASH_IDS = [72, 73, 74]; /* 可视化驾驶舱（20261107f12） */"),
    # pageState：BI 页加入 hh-report-page + hh-bi-page
    ("""    document.documentElement.classList.toggle('hh-directory', !editing && categories.indexOf(id) >= 0);
    document.documentElement.classList.toggle('hh-report-page', !editing && (id === 2 || id === 32 || (id >= 35 && id <= 70)));""",
     """    var biPage = !editing && BI_DASH_IDS.indexOf(id) >= 0;
    document.documentElement.classList.toggle('hh-directory', !editing && categories.indexOf(id) >= 0);
    document.documentElement.classList.toggle('hh-report-page', !editing && (id === 2 || id === 32 || (id >= 35 && id <= 70) || biPage));
    document.documentElement.classList.toggle('hh-bi-page', biPage);"""),
    # crumb：BI 页固定层级
    ("""    } else if (id >= 61 && id <= 70) {""",
     """    } else if (BI_DASH_IDS.indexOf(id) >= 0) {
      /* 可视化驾驶舱（20261107f12）：固定中间层“可视化驾驶舱” */
      box.appendChild(seg('报表目录', '/superset/dashboard/34/'));
      box.appendChild(sep());
      box.appendChild(seg('可视化驾驶舱', null));
      box.appendChild(sep());
      box.appendChild(seg(title, null));
    } else if (id >= 61 && id <= 70) {"""),
    # queryToolbar：BI 页跳过
    ("  function queryToolbar() {\n    var on = isQueryPage() && pageId() !== 32;",
     "  function queryToolbar() {\n    var on = isQueryPage() && pageId() !== 32 && BI_DASH_IDS.indexOf(pageId()) < 0; /* 多图表 BI 看板不注入单表工具条 */"),
    # BI 卡片 CSS（追加到 hh-density-compact 规则后）
    ("    'html.hh-density-compact .superset-chart-table td *{line-height:24px!important}',",
     """    'html.hh-density-compact .superset-chart-table td *{line-height:24px!important}',
    /* 可视化 BI 驾驶舱卡片样式（20261107f12）：白底细边框圆角 */
    'html.hh-bi-page .dashboard-component-chart-holder{background:#fff!important;border:1px solid #e4e9ef!important;border-radius:6px!important;box-shadow:none!important}',
    'html.hh-bi-page .dashboard-markdown .dashboard-component{padding:6px 12px!important;border-left:3px solid #246598;background:#f0f6fc;border-radius:6px;font-size:13px;line-height:24px;white-space:nowrap;overflow:auto!important}',
    'html.hh-bi-page .dashboard-component-chart-holder [data-test="slice-header"]{font-size:15px;color:#153f66;border-bottom:1px solid #edf1f6;padding-bottom:6px;margin-bottom:6px}',"""),
]
patch("report-ui.js", report_subs, ["20261107f12"])

# ---------- report-dates.js → 20261107d14 ----------
dates = io.open(ROOT + "report-dates.js", encoding="utf-8").read()
old_ver = re.search(r"hospitalDateUI=\{version:'([0-9a-z]+)'\}", dates)
assert old_ver, "date version not found"
old_ver = old_ver.group(1)
dates = dates.replace("hospitalDateUI={version:'%s'}" % old_ver, "hospitalDateUI={version:'20261107d14'}")
m = re.search(r"(61:\{gran:'range',quick:'month'\}),62:", dates)
assert m, "CONTRACT anchor not found"
dates = dates.replace("61:{gran:'range',quick:'month'},62:",
                      "61:{gran:'range',quick:'month'},72:{gran:'range',quick:'month'},73:{gran:'day',quick:'day'},74:{gran:'range',quick:'month'},62:", 1)
old_is = "return n===2||n===32||(n>=35&&n<=70);"
assert old_is in dates
dates = dates.replace(old_is, "return n===2||n===32||(n>=35&&n<=70)||(n>=72&&n<=74);")
io.open(ROOT + "report-dates.js", "w", encoding="utf-8", newline="").write(dates)
print("patched report-dates.js → 20261107d14")
