/* 20261104h7（NAV-SEARCH 批）：接入抗菌办分类与快速搜索。侧栏 8 分类下按权限追加“抗菌药物监测（10 项）”（Admin 或角色 343，探测 /api/v1/dashboard/61，无权限不渲染，不暴露死链）；
   34 目录末尾追加同构可展开虚拟分组 li[data-hh-cat-group="kyb"]（展开状态记入 sessionStorage，#kyb 锚点自动展开）；
   首页工作台与 34 目录新增紧凑搜索框（input#hh-report-search）：首页输入实时聚合 categoryCache 弹出下拉浮层可跳转；34 目录输入时自动展开命中分类、只显示匹配报表行、清空恢复原展开状态；
   QUERY_SUMMARY 补 2 与 61–70，isQuery 范围扩到 35–70。样式沿用企业后台列表规范，不改业务链接、权限或查询。
   20261026h6：在 h5 基础上优化左侧导航与目录层级/间距。侧栏改为“报表导航+分类计数”，移除单字方块；34 目录按原生 position_json Markdown 生成“分类→报表”可展开层级（默认展开质控科，sessionStorage 记忆），无权限/失败不伪造内容。相关行高与留白提高至约44px，不恢复大卡片，不改业务链接、权限或查询。 */
(function () {
  'use strict';
  if (window.hospitalHomeUI) return;
  var api=window.hospitalHomeUI={version:'20261107h8'},pending=0,editGrid=null,editStore=null;
  var catalogs=[25,26,27,28,29,30,31,33,34];
  var NAV=[['质控科报表',33,'质'],['护理部报表',26,'护'],['月报',25,'月'],['门诊',27,'门'],['急诊',28,'急'],['手术',29,'术'],['门诊流量监测',30,'流'],['绩效考核监测',31,'绩']];
  var MGMT=[['dashboards','看板'],['charts','图表'],['queries','已保存查询']];
  var QUERY_SUMMARY={2:'出院日期',32:'日期',35:'月份',36:'日期',37:'日期+门诊/住院',39:'日期',40:'日期',41:'月份',42:'日期',43:'日期',44:'日期',45:'月份',46:'月份',47:'日期',48:'日期',49:'日期',50:'月份',51:'月份+科室',52:'月份+科室',53:'日期',54:'日期',55:'日期',56:'日期',57:'日期',58:'日期+门诊/住院',59:'日期+就诊次数上下限',60:'统计期间',61:'开单日期',62:'出院日期',63:'统计季度',64:'出院日期',65:'医嘱日期',66:'出院日期',67:'出院日期',68:'出院日期',69:'出院日期',70:'记录日期'};
  /* 抗菌办 10 张查询页（20261104h7）：清单固定，仅对 Admin / 角色 343 成员可见 */
  var KYB_REPORTS=[
    {id:61,name:'抗菌办·门急诊处方查询'},{id:62,name:'抗菌办·住院检验结果查询'},
    {id:63,name:'抗菌办·抗菌药物消耗查询（季度）'},{id:64,name:'抗菌办·住院患者信息查询'},
    {id:65,name:'抗菌办·住院医嘱查询'},{id:66,name:'抗菌办·微生物检验结果查询'},
    {id:67,name:'抗菌办·检查结果查询'},{id:68,name:'抗菌办·住院诊断查询'},
    {id:69,name:'抗菌办·手术记录查询（ODS）'},{id:70,name:'抗菌办·生命体征查询（ODS）'}
  ];
  var GENERIC_DESC='设置查询条件，查看报表结果';
  /* 可视化驾驶舱（20261107h8）：3 个 BI 看板已 published+Gamma，全员可见 */
  var BI_LINKS=[['全院医疗运营核心指标总览','/superset/dashboard/72/','KPI 总览 · 科室 TOP15 · 转归构成'],['门急诊流量与窗口负荷监测中心','/superset/dashboard/73/','四窗口人次 · 分时段波峰'],['手术与住院医疗质量可视化分析','/superset/dashboard/74/','手术分布 · 病区质量排行']];
  var categoryCache={},categoryPending={};
  var SS=window.sessionStorage;
  function ssGet(k){try{return SS?SS.getItem(k):null}catch(e){return null}}
  function ssSet(k,v){try{if(SS){if(v===null)SS.removeItem(k);else SS.setItem(k,v)}}catch(e){}}
  var recentAutoDone=false,programmatic=0,pollTimer=0;
  function isHome(){return location.pathname==='/'||/^\/superset\/welcome\/?$/.test(location.pathname);}
  function pageId(){var m=location.pathname.match(/^\/superset\/dashboard\/(\d+)\/?$/);return m?+m[1]:0;}
  function editing(){
    if(/(?:\?|&)edit=true/.test(location.search))return true;
    var grid=document.querySelector('[data-test="grid-content"]');
    if(grid!==editGrid||(grid&&!editStore)){
      editGrid=grid;editStore=null;
      var fiberKey=grid&&Object.keys(grid).filter(function(k){return k.indexOf('__reactFiber')===0;})[0],f=grid&&grid[fiberKey];
      while(f){var p=f.memoizedProps,s=p&&(p.store||(p.value&&p.value.store));if(s&&s.getState){editStore=s;break;}f=f.return;}
    }
    var state=editStore&&editStore.getState();return !!(state&&state.dashboardState&&state.dashboardState.editMode);
  }
  api.isEditing=editing;
  function isCatalog(){return catalogs.indexOf(pageId())>=0&&!editing();}
  function isQuery(){var id=pageId();return !editing()&&(id===2||id===32||(id>=35&&id<=70)||/^\/superset\/dashboard\/(?:mr-discharge-death-detail|month-work-report-new)\/?$/.test(location.pathname));}
  function isAdmin(){
    try{
      var app=document.getElementById('app'),raw=app&&app.getAttribute('data-bootstrap');
      if(!raw)return false;
      var data=JSON.parse(raw),u=data&&data.user,r=u&&u.roles;
      if(!r)return false;
      if(Array.isArray(r))return r.indexOf('Admin')>=0;
      return Object.prototype.hasOwnProperty.call(r,'Admin');
    }catch(e){return false;}
  }
  function node(tag,cls,text){var e=document.createElement(tag);if(cls)e.className=cls;if(text)e.textContent=text;return e;}
  function mark(e,name){if(e&&!e.hasAttribute(name)){e.setAttribute(name,'');return true;}return false;}
  function tooltip(e){if(!e)return;var text=e.textContent.trim();if(!e.hasAttribute('title')||e.hasAttribute('data-hh-own-title')){if(e.title!==text)e.title=text;mark(e,'data-hh-own-title');}}
  function removeById(id){var e=document.getElementById(id);if(e)e.remove();}
  function directoryAllowed(){return !!(window.hospitalReportUI&&window.hospitalReportUI.directoryAccess===true);}

  /* ---------- 抗菌办分类（20261104h7）：Admin 直通，其余探测看板 61 可达性 ---------- */
  function kybList(){
    return {reports:KYB_REPORTS.map(function(r){
      return {name:r.name,href:'/superset/dashboard/'+r.id+'/',description:QUERY_SUMMARY[r.id]?'查询条件：'+QUERY_SUMMARY[r.id]:''};
    })};
  }
  function checkKybAccess(){
    if(categoryCache.kybStatus)return;
    if(isAdmin()){
      categoryCache.kybStatus='ok';categoryCache.kyb=kybList();updateCounts('kyb');schedule();return;
    }
    categoryCache.kybStatus='pending';
    fetch('/api/v1/dashboard/61',{credentials:'same-origin'}).then(function(r){
      categoryCache.kybStatus=r.ok?'ok':'denied';
      if(r.ok)categoryCache.kyb=kybList();
      schedule();
    }).catch(function(){categoryCache.kybStatus='denied';schedule();});
  }
  function kybAllowed(){return categoryCache.kybStatus==='ok';}
  /* 首页侧栏：8 分类下方按权限追加“抗菌药物监测（10 项）”，无权限不渲染 */
  function updateKybNav(){
    var nav=document.getElementById('hh-home-nav');if(!nav)return;
    var item=document.getElementById('hh-home-nav-kyb');
    if(!kybAllowed()){if(item)item.remove();return;}
    if(item)return;
    var all=nav.querySelector('.hh-home-nav-all');
    item=node('a','hh-home-nav-item');item.id='hh-home-nav-kyb';item.href='/superset/dashboard/34/#kyb';
    item.title='抗菌药物监测（10 项专项查询）';
    item.appendChild(node('span','hh-home-nav-label','抗菌药物监测'));
    var count=node('span','hh-home-nav-count','10 项');count.setAttribute('data-hh-cat-count','kyb');count.setAttribute('aria-hidden','true');
    item.appendChild(count);
    nav.insertBefore(item,all);
  }
  /* 34 目录：末尾追加与原生分类同构的可展开虚拟分组；#kyb 锚点自动展开一次 */
  var kybHashOpened=false;
  function kybGroup(){
    var md=document.querySelector('.dashboard-markdown');if(!md)return;
    var list=md.querySelector('ul');if(!list)return;
    var li=list.querySelector('li[data-hh-cat-group="kyb"]');
    if(!kybAllowed()){if(li)li.remove();return;}
    if(li)return;
    li=node('li');
    var a=node('a');a.setAttribute('data-hh-catalog-name','');a.href='/superset/dashboard/34/#kyb';
    a.textContent='抗菌药物监测';a.title='抗菌药物监测';
    var d=node('span');d.setAttribute('data-hh-catalog-description','');
    d.textContent='门急诊处方、住院医嘱、微生物与检验检查等 10 项专项查询';d.title=d.textContent;
    li.appendChild(a);li.appendChild(d);
    list.appendChild(li);
    setupCategoryGroup(li,'kyb');
    if(location.hash==='#kyb'&&!kybHashOpened){
      kybHashOpened=true;setCategoryOpen('kyb',true);
      li.setAttribute('data-hh-open','1');
      var t=li.querySelector('.hh-cat-toggle');
      if(t){t.textContent='▾';t.setAttribute('aria-expanded','true');}
    }
    loadCategory('kyb');
  }

  /* ---------- 快速搜索（20261104h7）：首页下拉浮层 + 34 目录实时过滤 ---------- */
  var dirKw='',dropOutsideBound=false;
  function makeSearchInput(){
    var input=document.createElement('input');
    input.type='search';input.id='hh-report-search';
    input.setAttribute('placeholder','搜索报表名称或条件（如：手术、门诊、月报）…');
    input.setAttribute('aria-label','快速搜索报表');
    input.autocomplete='off';
    return input;
  }
  function searchIndex(){
    var out=[];
    function catName(id){for(var i=0;i<NAV.length;i++)if(NAV[i][1]===id)return NAV[i][0];return id==='kyb'?'抗菌药物监测':'';}
    function push(id,reports){
      (reports||[]).forEach(function(r){
        var rid=Number((r.href.match(/\/dashboard\/(\d+)\//)||[])[1]||0);
        out.push({name:r.name,href:r.href,cat:catName(id),cond:QUERY_SUMMARY[rid]||''});
      });
    }
    NAV.forEach(function(c){var d=categoryCache[c[1]];if(d&&d.reports)push(c[1],d.reports);});
    if(kybAllowed()&&categoryCache.kyb&&categoryCache.kyb.reports)push('kyb',categoryCache.kyb.reports);
    return out;
  }
  function ensureHomeSearch(){
    var hint=document.getElementById('hospital-home-hint');
    if(!hint||!directoryAllowed())return;
    if(document.getElementById('hh-search-wrap'))return;
    var wrap=node('span','hh-search-box');wrap.id='hh-search-wrap';
    var input=makeSearchInput();
    var drop=node('div','hh-search-dropdown');drop.id='hh-search-drop';drop.style.display='none';drop.setAttribute('role','listbox');
    wrap.appendChild(input);wrap.appendChild(drop);
    hint.insertBefore(wrap,hint.querySelector('.hh-home-primary')||null);
    function renderDrop(){
      var kw=input.value.trim().toLowerCase();
      NAV.forEach(function(c){loadCategory(c[1]);});
      if(!kw){drop.style.display='none';return;}
      var hits=searchIndex().filter(function(r){return (r.name+' '+r.cat+' '+r.cond).toLowerCase().indexOf(kw)>=0;});
      while(drop.firstChild)drop.removeChild(drop.firstChild);
      if(!hits.length){drop.appendChild(node('div','hh-search-empty','无匹配报表'));}
      else{
        hits.slice(0,30).forEach(function(r){
          var a=node('a','hh-search-row');a.href=r.href;a.setAttribute('role','option');
          var nm=node('span','hh-search-name',r.name);nm.title=r.name;
          a.appendChild(nm);
          var meta=node('span','hh-search-meta',(r.cat?r.cat:'')+(r.cat&&r.cond?' · ':'')+(r.cond||''));
          a.appendChild(meta);
          drop.appendChild(a);
        });
      }
      drop.style.display='block';
    }
    input.addEventListener('input',renderDrop);
    input.addEventListener('keydown',function(e){
      if(e.key==='Escape'){drop.style.display='none';e.stopPropagation();}
    });
    if(!dropOutsideBound){
      dropOutsideBound=true;
      document.addEventListener('click',function(e){
        var w=document.getElementById('hh-search-wrap');
        var d=document.getElementById('hh-search-drop');
        if(w&&!w.contains(e.target)&&d)d.style.display='none';
      },true);
    }
  }
  function ensureDirectorySearch(){
    if(pageId()!==34)return;
    var md=document.querySelector('.dashboard-markdown');if(!md)return;
    var list=md.querySelector('ul');if(!list)return;
    if(document.getElementById('hh-dir-search-wrap'))return;
    var wrap=node('div','hh-dir-search-wrap');wrap.id='hh-dir-search-wrap';
    var input=makeSearchInput();
    wrap.appendChild(input);
    list.parentNode.insertBefore(wrap,list);
    input.addEventListener('input',function(){dirKw=input.value.trim().toLowerCase();applyDirectoryFilter();});
    input.addEventListener('keydown',function(e){
      if(e.key==='Escape'&&input.value){input.value='';dirKw='';applyDirectoryFilter();}
    });
  }
  /* 34 目录过滤：命中分类强制展开、只显示匹配报表行；无命中分类临时隐藏；清空恢复 sessionStorage 展开状态 */
  function applyDirectoryFilter(){
    if(pageId()!==34)return;
    var groups=document.querySelectorAll('.dashboard-markdown li[data-hh-cat-group]');
    if(!dirKw){
      Array.prototype.forEach.call(groups,function(li){
        li.style.display='';
        var id=li.getAttribute('data-hh-cat-group');
        var open=openSet().indexOf(id)>=0;
        li.setAttribute('data-hh-open',open?'1':'0');
        var t=li.querySelector('.hh-cat-toggle');
        if(t){t.textContent=open?'▾':'▸';t.setAttribute('aria-expanded',open?'true':'false');}
        Array.prototype.forEach.call(li.querySelectorAll('.hh-cat-report'),function(a){a.style.display='';});
      });
      return;
    }
    Array.prototype.forEach.call(groups,function(li){
      var id=li.getAttribute('data-hh-cat-group'),d=categoryCache[id];
      if(!d||d.error){li.style.display='none';return;}
      var nameEl=li.querySelector('[data-hh-catalog-name]');
      var catHit=nameEl&&nameEl.textContent.toLowerCase().indexOf(dirKw)>=0;
      var hits=d.reports.filter(function(r){return catHit||((r.name+' '+(r.description||'')).toLowerCase().indexOf(dirKw)>=0);});
      if(!hits.length){li.style.display='none';return;}
      li.style.display='';
      li.setAttribute('data-hh-open','1');
      var t=li.querySelector('.hh-cat-toggle');
      if(t){t.textContent='▾';t.setAttribute('aria-expanded','true');}
      Array.prototype.forEach.call(li.querySelectorAll('.hh-cat-report'),function(a){
        var nm=a.querySelector('.hh-cat-report-name'),ds=a.querySelector('.hh-cat-report-desc');
        var txt=((nm?nm.textContent:'')+' '+(ds?ds.textContent:'')).toLowerCase();
        a.style.display=(catHit||txt.indexOf(dirKw)>=0)?'':'none';
      });
    });
  }

  function buildNav(main,allowed){
    if(!allowed){removeById('hh-home-nav');return;}
    var nav=document.getElementById('hh-home-nav');
    if(nav&&nav.getAttribute('data-hh-home-v4')==='1')return;
    if(nav)nav.remove();
    nav=node('aside');nav.id='hh-home-nav';nav.setAttribute('aria-label','报表导航');nav.setAttribute('data-hh-home-v4','1');
    nav.appendChild(node('div','hh-home-nav-title','报表导航'));
    var work=node('a','hh-home-nav-item hh-home-nav-active','工作台');
    work.href='/superset/welcome/';work.setAttribute('aria-current','page');work.title='工作台';
    nav.appendChild(work);
    /* 📊 可视化驾驶舱（20261107h8）：置顶分区，工作台下方、报表分类上方 */
    nav.appendChild(node('div','hh-home-nav-section hh-home-nav-section-bi','可视化驾驶舱'));
    Array.prototype.forEach.call(BI_LINKS,function(b){
      var a=node('a','hh-home-nav-item hh-home-nav-bi');a.href=b[1];a.title=b[0];
      a.appendChild(node('span','hh-home-nav-label',b[0]));
      a.appendChild(node('span','hh-home-nav-count','BI'));
      a.setAttribute('data-hh-bi-link',b[1]);nav.appendChild(a);
    });
    nav.appendChild(node('div','hh-home-nav-section','报表分类'));
    Array.prototype.forEach.call(NAV,function(c){
      var a=node('a','hh-home-nav-item');a.href='/superset/dashboard/'+c[1]+'/';a.title=c[0];a.setAttribute('data-hh-cat-link',c[1]);
      a.appendChild(node('span','hh-home-nav-label',c[0]));
      var count=node('span','hh-home-nav-count','…');count.setAttribute('data-hh-cat-count',c[1]);count.setAttribute('aria-hidden','true');
      a.appendChild(count);nav.appendChild(a);
    });
    var all=node('a','hh-home-nav-all','查看全部报表 →');
    all.href='/superset/dashboard/34/';all.title='查看全部报表';
    nav.appendChild(all);
    main.insertBefore(nav,main.firstChild);
  }

  function parseReports(code){
    var lines=(code||'').split(/\r?\n/),items=[];
    for(var i=0;i<lines.length;i++){
      var m=lines[i].match(/^\s*-\s+\[([^\]]+)\]\((\/superset\/dashboard\/[^)]+)\)/);
      if(!m)continue;
      var desc='';
      for(var j=i+1;j<lines.length;j++){
        if(/^\s*-\s+\[/.test(lines[j]))break;
        var t=lines[j].trim();
        if(t&&t.charAt(0)!=='#'){desc=t;break;}
      }
      var href=m[2],id=Number((href.match(/\/dashboard\/(\d+)\//)||[])[1]||0);
      items.push({name:m[1],href:href,description:desc==GENERIC_DESC&&QUERY_SUMMARY[id]?'查询条件：'+QUERY_SUMMARY[id]:desc});
    }
    return items;
  }
  function updateCounts(id){
    var data=categoryCache[id],text=data&&data.reports?data.reports.length+' 项':(data&&data.error?'—':'…');
    Array.prototype.forEach.call(document.querySelectorAll('[data-hh-cat-count="'+id+'"]'),function(e){
      if(e.textContent!==text)e.textContent=text;
      var title=data&&data.error?'分类清单暂时无法读取':text;
      if(e.title!==title)e.title=title;
    });
    var group=document.querySelector('[data-hh-cat-group="'+id+'"]');
    if(group)renderGroup(group,id);
    if(pageId()===34&&dirKw)applyDirectoryFilter();
  }
  function loadCategory(id){
    if(categoryCache[id]){updateCounts(id);return Promise.resolve(categoryCache[id]);}
    if(categoryPending[id])return categoryPending[id];
    categoryPending[id]=fetch('/api/v1/dashboard/'+id,{credentials:'same-origin'}).then(function(r){
      if(!r.ok)return {error:r.status};
      return r.json().then(function(doc){
        var pos=doc.result&&doc.result.position_json;
        if(typeof pos==='string')pos=JSON.parse(pos);
        var code='';
        Object.keys(pos||{}).forEach(function(k){
          var meta=pos[k]&&pos[k].meta;
          if(!code&&meta&&typeof meta.code==='string'&&meta.code.indexOf('- [')>=0)code=meta.code;
        });
        return {reports:parseReports(code)};
      });
    }).catch(function(e){return {error:String(e&&e.message||e)};}).then(function(result){
      categoryCache[id]=result;updateCounts(id);return result;
    });
    return categoryPending[id];
  }
  function updateNavCounts(){
    if(!directoryAllowed())return;
    Array.prototype.forEach.call(NAV,function(c){loadCategory(c[1]);});
  }
  function openSet(){
    var raw=ssGet('hhDirOpenIds');
    if(raw===null)return [33];
    try{var ids=JSON.parse(raw);return Array.isArray(ids)?ids:[33];}catch(e){return [33];}
  }
  function setCategoryOpen(id,open){
    var set=openSet().filter(function(x){return x!==id;});
    if(open)set.push(id);
    ssSet('hhDirOpenIds',JSON.stringify(set));
  }
  function renderGroup(li,id){
    var box=li.querySelector('.hh-cat-children');if(!box)return;
    var data=categoryCache[id];if(!data)return;
    var signature=data.error?'error:'+data.error:(data.reports||[]).map(function(r){return r.name+'|'+r.href+'|'+r.description;}).join(';');
    if(box.getAttribute('data-hh-signature')===signature)return;
    box.setAttribute('data-hh-signature',signature);
    while(box.firstChild)box.removeChild(box.firstChild);
    if(data.error){box.appendChild(node('div','hh-cat-error','暂时无法加载，点击分类名进入分类页。'));return;}
    if(!data.reports.length){box.appendChild(node('div','hh-cat-error','该分类暂无可展开的报表。'));return;}
    Array.prototype.forEach.call(data.reports,function(report){
      var a=node('a','hh-cat-report');a.href=report.href;a.title=report.name+(report.description?'：'+report.description:'');
      a.appendChild(node('span','hh-cat-report-name',report.name));
      if(report.description)a.appendChild(node('span','hh-cat-report-desc',report.description));
      box.appendChild(a);
    });
  }
  function setupCategoryGroup(li,id){
    var root=li.querySelector('[data-hh-catalog-name]')||li.querySelector('a');
    var desc=li.querySelector('[data-hh-catalog-description]');
    var open=openSet().indexOf(id)>=0;
    li.setAttribute('data-hh-cat-group',id);li.setAttribute('data-hh-open',open?'1':'0');
    var head=node('div','hh-cat-head');
    var toggle=node('button','hh-cat-toggle',open?'▾':'▸');toggle.type='button';
    toggle.setAttribute('aria-expanded',open?'true':'false');toggle.setAttribute('aria-controls','hh-cat-children-'+id);
    toggle.setAttribute('aria-label',(open?'收起':'展开')+' '+li.querySelector('a').textContent.trim()+'报表');
    toggle.title=(open?'收起':'展开')+'报表';
    head.appendChild(toggle);
    if(root)head.appendChild(root);
    if(desc)head.appendChild(desc);
    var count=node('span','hh-cat-count','…');count.setAttribute('data-hh-cat-count',id);head.appendChild(count);
    var children=node('div','hh-cat-children');children.id='hh-cat-children-'+id;
    li.insertBefore(head,li.firstChild);li.appendChild(children);
    toggle.addEventListener('click',function(){
      var next=li.getAttribute('data-hh-open')!=='1';
      li.setAttribute('data-hh-open',next?'1':'0');
      toggle.setAttribute('aria-expanded',next?'true':'false');toggle.textContent=next?'▾':'▸';
      toggle.setAttribute('aria-label',(next?'收起':'展开')+' 分类报表');toggle.title=(next?'收起':'展开')+'报表';
      setCategoryOpen(id,next);if(next){loadCategory(id);renderGroup(li,id);}
    });
  }
  function directoryTree(){
    var md=document.querySelector('.dashboard-markdown');if(!md)return;
    var guide=Array.prototype.filter.call(md.querySelectorAll('p'),function(p){return p.textContent.trim().indexOf('请选择业务分类')===0;})[0];
    if(guide&&!guide.hasAttribute('data-hh-dir-guide')){guide.textContent+=' 也可点击分类左侧箭头直接展开报表。';guide.setAttribute('data-hh-dir-guide','');}
    var list=md.querySelector('ul');if(!list)return;
    Array.prototype.forEach.call(list.children,function(li){
      if(li.tagName!=='LI')return;
      if(li.getAttribute('data-hh-cat-group')==='kyb')return;
      var link=li.querySelector('a[href*="/superset/dashboard/"]');if(!link)return;
      var id=Number((link.getAttribute('href').match(/\/dashboard\/(\d+)\//)||[])[1]||0);
      if(!NAV.some(function(c){return c[1]===id;}))return;
      if(!li.hasAttribute('data-hh-cat-group'))setupCategoryGroup(li,id);
      loadCategory(id);
    });
    kybGroup();
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
    if(wrap&&wrap.parentElement===md&&wrap.nextSibling){md.insertBefore(box,wrap.nextSibling);}
    if(!box.parentElement){
      if(list)md.insertBefore(box,list);
      else md.appendChild(box);
    }
  }

  function updateNavCountsAndDirectory(){
    updateNavCounts();
    if(pageId()===34)directoryTree();
  }

  function header(main,allowed){
    var hint=document.getElementById('hospital-home-hint');if(!hint){hint=node('section');hint.id='hospital-home-hint';}
    var nav=document.getElementById('hh-home-nav');
    var prev=nav&&nav.parentElement===main?nav:null;
    if(hint.parentElement!==main||hint.previousElementSibling!==prev)main.insertBefore(hint,prev?prev.nextSibling:main.firstChild);
    if(hint.getAttribute('data-hh-access')!==String(allowed)||!hint.querySelector('h1')){
      while(hint.firstChild)hint.removeChild(hint.firstChild);
      hint.appendChild(node('h1','','统计报表工作台'));
      hint.appendChild(node('p','hh-home-desc','选择分类查找报表，或从最近使用继续。'));
      if(allowed){var btn=node('a','hh-home-primary','浏览全部报表');btn.href='/superset/dashboard/34/';btn.title='浏览全部报表';hint.appendChild(btn);}
      hint.setAttribute('data-hh-access',String(allowed));mark(hint,'data-hh-home-banner');
    }
  }

  function panelItems(collapse){
    var recent=null,map={};
    Array.prototype.forEach.call(collapse.children,function(item){
      if(!item.classList||!item.classList.contains('ant-collapse-item'))return;
      var textEl=item.querySelector('.ant-collapse-header-text'),t=textEl?textEl.textContent.trim():'';
      if(t==='最近使用'){recent=item;item.setAttribute('data-hh-home-panel','recent');return;}
      for(var i=0;i<MGMT.length;i++){
        if(t===MGMT[i][1]){
          item.setAttribute('data-hh-mgmt-panel',MGMT[i][0]);
          if(!item.id)item.id='hh-home-panel-'+MGMT[i][0];
          map[MGMT[i][0]]=item;
        }
      }
    });
    return {recent:recent,map:map};
  }

  function recentPanel(item){
    var head=item.querySelector('.ant-collapse-header');
    if(head&&!head.hasAttribute('data-hh-recent-bound')){
      head.setAttribute('data-hh-recent-bound','');
      head.addEventListener('click',function(){if(!programmatic)ssSet('hhHomeRecentManual','1');},true);
    }
    var active=!!item.querySelector('.ant-collapse-content-active');
    if(!active&&!recentAutoDone&&ssGet('hhHomeRecentManual')!=='1'&&head){
      recentAutoDone=true;programmatic=1;
      try{head.click();}catch(e){}
      programmatic=0;
    }
    var line=item.querySelector('.hh-home-empty-line');
    var empty=!!item.querySelector('.ant-collapse-content-active .ant-empty');
    var cards=item.querySelectorAll('.ant-collapse-content-active [data-test="styled-card"]').length;
    if(active&&cards===0&&empty){
      if(!line){
        line=node('div','hh-home-empty-line');
        line.textContent=document.getElementById('hh-home-nav')?'还没有最近使用的报表，请从左侧选择分类。':'当前账号暂无可用报表，请联系信息科。';
        var box=item.querySelector('.ant-collapse-content-box');
        if(box)box.appendChild(line);
      }
    }else if(line)line.remove();
  }

  function clearMounting(collapse){
    Array.prototype.forEach.call(collapse.querySelectorAll('[data-hh-mgmt-mounting]'),function(e){e.removeAttribute('data-hh-mgmt-mounting');});
  }
  function mountActive(map){
    var sec=document.getElementById('hh-home-management');
    var key=sec&&sec.getAttribute('data-hh-mgmt-active'),item=key&&map[key];
    if(!item)return;
    if(item.querySelector('.ant-collapse-content-active')){item.removeAttribute('data-hh-mgmt-mounting');return;}
    if(item.hasAttribute('data-hh-mgmt-mounting'))return;
    var head=item.querySelector('.ant-collapse-header');if(!head)return;
    item.setAttribute('data-hh-mgmt-mounting','');
    programmatic=1;try{head.click();}catch(e){}programmatic=0;
  }

  function management(collapse,map,admin){
    var sec=document.getElementById('hh-home-management');
    if(!admin||!map.dashboards){if(sec)sec.remove();return;}
    if(!sec){
      sec=node('section');sec.id='hh-home-management';sec.setAttribute('data-hh-home-v4','1');
      var bar=node('button','hh-home-mgmt-bar');bar.type='button';bar.id='hh-home-mgmt-toggle';
      bar.setAttribute('aria-controls','hh-home-mgmt-body');
      bar.appendChild(node('span','hh-home-mgmt-title','资源管理（管理员）'));
      bar.appendChild(node('span','hh-home-mgmt-hint','展开'));
      var body=node('div','hh-home-mgmt-body');body.id='hh-home-mgmt-body';
      body.setAttribute('role','tablist');body.setAttribute('aria-label','资源管理');
      Array.prototype.forEach.call(MGMT,function(m){
        var b=node('button','hh-home-mgmt-tab',m[1]);b.type='button';b.id='hh-home-tab-'+m[0];
        b.setAttribute('role','tab');b.setAttribute('aria-controls','hh-home-panel-'+m[0]);
        b.title=m[1];
        body.appendChild(b);
      });
      sec.appendChild(bar);sec.appendChild(body);
      collapse.insertBefore(sec,map.dashboards);
      bar.addEventListener('click',function(){
        var open=ssGet('hhHomeMgmtOpen')==='1';
        ssSet('hhHomeMgmtOpen',open?null:'1');
        if(!open)clearMounting(collapse);
        schedule();
      });
      body.addEventListener('click',function(e){
        var t=e.target,b=t&&t.closest?t.closest('.hh-home-mgmt-tab'):null;if(!b)return;
        var key=b.id.slice('hh-home-tab-'.length);
        if(ssGet('hhHomeMgmtTab')!==key){ssSet('hhHomeMgmtTab',key);clearMounting(collapse);}
        schedule();
      });
      body.addEventListener('keydown',function(e){
        if(e.key!=='ArrowRight'&&e.key!=='ArrowLeft')return;
        var tabs=body.querySelectorAll('.hh-home-mgmt-tab'),i=-1;
        for(var j=0;j<tabs.length;j++)if(tabs[j]===document.activeElement)i=j;
        if(i<0)return;
        var n=e.key==='ArrowRight'?(i+1)%tabs.length:(i-1+tabs.length)%tabs.length;
        tabs[n].focus();tabs[n].click();e.preventDefault();
      });
    }
    var open=ssGet('hhHomeMgmtOpen')==='1';
    var tab=ssGet('hhHomeMgmtTab');if(!tab||!map[tab])tab='dashboards';
    sec.setAttribute('data-hh-mgmt-active',tab);
    sec.setAttribute('data-hh-mgmt-open',open?'1':'0');
    var toggle=document.getElementById('hh-home-mgmt-toggle');
    toggle.setAttribute('aria-expanded',open?'true':'false');
    var hintEl=toggle.querySelector('.hh-home-mgmt-hint');
    if(hintEl&&hintEl.textContent!==(open?'收起':'展开'))hintEl.textContent=open?'收起':'展开';
    Array.prototype.forEach.call(sec.querySelectorAll('.hh-home-mgmt-tab'),function(b){
      var k=b.id.slice('hh-home-tab-'.length);
      b.setAttribute('aria-selected',k===tab?'true':'false');
    });
    if(open)mountActive(map);
  }

  function flatten(e,stop){while(e&&e!==stop){mark(e,'data-hh-flatten');e=e.parentElement;}}
  function row(card){
    var body=card.querySelector('.ant-card-body'),titleRow=card.querySelector('.titleRow'),actions=card.querySelector('[data-test="card-actions"]');
    if(!body||!titleRow||!actions)return false;
    var title=titleRow.firstElementChild;
    if(!title||title===actions||title.contains(actions))return false;
    mark(card,'data-hh-list-row');mark(body,'data-hh-row-body');mark(title,'data-hh-row-title');mark(actions,'data-hh-row-actions');
    flatten(title.parentElement,body);flatten(actions.parentElement,body);tooltip(title);
    if(title.tagName!=='A'&&!title.hasAttribute('tabindex')){
      title.tabIndex=0;title.setAttribute('role','link');
      title.addEventListener('keydown',function(e){if(e.key==='Enter'&&!e.ctrlKey&&!e.metaKey&&!e.altKey){e.preventDefault();e.stopPropagation();title.click();}});
    }
    Array.prototype.forEach.call(card.querySelectorAll('.ant-tag'),function(tag){mark(tag,'data-hh-row-state');flatten(tag.parentElement,body);});
    var info=card.querySelector('.ant-card-meta-description');if(info){mark(info,'data-hh-row-info');tooltip(info);}
    return true;
  }
  function columns(grid){
    var hasState=!!grid.querySelector('[data-hh-row-state]');
    if(grid.getAttribute('data-hh-has-state')!==String(hasState))grid.setAttribute('data-hh-has-state',String(hasState));
    var head=grid.querySelector('.hh-list-columns');
    if(!head){head=node('div','hh-list-columns');head.setAttribute('aria-hidden','true');head.appendChild(node('span','','名称'));head.appendChild(node('span','','信息'));head.appendChild(node('span','hh-state-column','状态'));head.appendChild(node('span','','操作'));grid.insertBefore(head,grid.firstChild);}
  }
  function relativeZh(text){
    var t=(text||'').trim();
    var rules=[[/^just now$/i,'刚刚'],[/^(?:a|an|1) minute ago$/i,'1分钟前'],[/^(\d+) minutes ago$/i,'$1分钟前'],[/^(?:an|1) hour ago$/i,'1小时前'],[/^(\d+) hours ago$/i,'$1小时前'],[/^(?:a|1) day ago$/i,'1天前'],[/^(\d+) days ago$/i,'$1天前'],[/^(?:a|1) week ago$/i,'1周前'],[/^(\d+) weeks ago$/i,'$1周前'],[/^(?:a|1) month ago$/i,'1个月前'],[/^(\d+) months ago$/i,'$1个月前'],[/^(?:a|1) year ago$/i,'1年前'],[/^(\d+) years ago$/i,'$1年前']];
    for(var i=0;i<rules.length;i++)if(rules[i][0].test(t))return t.replace(rules[i][0],rules[i][1]);
    return t;
  }
  function localizeRecent(collapse){
    Array.prototype.forEach.call(collapse.querySelectorAll('[data-hh-home-panel="recent"] .ant-card-meta-description'),function(info){
      var text=info.textContent.trim(),next=text;
      if(/ ago$/i.test(text)||/^just now$/i.test(text)){
        var match=text.match(/^(已查看|已编辑|已创建)\s+(.+)$/);
        next=match?match[1]+' '+relativeZh(match[2]):relativeZh(text);
        if(next!==text){info.textContent=next;tooltip(info);}
      }
    });
  }
  function home(){
    var collapse=document.querySelector('main .ant-collapse'),main=collapse&&collapse.closest('main');if(!main)return;
    mark(main,'data-hh-home-content');
    Array.prototype.forEach.call(main.children,function(e){if(e.textContent.trim()==='首页'&&!e.querySelector('a,button,input'))mark(e,'data-hh-home-old-title');});
    var allowed=directoryAllowed();
    document.documentElement.classList.toggle('hh-home-nonav',!allowed);
    buildNav(main,allowed);
    updateKybNav();
    header(main,allowed);
    ensureHomeSearch();
    var p=panelItems(collapse);
    if(p.recent)recentPanel(p.recent);
    management(collapse,p.map,isAdmin());
    Array.prototype.forEach.call(collapse.querySelectorAll('[data-test="styled-card"]'),function(card){
      var item=card.parentElement,grid=item&&item.parentElement,box=grid&&grid.closest('.ant-collapse-content-box');
      if(!box||item.querySelectorAll('[data-test="styled-card"]').length!==1||!row(card))return;
      var recentGrid=card.closest('[data-hh-home-panel="recent"] .recentCards');
      if(recentGrid){
        mark(item,'data-hh-home-card');
        Array.prototype.forEach.call(recentGrid.querySelectorAll('[data-hh-home-grid]'),function(e){if(e!==recentGrid)e.removeAttribute('data-hh-home-grid');});
        Array.prototype.forEach.call(recentGrid.querySelectorAll('.hh-list-columns'),function(e){if(e.parentElement!==recentGrid)e.remove();});
        mark(recentGrid,'data-hh-home-grid');
        var recentInner=recentGrid;
        while(recentInner.parentElement&&recentInner.parentElement!==box)recentInner=recentInner.parentElement;
        var recentBar=recentInner.previousElementSibling;
        if(recentBar&&!recentBar.hasAttribute('data-hh-home-toolbar')&&!recentBar.querySelector('[data-test="styled-card"]'))mark(recentBar,'data-hh-home-toolbar');
        columns(recentGrid);
        return;
      }
      mark(item,'data-hh-home-card');mark(grid,'data-hh-home-grid');
      var container=grid;
      while(container.parentElement&&container.parentElement!==box)container=container.parentElement;
      var inner=grid;
      while(inner.parentElement&&inner.parentElement!==box&&inner.parentElement!==container)inner=inner.parentElement;
      var bar=inner.previousElementSibling;
      if(bar&&!bar.hasAttribute('data-hh-home-toolbar')&&!bar.querySelector('[data-test="styled-card"]'))mark(bar,'data-hh-home-toolbar');
      columns(grid);
    });
    localizeRecent(collapse);
    api.homeReady=true;
  }
  function catalog(){
    Array.prototype.forEach.call(document.querySelectorAll('.dashboard-markdown li'),function(li){
      var links=li.querySelectorAll('a');if(links.length!==1)return;
      var link=links[0];tooltip(link);tooltip(li);
      var root=link;while(root.parentElement&&root.parentElement!==li)root=root.parentElement;
      if(root.parentElement!==li||root.textContent.trim()!==link.textContent.trim())return;
      mark(root,'data-hh-catalog-name');
      Array.prototype.forEach.call(li.children,function(e){if(e!==root&&!e.querySelector('a')){mark(e,'data-hh-catalog-description');tooltip(e);}});
    });
  }
  function restoreCatalog(){
    Array.prototype.forEach.call(document.querySelectorAll('[data-hh-catalog-description]'),function(e){e.removeAttribute('data-hh-catalog-description');});
  }
  function refresh(){
    pending=0;var h=isHome(),c=isCatalog(),q=isQuery();
    document.documentElement.classList.toggle('hh-home',h);document.documentElement.classList.toggle('hh-catalog-compact',c);document.documentElement.classList.toggle('hh-query-ui',q);
    document.documentElement.classList.toggle('hh-native-editor',editing());
    if(h){home();}
    else{
      recentAutoDone=false;
      document.documentElement.classList.remove('hh-home-nonav');
      removeById('hh-home-nav');removeById('hospital-home-hint');removeById('hh-home-management');
    }
    if(c)catalog();else restoreCatalog();
    if(h||pageId()===34){checkKybAccess();updateNavCountsAndDirectory();}
  }
  function schedule(){if(!pending)pending=setTimeout(refresh,80);}
  function watchDirectory(){
    if(pollTimer)clearInterval(pollTimer);
    var seen=window.hospitalReportUI?window.hospitalReportUI.directoryAccess:undefined,n=0;
    pollTimer=setInterval(function(){
      n++;
      var now=window.hospitalReportUI?window.hospitalReportUI.directoryAccess:undefined;
      if(now!==seen){seen=now;schedule();}
      if(n>=38){clearInterval(pollTimer);pollTimer=0;}
    },400);
  }
  function start(){
    var style=node('style');style.id='hospital-home-layout-style';
    style.textContent=[
      'html.hh-home,html.hh-catalog-compact,html.hh-query-ui{--hui-page:#f7f8fa;--hui-content:#fff;--hui-text:#303133;--hui-muted:#909399;--hui-blue:#1677c8;--hui-line:#ebeef0;--hui-border:#e4e7ed;--hui-row:42px;--hui-gap:12px;--hui-radius:6px}',
      'html.hh-home{--hh-page:#f5f7fa;--hh-panel:#fff;--hh-border:#e4e9ef;--hh-text:#263445;--hh-muted:#718096;--hh-blue:#1677c8;--hh-blue-dark:#135da3;--hh-radius:8px;--hh-line:#eef2f6}',
      'html.hh-home body{color:var(--hh-text);font-family:"Microsoft YaHei",system-ui,-apple-system,"Segoe UI",sans-serif;font-size:14px;background:var(--hh-page)!important}',
      'html.hh-catalog-compact body,html.hh-query-ui body{color:var(--hui-text);font-family:"Microsoft YaHei",system-ui,-apple-system,"Segoe UI",sans-serif;font-size:14px}',
      'html.hh-home main[data-hh-home-content]{display:grid!important;grid-template-columns:224px minmax(0,1fr);grid-template-rows:auto auto;gap:0 20px;align-items:start;align-content:start;width:100%;max-width:1440px;margin:0 auto;box-sizing:border-box;padding:16px 20px 24px!important;background:var(--hh-page)}',
      'html.hh-home.hh-home-nonav main[data-hh-home-content]{grid-template-columns:minmax(0,1fr)}',
      'html.hh-home.hh-home-nonav #hospital-home-hint,html.hh-home.hh-home-nonav main .ant-collapse{grid-column:1}',
      'html.hh-home [data-hh-home-old-title]{display:none!important}',
      'html.hh-home #hh-home-nav{grid-column:1;grid-row:1/3;display:flex;flex-direction:column;align-self:start;position:sticky;top:16px;background:var(--hh-panel);border:1px solid var(--hh-border);border-radius:var(--hh-radius);padding:8px 0 6px;margin:0;box-sizing:border-box;min-width:0}',
      'html.hh-home #hh-home-nav .hh-home-nav-title{padding:4px 16px 10px;margin:0 0 6px;border-bottom:1px solid var(--hh-line);font-size:15px;line-height:22px;font-weight:600;color:var(--hh-text)}',
      'html.hh-home #hh-home-nav .hh-home-nav-section{padding:8px 16px 4px;font-size:12px;line-height:18px;color:var(--hh-muted)}',
      'html.hh-home #hh-home-nav .hh-home-nav-item{display:flex;align-items:center;justify-content:space-between;gap:8px;height:42px;padding:0 14px;margin:2px 8px;border-radius:4px;font-size:14px;line-height:22px;color:var(--hh-text);text-decoration:none;white-space:nowrap;overflow:hidden}',
      'html.hh-home #hh-home-nav .hh-home-nav-count{flex:none;margin-left:auto;min-width:26px;padding:0 6px;border-radius:10px;background:#f3f6f9;color:#7b8a9a;font-size:12px;line-height:20px;text-align:center}',
      'html.hh-home #hh-home-nav .hh-home-nav-label{min-width:0;overflow:hidden;text-overflow:ellipsis}',
      'html.hh-home #hh-home-nav .hh-home-nav-badge{flex:none;width:20px;height:20px;line-height:20px;text-align:center;background:#eaf3fb;color:var(--hh-blue);border-radius:4px;font-size:12px}',
      'html.hh-home #hh-home-nav a:hover{background:#f3f8fc;color:var(--hh-text)}',
      'html.hh-home #hh-home-nav .hh-home-nav-active{background:#eaf3fb;color:var(--hh-blue);font-weight:600}',
      'html.hh-home #hh-home-nav .hh-home-nav-all{display:flex;align-items:center;height:42px;margin:8px 8px 2px;padding:0 14px;border-top:1px solid var(--hh-line);color:var(--hh-blue);font-size:13px;text-decoration:none;white-space:nowrap}',
      'html.hh-home #hh-home-nav .hh-home-nav-all:hover{color:var(--hh-blue-dark)}',
      'html.hh-home #hospital-home-hint{grid-column:2;grid-row:1;display:flex!important;align-items:center;gap:16px;min-height:48px;margin:2px 0 14px!important;padding:0!important;border:0!important;border-radius:0!important;background:transparent!important;box-shadow:none!important;color:var(--hh-text)}',
      '#hospital-home-hint h1{margin:0!important;font-size:20px;line-height:28px;font-weight:600;color:var(--hh-text);white-space:nowrap}',
      '#hospital-home-hint .hh-home-desc{margin:0!important;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--hh-muted);font-size:13px;line-height:20px}',
      '#hospital-home-hint .hh-home-primary{margin-left:auto;flex:none;display:inline-flex;align-items:center;height:32px;padding:0 14px;border-radius:4px;background:var(--hh-blue);color:#fff!important;font-size:13px;line-height:32px;text-decoration:none!important;white-space:nowrap}',
      '#hospital-home-hint .hh-home-primary:hover{background:var(--hh-blue-dark);color:#fff!important}',
      'html.hh-home main .ant-collapse{grid-column:2;grid-row:2;display:block;margin:0!important;padding:0!important;border:0!important;background:transparent}',
      'html.hh-home .ant-collapse-item{background:var(--hh-panel);border:1px solid var(--hh-border);border-radius:var(--hh-radius);margin:0 0 12px!important;overflow:hidden;box-shadow:none!important}',
      'html.hh-home .ant-collapse-item>.ant-collapse-header{display:flex!important;align-items:center!important;min-height:44px;margin:0!important;padding:0 16px!important;font-size:15px!important;line-height:22px!important;font-weight:600!important;color:var(--hh-text)!important;background:transparent!important}',
      'html.hh-home .ant-collapse-header .ant-collapse-arrow{color:var(--hh-muted)}',
      'html.hh-home .ant-collapse-content{border:0!important;background:transparent!important}',
      'html.hh-home .ant-collapse-content-box{padding:0 0 8px!important;margin:0!important}',
      'html.hh-home [data-hh-home-toolbar]{position:static!important;transform:none!important;top:auto!important;bottom:auto!important;right:auto!important;min-width:0;min-height:40px;padding:6px 16px 8px!important;margin:0!important}',
      'html.hh-home [data-hh-home-toolbar] .menu{display:flex!important;align-items:center!important;justify-content:space-between;gap:8px;margin:0!important;width:100%!important;flex-wrap:wrap}',
      'html.hh-home [data-hh-home-toolbar] .nav-left{display:flex;align-items:center;gap:2px;min-width:0;flex-wrap:wrap}',
      'html.hh-home [data-hh-home-toolbar] .nav-right{position:static!important;top:auto!important;right:auto!important;display:flex;align-items:center;gap:8px;margin-left:auto;align-self:center}',
      'html.hh-home [data-hh-home-toolbar] .no-router{padding:3px 8px;border-radius:4px;font-size:13px;color:var(--hh-muted);text-decoration:none;cursor:pointer}',
      'html.hh-home [data-hh-home-toolbar] .no-router:hover{color:var(--hh-blue)}',
      'html.hh-home [data-hh-home-toolbar] .no-router.active{background:#eaf3fb!important;color:var(--hh-blue)!important;border-radius:4px!important}',
      'html.hh-home [data-hh-home-toolbar] .ant-btn{height:28px!important;padding:0 10px!important;border-radius:4px!important;box-shadow:none!important;font-size:13px!important;background:#fff!important;color:var(--hh-blue)!important;border-color:var(--hh-border)!important}',
      'html.hh-home [data-hh-home-toolbar] .nav-right a{color:var(--hh-blue);font-size:13px;text-decoration:none;white-space:nowrap}',
      'html.hh-home [data-hh-home-toolbar] .nav-right a:hover{text-decoration:underline}',
      'html.hh-home [data-hh-home-grid]{--hui-columns:minmax(0,1fr) 160px 88px 76px;display:block!important;width:100%!important;height:auto!important;min-height:0!important;max-height:none!important;overflow:visible!important;margin:0!important;padding:0!important}',
      'html.hh-home [data-hh-home-grid][data-hh-has-state=false]{--hui-columns:minmax(0,1fr) 160px 76px}',
      'html.hh-home .hh-list-columns{display:grid;grid-template-columns:var(--hui-columns);align-items:center;min-height:34px;padding:0 16px;background:var(--hh-page);border-top:1px solid var(--hh-line);border-bottom:1px solid var(--hh-line);font-size:13px;color:#606266}',
      'html.hh-home .hh-list-columns>span:not(:first-child){text-align:center}html.hh-home [data-hh-has-state=false] .hh-state-column{display:none}',
      'html.hh-home .recentCards[data-hh-home-grid]{display:block!important;max-height:min(46vh,448px)!important;overflow-y:auto!important;overflow-x:hidden!important;scrollbar-width:thin;scrollbar-color:#c8d3df transparent}',
      'html.hh-home .recentCards .hh-list-columns{position:sticky;top:0;z-index:2}',
      'html.hh-home [data-hh-home-card]{display:block!important;width:100%!important;max-width:none!important;min-width:0!important;height:auto!important;margin:0!important;padding:0!important}',
      'html.hh-home [data-hh-list-row]{width:100%!important;min-height:0!important;height:auto!important;max-width:none!important;margin:0!important;border:0!important;border-bottom:1px solid var(--hh-line)!important;border-radius:0!important;box-shadow:none!important;background:var(--hh-panel)!important}',
      'html.hh-home [data-hh-list-row]:hover{background:#f3f8fc!important}',
      'html.hh-home [data-hh-row-body]{display:grid!important;grid-template-columns:var(--hui-columns);grid-template-rows:minmax(43px,auto);align-items:center;column-gap:0;width:100%;margin:0!important;padding:0 16px!important;min-height:0!important}',
      'html.hh-home [data-hh-flatten]{display:contents!important;margin:0!important;padding:0!important;width:auto!important;height:auto!important;min-height:0!important;max-height:none!important}',
      'html.hh-home [data-hh-row-title]{grid-column:1;grid-row:1;display:block!important;min-width:0!important;width:100%!important;max-width:none!important;margin:0!important;padding:0 16px 0 0!important;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;line-height:22px!important;font-size:14px!important;color:var(--hh-text);cursor:pointer}',
      'html.hh-home [data-hh-row-title]:hover{color:var(--hh-blue)}',
      'html.hh-home [data-hh-row-info]{grid-column:2;grid-row:1;text-align:center;margin:0!important;min-width:0;width:100%!important;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;line-height:22px!important;font-size:13px;color:var(--hh-muted)!important}',
      'html.hh-home [data-hh-row-state]{grid-column:3;grid-row:1;justify-self:center;margin:0!important;padding:0 5px!important;border:1px solid var(--hh-border)!important;border-radius:3px!important;line-height:19px!important;font-size:12px!important;background:#f5f7fa!important;color:#606266!important}',
      'html.hh-home [data-hh-row-state] .anticon{color:inherit!important}',
      'html.hh-home [data-hh-row-actions]{grid-column:-2/-1;grid-row:1;display:flex!important;justify-content:center;align-items:center;position:static!important;width:100%!important;min-width:0;margin:0!important;padding:0!important}',
      'html.hh-home [data-hh-row-actions] .ant-btn{height:28px!important;padding:0 4px!important;border-radius:3px!important}',
      'html.hh-home [data-hh-list-row] .ant-card-cover{display:none!important}',
      'html.hh-home [data-hh-list-row] .ant-card-meta-avatar{display:none!important}',
      'html.hh-home .ant-empty{margin:12px 0!important}html.hh-home .ant-empty-image{display:none!important}html.hh-home .ant-empty-description{font-size:13px;color:var(--hh-muted)}',
      'html.hh-home [data-hh-home-panel="recent"] .ant-empty{display:none!important}',
      'html.hh-home .hh-home-empty-line{padding:10px 16px 6px;font-size:13px;line-height:22px;color:var(--hh-muted)}',
      'html.hh-home #hh-home-management{margin:0 0 12px;min-width:0}',
      'html.hh-home .hh-home-mgmt-bar{display:flex!important;align-items:center;width:100%;height:42px;box-sizing:border-box;padding:0 16px;background:var(--hh-panel);border:1px solid var(--hh-border);border-radius:var(--hh-radius);cursor:pointer;font:inherit;text-align:left}',
      'html.hh-home .hh-home-mgmt-bar:hover{border-color:#cfd9e2}',
      'html.hh-home .hh-home-mgmt-title{font-size:14px;font-weight:600;color:var(--hh-text);white-space:nowrap}',
      'html.hh-home .hh-home-mgmt-hint{margin-left:auto;padding-left:12px;font-size:13px;color:var(--hh-blue);white-space:nowrap}',
      'html.hh-home #hh-home-management[data-hh-mgmt-open="1"] .hh-home-mgmt-bar{border-radius:var(--hh-radius) var(--hh-radius) 0 0;border-bottom:0}',
      'html.hh-home .hh-home-mgmt-body{display:none}',
      'html.hh-home #hh-home-management[data-hh-mgmt-open="1"] .hh-home-mgmt-body{display:flex;align-items:center;gap:4px;height:40px;box-sizing:border-box;padding:0 12px;background:var(--hh-panel);border:1px solid var(--hh-border);border-top:0;border-bottom:0;overflow-x:auto}',
      'html.hh-home .hh-home-mgmt-tab{flex:none;height:38px;padding:0 12px;border:0;background:transparent;font:inherit;font-size:13px;color:var(--hh-muted);cursor:pointer;border-bottom:2px solid transparent}',
      'html.hh-home .hh-home-mgmt-tab:hover{color:var(--hh-text)}',
      'html.hh-home .hh-home-mgmt-tab[aria-selected="true"]{color:var(--hh-blue);font-weight:600;border-bottom-color:var(--hh-blue)}',
      'html.hh-home [data-hh-mgmt-panel]{display:none!important;margin:0!important}',
      'html.hh-home [data-hh-mgmt-panel]>.ant-collapse-header{display:none!important}',
      'html.hh-home #hh-home-management[data-hh-mgmt-open="1"][data-hh-mgmt-active="dashboards"]~[data-hh-mgmt-panel="dashboards"]{display:block!important;border-top:0;border-radius:0 0 var(--hh-radius) var(--hh-radius);margin:0 0 12px!important}',
      'html.hh-home #hh-home-management[data-hh-mgmt-open="1"][data-hh-mgmt-active="charts"]~[data-hh-mgmt-panel="charts"]{display:block!important;border-top:0;border-radius:0 0 var(--hh-radius) var(--hh-radius);margin:0 0 12px!important}',
      'html.hh-home #hh-home-management[data-hh-mgmt-open="1"][data-hh-mgmt-active="queries"]~[data-hh-mgmt-panel="queries"]{display:block!important;border-top:0;border-radius:0 0 var(--hh-radius) var(--hh-radius);margin:0 0 12px!important}',
      'html.hh-home #hh-home-nav a:focus,html.hh-home #hospital-home-hint .hh-home-primary:focus,html.hh-home .hh-home-mgmt-bar:focus,html.hh-home .hh-home-mgmt-tab:focus,html.hh-home [data-hh-row-title]:focus{outline:2px solid var(--hh-blue);outline-offset:2px}',
      'html.hh-catalog-compact [data-test="dashboard-content-wrapper"]{background:var(--hui-page)}',
      'html.hh-catalog-compact .dashboard-markdown{height:auto!important;min-height:0!important}',
      'html.hh-catalog-compact .dashboard-markdown .dashboard-component{height:auto!important;min-height:0!important;padding:18px!important;border:0!important;border-radius:var(--hui-radius)!important;box-shadow:none!important;background:var(--hui-content)!important}',
      'html.hh-catalog-compact .dashboard-markdown h2{font-size:16px!important;line-height:24px!important;margin:0 0 6px!important;color:var(--hui-text)!important}',
      'html.hh-catalog-compact .dashboard-markdown p{margin:0 0 10px!important;font-size:13px!important;line-height:22px!important;color:var(--hui-muted)!important}',
      'html.hh-catalog-compact .dashboard-markdown ul{display:block!important;padding:0!important;margin:10px 0 12px!important;border-top:1px solid var(--hui-line)}',
      'html.hh-catalog-compact .dashboard-markdown li{display:flex!important;align-items:center;gap:16px;position:relative;min-height:44px!important;margin:0!important;padding:10px 12px!important;border:0!important;border-bottom:1px solid var(--hui-line)!important;border-radius:0!important;background:var(--hui-content)!important;font-size:14px;line-height:24px;box-sizing:border-box}',
      'html.hh-catalog-compact .dashboard-markdown li:hover{background:#f3f8fc!important}',
      'html.hh-catalog-compact .dashboard-markdown li:after{content:none!important}',
      'html.hh-catalog-compact .dashboard-markdown [data-hh-catalog-name]{flex:0 0 260px;min-width:0;margin:0!important}',
      'html.hh-catalog-compact .dashboard-markdown li a{font-size:14px!important;font-weight:400!important;line-height:24px!important;margin:0!important;color:var(--hui-blue)!important;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}',
      'html.hh-catalog-compact .dashboard-markdown li a:after{border-radius:0!important}',
      'html.hh-catalog-compact .dashboard-markdown [data-hh-catalog-description]{min-width:0;flex:1;display:block;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;line-height:24px!important;margin:0!important;font-size:13px;color:var(--hui-muted)}',
      /* 34 可展开两级目录：分类头 + 原生报表链接子层 */
      'html.hh-directory .dashboard-markdown li[data-hh-cat-group] a:after,html.hh-catalog-compact .dashboard-markdown li[data-hh-cat-group] a:after{content:none!important;pointer-events:none!important}',
      'html.hh-catalog-compact .dashboard-markdown li[data-hh-cat-group]{display:block!important;min-height:0!important;padding:0!important}',
      'html.hh-catalog-compact .dashboard-markdown .hh-cat-head{display:flex;align-items:center;gap:12px;min-height:48px;padding:8px 12px;box-sizing:border-box}',
      'html.hh-catalog-compact .dashboard-markdown .hh-cat-toggle{flex:none;width:30px;height:30px;padding:0;border:0;border-radius:4px;background:transparent;color:#718096;font-size:16px;line-height:28px;cursor:pointer}',
      'html.hh-catalog-compact .dashboard-markdown .hh-cat-toggle:hover{background:#eaf3fb;color:#1677c8}',
      'html.hh-catalog-compact .dashboard-markdown .hh-cat-toggle:focus-visible{outline:2px solid #1677c8;outline-offset:2px}',
      'html.hh-catalog-compact .dashboard-markdown .hh-cat-head [data-hh-catalog-name]{flex:0 0 200px;min-width:0;margin:0!important}',
      'html.hh-catalog-compact .dashboard-markdown .hh-cat-head [data-hh-catalog-name] a{font-weight:600!important}',
      'html.hh-catalog-compact .dashboard-markdown .hh-cat-count{flex:none;margin-left:auto;font-size:12px;line-height:20px;color:#718096;white-space:nowrap}',
      'html.hh-catalog-compact .dashboard-markdown .hh-cat-children{display:none;margin:0 12px 10px 46px;padding-left:10px;border-left:2px solid #e4e9ef}',
      'html.hh-catalog-compact .dashboard-markdown li[data-hh-open="1"]>.hh-cat-children{display:block}',
      'html.hh-catalog-compact .dashboard-markdown .hh-cat-report{display:grid;grid-template-columns:minmax(220px,300px) minmax(0,1fr);align-items:center;column-gap:16px;min-height:40px;padding:4px 8px;border-radius:4px;font-size:13px;line-height:22px;text-decoration:none}',
      'html.hh-catalog-compact .dashboard-markdown .hh-cat-report:hover{background:#f3f8fc}',
      'html.hh-catalog-compact .dashboard-markdown .hh-cat-report-name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#1677c8}',
      'html.hh-catalog-compact .dashboard-markdown .hh-cat-report-desc{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#718096}',
      'html.hh-catalog-compact .dashboard-markdown .hh-cat-error{padding:8px 10px 12px;font-size:13px;color:#909399}',
      /* 快速搜索（20261104h7）：首页工作台与 34 目录共用输入框样式 */
      '#hh-report-search{box-sizing:border-box;width:260px;height:32px;padding:0 28px 0 10px;border:1px solid #d9e1ea;border-radius:4px;background:#fff;color:#263445;font:inherit;font-size:13px;line-height:30px;outline:none}',
      '#hh-report-search:focus{border-color:#1677c8;box-shadow:0 0 0 2px rgba(22,119,200,.12)}',
      '#hh-report-search::-webkit-search-cancel-button{cursor:pointer}',
      '.hh-search-box{position:relative;flex:none;margin-left:auto}',
      '#hospital-home-hint .hh-search-box+.hh-home-primary{margin-left:12px}',
      '.hh-search-dropdown{position:absolute;top:36px;right:0;width:min(430px,70vw);max-height:320px;overflow-y:auto;background:#fff;border:1px solid #d9e1ea;border-radius:6px;box-shadow:0 6px 20px rgba(16,42,67,.14);z-index:1200}',
      '.hh-search-row{display:flex;align-items:center;gap:12px;height:38px;padding:0 12px;font-size:13px;color:#263445;text-decoration:none;white-space:nowrap}',
      '.hh-search-row:hover{background:#f3f8fc}',
      '.hh-search-row:focus-visible{outline:2px solid #1677c8;outline-offset:-2px}',
      '.hh-search-name{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis}',
      '.hh-search-meta{flex:none;max-width:48%;overflow:hidden;text-overflow:ellipsis;color:#8a97a5;font-size:12px}',
      '.hh-search-empty{display:flex;align-items:center;height:38px;padding:0 12px;font-size:13px;color:#8a97a5}',
      '.hh-dir-search-wrap{margin:0 0 10px}',
      '.hh-dir-search-wrap #hh-report-search{display:block}',
      'html.hh-query-ui .dashboard-markdown .dashboard-component{background:#fafbfc!important;border-left-color:var(--hui-border)!important;color:#606266!important;box-shadow:none!important}',
      'html.hh-query-ui .superset-chart-table table,html.hh-query-ui #hospital-monthly-report table{font-size:14px!important}',
      'html.hh-query-ui .superset-chart-table th,html.hh-query-ui #hospital-monthly-report th{background:var(--hui-page)!important;color:var(--hui-text)!important;border-color:var(--hui-line)!important}',
      'html.hh-query-ui .superset-chart-table td,html.hh-query-ui #hospital-monthly-report td{height:var(--hui-row)!important;box-sizing:border-box;border-color:var(--hui-line)!important}',
      'html.hh-query-ui #hospital-monthly-report{border-color:var(--hui-border);border-radius:var(--hui-radius);box-shadow:none;color:var(--hui-text)}',
      'html.hh-query-ui #hospital-monthly-report h2{font-size:16px;color:var(--hui-text)}',
      'html.hh-query-ui #hospital-monthly-report th.hm-group{font-size:15px;background:#f0f2f5!important}',
      'html.hh-query-ui .superset-chart-table tbody tr:hover td,html.hh-query-ui #hospital-monthly-report tr:hover td{background:#f3f8fc!important}',
      '@media(min-width:901px) and (max-width:1199px){html.hh-home main[data-hh-home-content]{grid-template-columns:200px minmax(0,1fr)}html.hh-home #hospital-home-hint{flex-wrap:wrap;gap:8px 12px}#hospital-home-hint .hh-home-desc{white-space:normal;overflow:visible;text-overflow:clip}}',
      '@media(max-width:900px){html.hh-home main[data-hh-home-content]{grid-template-columns:minmax(0,1fr);padding:14px 12px 20px!important}html.hh-home #hh-home-nav{grid-column:1/-1;grid-row:1;position:static;flex-direction:row;align-items:center;gap:0;padding:0 4px;margin:0 0 12px;overflow-x:auto;overflow-y:hidden}html.hh-home #hh-home-nav .hh-home-nav-title,html.hh-home #hh-home-nav .hh-home-nav-section,html.hh-home #hh-home-nav .hh-home-nav-count{display:none}html.hh-home #hh-home-nav .hh-home-nav-item{flex:none;height:36px;margin:4px 2px;padding:0 10px}html.hh-home #hh-home-nav .hh-home-nav-badge{display:none}html.hh-home #hh-home-nav .hh-home-nav-all{flex:none;height:36px;margin:4px 2px;padding:0 10px;border-top:0}html.hh-home #hospital-home-hint{grid-column:1/-1;grid-row:2;flex-wrap:wrap;gap:8px 12px}#hospital-home-hint h1{white-space:normal}#hospital-home-hint .hh-home-desc{white-space:normal;overflow:visible;text-overflow:clip;flex-basis:100%}html.hh-home main .ant-collapse{grid-column:1/-1;grid-row:3}html.hh-home [data-hh-home-grid]{--hui-columns:minmax(0,1fr) 120px 78px 68px}html.hh-home [data-hh-home-grid][data-hh-has-state=false]{--hui-columns:minmax(0,1fr) 120px 68px}html.hh-catalog-compact [data-hh-catalog-name]{flex-basis:200px}html.hh-catalog-compact .dashboard-markdown .hh-cat-head [data-hh-catalog-description]{display:none}html.hh-catalog-compact .dashboard-markdown .hh-cat-report{grid-template-columns:minmax(180px,240px) minmax(0,1fr)}}',
      '@media(max-width:600px){#hospital-home-hint .hh-home-desc{display:none}#hospital-home-hint .hh-home-primary{padding:0 10px}html.hh-home [data-hh-home-grid]{--hui-columns:minmax(0,1fr) 72px 64px}html.hh-home [data-hh-home-grid][data-hh-has-state=false]{--hui-columns:minmax(0,1fr) 64px}html.hh-home [data-hh-row-info],html.hh-home .hh-list-columns>span:nth-child(2){display:none}html.hh-home [data-hh-row-state]{grid-column:2}html.hh-home [data-hh-home-toolbar] .nav-right{flex-wrap:wrap}html.hh-catalog-compact [data-hh-catalog-name]{flex-basis:150px}html.hh-catalog-compact .dashboard-markdown .hh-cat-head{gap:8px;padding-left:8px;padding-right:8px}html.hh-catalog-compact .dashboard-markdown .hh-cat-head [data-hh-catalog-name]{flex:1;min-width:0}html.hh-catalog-compact .dashboard-markdown .hh-cat-children{margin-left:38px;padding-left:6px}html.hh-catalog-compact .dashboard-markdown .hh-cat-report{grid-template-columns:minmax(0,1fr);min-height:40px}html.hh-catalog-compact .dashboard-markdown .hh-cat-report-desc{display:none}}'
    ].join('\n');document.head.appendChild(style);
    var push=history.pushState;history.pushState=function(){var r=push.apply(history,arguments);schedule();return r;};
    window.addEventListener('popstate',schedule);window.addEventListener('resize',schedule);window.addEventListener('hashchange',schedule);new MutationObserver(schedule).observe(document.body,{childList:true,subtree:true});
    refresh();watchDirectory();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
