# -*- coding: utf-8 -*-
"""20261107-BI-DASHBOARDS T1③ 止损修复：目录34入口条/搜索框、73 单日契约、BI slug 别名。
版本号按计划 §5.3 保持 h8/f12/d14 不变（/custom/ no-cache，原位更新）。执行后 node --check 校验。"""
import io

ROOT = "F:/python/superset/offline-bundle/custom/"


def patch(path, subs):
    p = ROOT + path
    s = io.open(p, encoding="utf-8").read()
    for old, new in subs:
        assert old in s, "NOT FOUND in %s: %r" % (path, old[:80])
        assert s.count(old) == 1, "NOT UNIQUE in %s: %r" % (path, old[:80])
        s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8", newline="").write(s)
    print("patched", path, "(%d subs)" % len(subs))


# ---------- home-ui.js（h8 修复，版本不变） ----------
home_subs = [
    # 1) 调用顺序：搜索框先建，入口条随后落在搜索框与分类列表之间
    ("""    kybGroup();
    ensureBiShowcase();
    ensureDirectorySearch();
    applyDirectoryFilter();""",
     """    kybGroup();
    ensureDirectorySearch();
    ensureBiShowcase();
    applyDirectoryFilter();"""),
    # 2) ensureBiShowcase 重写：父节点插入 + 幂等 + try/catch
    ("""  /* 34 目录顶部：可视化驾驶舱三列入口条（20261107h8） */
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
    if(wrap&&wrap.parentElement===md&&wrap.nextSibling){md.insertBefore(box,wrap.nextSibling);}
    if(!box.parentElement){
      if(list)md.insertBefore(box,list);
      else md.appendChild(box);
    }
  }""",
     """  /* 34 目录顶部：可视化驾驶舱三列入口条（20261107h8 修复：插列表父节点、搜索框先行、幂等+try/catch） */
  function ensureBiShowcase(){
    try{
      var md=document.querySelector('.dashboard-markdown');if(!md)return;
      var list=md.querySelector('ul');if(!list)return;
      var old=document.getElementById('hh-bi-showcase');
      if(old&&old.nextElementSibling===list)return;
      if(old)old.remove();
      var box=node('div');box.id='hh-bi-showcase';box.className='hh-bi-showcase';
      Array.prototype.forEach.call(BI_LINKS,function(b){
        var a=node('a','hh-bi-card');a.href=b[1];a.title=b[0];
        var t=node('span','hh-bi-card-title','📊 '+b[0]);
        var d=node('span','hh-bi-card-desc',b[2]);
        a.appendChild(t);a.appendChild(d);box.appendChild(a);
      });
      /* ul 不一定是 .dashboard-markdown 直接子节点：插到列表父节点，即落在搜索框与分类列表之间 */
      list.parentNode.insertBefore(box,list);
    }catch(e){/* 入口条自身失败不再拖垮搜索框与目录 */}
  }"""),
    # 3) 入口条与侧栏 BI 分区样式（追加在目录搜索框样式后）
    ("""      '.hh-dir-search-wrap{margin:0 0 10px}',
      '.hh-dir-search-wrap #hh-report-search{display:block}',""",
     """      '.hh-dir-search-wrap{margin:0 0 10px}',
      '.hh-dir-search-wrap #hh-report-search{display:block}',
      /* 可视化驾驶舱入口条（34 目录）：三列网格、卡片 56px 蓝左边框 */
      '.hh-bi-showcase{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:0 0 12px}',
      '.hh-bi-card{display:flex;flex-direction:column;justify-content:center;gap:2px;height:56px;padding:0 12px;background:#fff;border:1px solid #e4e9ef;border-left:3px solid #1677c8;border-radius:6px;text-decoration:none;box-sizing:border-box;min-width:0}',
      '.hh-bi-card:hover{background:#f3f8fc}',
      '.hh-bi-card .hh-bi-card-title{font-size:14px;font-weight:600;color:#263445;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '.hh-bi-card .hh-bi-card-desc{font-size:12px;color:#909399;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      /* 首页侧栏「可视化驾驶舱」分区标题：蓝色小标识 */
      'html.hh-home #hh-home-nav .hh-home-nav-section-bi{display:flex;align-items:center;gap:6px;font-weight:600;color:var(--hh-blue)}',
      'html.hh-home #hh-home-nav .hh-home-nav-section-bi::before{content:"";flex:none;width:4px;height:12px;border-radius:2px;background:var(--hh-blue)}',"""),
]
patch("home-ui.js", home_subs)

# ---------- report-dates.js（d14 修复，版本不变） ----------
patch("report-dates.js", [
    ("73:{gran:'day',quick:'day'}", "73:{gran:'sameday',quick:'day'}"),
])

# ---------- report-ui.js（f12 修复，版本不变） ----------
patch("report-ui.js", [
    ("""    '/superset/dashboard/month-work-report-new/': 32,
    '/superset/dashboard/mr-discharge-death-detail/': 2
  };""",
     """    '/superset/dashboard/month-work-report-new/': 32,
    '/superset/dashboard/mr-discharge-death-detail/': 2,
    '/superset/dashboard/bi-overview/': 72,
    '/superset/dashboard/bi-outpatient-flow/': 73,
    '/superset/dashboard/bi-surgery-quality/': 74
  };"""),
])

print("done")
