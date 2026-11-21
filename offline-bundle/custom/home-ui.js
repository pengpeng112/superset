/* 20261121h18（RBAC-FRONTEND-POLISH 批）：千人千面动态权限感知导航（配套 20261120-RBAC-BACKEND
   11 个 报表授权_* 角色体系）。核心机制：
   ①单飞获取当前登录用户真实授权看板白名单 allowedIds：GET /api/v1/dashboard/?q=(page:0,
     page_size:200,columns:!(id,slug))（DASHBOARD_RBAC=True 下后端按用户角色精确返回有权看板）。
     Admin 全通不打接口；结果仅存内存态（60s 短缓存，进入首页/34 目录时静默校验更新），管理员刚
     加角色、员工 F5 即可见——不写 sessionStorage 死缓存。挂 window.hospitalHomeUI.allowedIds 供
     report-ui.js 共享。
   ②CATALOG_REPORTS：从生产 25–31,33 目录 position_json 逐字导出核对的静态目录字典（2026-11-21
     只读导出：26=[40,41,42,43]、29=[50,51,52]、33=[32,35,36,37,38,39]、25=[32,35,41,44,45,46]、
     31=[39,40,58,59,60] 等），含报表名/查询条件摘要。配合 allowedIds：分类计数实时按真实可见张数
     计算；无权分类/驾驶舱/搜索项/收藏 100% 自动隐藏，不再对无权分类发 /api/v1/dashboard/<catId>
     盲请求（彻底淘汰 h7 版 dashboard/61 单点探测与分类 404 刷屏）。
   ③五大视图裁剪：BI 驾驶舱区按可见数 k 动态 1/2/3/4 列排版（0 张彻底隐藏不留空白）；左侧导航与
     34 目录隐藏 0 可见报表的分类整行、按真实张数显示徽标；二级分类页（25–31,33）自动隐藏无权
     子报表行；搜索候选池与「⭐ 我的常用报表」严格限制在 allowedIds 内；34 底部「其他专题」逐链接
     过滤。
   ④零报表权限员工友好引导态：可见业务报表数为 0 时侧栏自动收起（hh-home-nonav 单栏），工作台
     与 34 目录渲染 #hh-no-perm-guide 白底蓝边引导卡（显示工号姓名+开通指引，保留改密入口）。
     未决态（接口未返回）按原样渲染不闪空；仅最近使用列表中已撤权看板行自动隐藏。
   编辑态/管理员视图 100% 不受影响；syncGroupOpen 下钻、h16 展开记忆、h17 收藏夹全部保留。
   20261119h17（BI-ENHANCE 批）：①接入第 4 个 BI 驾驶舱——BI_LINKS 补「全院护理工作量与病区床位效率分析」
   （/superset/dashboard/75/，别名 bi-nursing-bed→75，isQuery 范围 72–75），34 目录 .hh-bi-showcase
   网格改响应式（≥1440px 四列单排、901–1439px 含 1366×768 两列双排，卡片 56px 蓝左边框不变）。
   ②新增「⭐ 我的常用报表」个人收藏夹（纯 localStorage 键 hh_fav_reports_v1_<工号> 按登录用户隔离，
   上限 12 条，严禁调用 /favorite_status/ 等后端接口）——34 目录报表行/驾驶舱卡右侧、8 个二级分类页
   报表行右侧、查询页与驾驶舱 .hh-crumb 主标题右侧注入星标按钮 button.hh-fav-btn（☆ 空心 / ★ 实心
   #f59e0b，点击 preventDefault+stopPropagation 只切状态绝不误跳链接，编辑态全部隐藏）；首页工作台
   收藏数≥1 时在 #hospital-home-hint 下方渲染 #hh-fav-panel 置顶列表（grid-column:2，左侧导航同步跨
   全高 1/4，收藏数=0 不渲染空盒子）；34 目录收藏数≥1 时在驾驶舱入口条下方渲染 #hh-dir-fav-box，
   为 0 时搜索框旁仅显示 12px 灰字提示。不删除业务说明、不改权限与链接。
   20261117h16（FINAL-CLOSEOUT 收尾续）：修复展开态失同步根因——applyDirectoryFilter 每次刷新
   只写 data-hh-open 属性与 ▾ 箭头，却不同步子容器内联 display；当容器内联为 none 而 openSet
   判定展开时，出现“箭头 ▾ 但下方无报表行”（用户截图实态）。h16 新增 syncGroupOpen(li,open)
   统一同步 属性+箭头+内联display 三者，applyDirectoryFilter 两分支与 renderGroup 全部走它。
   20261117h15（FINAL-CLOSEOUT 收尾续）：下钻兜底强化——用户环境（Chrome 98 实报）出现“分组
   已展开（▾）但子容器不可见”：h14 依赖 data-hh-open 属性 + CSS 子选择器（li[data-hh-open="1"]>
   .hh-cat-children{display:block}）联动，任何一环在特定环境失联即整箱不可见。h15 改为 JS 直接
   写内联样式（box.style.display），并在 kybGroup 已存在路径增加自愈：open 且子容器空而缓存有数据
   时强制 renderGroup，缓存缺失时补 loadCategory。h14（34 目录展开状态类型不匹配修复——openSet 会话存储
   里原生分类以数字 id 存取（[33]），applyDirectoryFilter 每次刷新按属性字符串 '33' 比对
   indexOf 恒 -1，导致 8 个原生分类箭头展开后 ~0.2s 被强制弹回（时序实测 t+0 open=1/ss=[33]
   → t+200ms open=0/ss=[33]）。修复：openSet 归一为字符串数组、setCategoryOpen 与
   setupCategoryGroup/applyDirectoryFilter 两处消费端统一按 String(id) 比较。展开记忆自此
   真正生效。h13（抗菌药物监测分组下钻修复：头部整行点击切换展开 + #kyb 锚点 hashchange
   展开，kybHashApply 同时作用于新建与已存在分组）——h7 版该组只有 ▸ 小箭头绑定展开事件，
   点击分类名（34/#kyb 自锚点，已带锚点时二次点击无效）或描述文字（“门急诊处方、住院医嘱、
   微生物与检验检查等 10 项专项查询”，无任何处理器）均无法展开下方 10 张报表；名称链接
   Ctrl/Cmd/Shift/中键仍走默认导航；每次锚点变更放行一次展开，收起后不会被强制回弹。
   绑定展开事件，点击分类名（34/#kyb 自锚点，已带锚点时二次点击无效）或描述文字
   （“门急诊处方、住院医嘱、微生物与检验检查等 10 项专项查询”，无任何处理器）均无法展开下方
   10 张报表。修复：①分组头部整行（名称+描述+计数）点击即切换展开/收起（箭头自身事件不受影响，
   名称链接 Ctrl/Cmd/Shift/中键仍走默认导航）；②hashchange 监听 + kybHashApply 同时作用于
   新建与已存在分组（h12 版锚点展开分支被 if(li) 早返回挡住，已存在时不生效，h13 修正）。
   每次锚点变更放行一次展开，收起后不会被强制回弹。
   20261115h11（FINAL-CLOSEOUT 收尾续）：修复 pageId() 别名解析 Bug——h10 版在数字路径
   未命中时用“完整 pathname”查 DASH_ALIASES 短键，恒不匹配，别名路径下 pageId() 恒为 0；
   改为正则捕获末段（^/superset/dashboard/([^/]+)/?$）后按纯数字/别名判定。逻辑其余不变。
   20261111h10（FINAL-CLOSEOUT 收尾）：pageId() 支持别名路径（mr-discharge-death-detail→2、
   month-work-report-new→32、bi-overview→72、bi-outpatient-flow→73、bi-surgery-quality→74），
   isQuery() 范围补 72–74，使 BI 驾驶舱内表格同样享受 hh-query-ui 紧凑表头与字体变量。
   20261108h9（FINAL-CLOSEOUT 批）：首页工作台“修改密码”快捷入口。全院员工初始密码统一，深层菜单入口难找，
   在 #hospital-home-hint 右侧操作区（“浏览全部报表”旁）新增次要按钮 a.hh-home-pwd-btn（文案“修改密码”，
   链接 /user_info/，高 32px、白底细边框 #d9e1ea、文字 #44536a、悬停变蓝），对无目录权限账号也显示（改密与
   报表权限无关）。不改既有导航/搜索/最近使用逻辑。
   20261104h7（NAV-SEARCH 批）：接入抗菌办分类与快速搜索。侧栏 8 分类下按权限追加“抗菌药物监测（10 项）”（Admin 或角色 343，探测 /api/v1/dashboard/61，无权限不渲染，不暴露死链）；
   34 目录末尾追加同构可展开虚拟分组 li[data-hh-cat-group="kyb"]（展开状态记入 sessionStorage，#kyb 锚点自动展开）；
   首页工作台与 34 目录新增紧凑搜索框（input#hh-report-search）：首页输入实时聚合 categoryCache 弹出下拉浮层可跳转；34 目录输入时自动展开命中分类、只显示匹配报表行、清空恢复原展开状态；
   QUERY_SUMMARY 补 2 与 61–70，isQuery 范围扩到 35–70。样式沿用企业后台列表规范，不改业务链接、权限或查询。
   20261026h6：在 h5 基础上优化左侧导航与目录层级/间距。侧栏改为“报表导航+分类计数”，移除单字方块；34 目录按原生 position_json Markdown 生成“分类→报表”可展开层级（默认展开质控科，sessionStorage 记忆），无权限/失败不伪造内容。相关行高与留白提高至约44px，不恢复大卡片，不改业务链接、权限或查询。 */
(function () {
  'use strict';
  if (window.hospitalHomeUI) return;
  var api=window.hospitalHomeUI={version:'20261121h18'},pending=0,editGrid=null,editStore=null;
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
  /* 可视化驾驶舱（20261107h8 建 3 个，20261119h17 补 75；20261121h18 起按角色过滤可见性） */
  var BI_LINKS=[['全院医疗运营核心指标总览','/superset/dashboard/72/','KPI 总览 · 科室 TOP15 · 转归构成',72],['门急诊流量与窗口负荷监测中心','/superset/dashboard/73/','截至17:00四窗口人次 · 分时段累计',73],['手术与住院医疗质量可视化分析','/superset/dashboard/74/','门诊住院手术构成 · 科室病区TOP15',74],['全院护理工作量与病区床位效率分析','/superset/dashboard/75/','床位负荷 · 分级护理 · 病区排行',75]];
  /* ---------- CATALOG_REPORTS（20261121h18）：从生产 25–31,33 目录 position_json 只读导出
     逐字核对的静态目录字典。desc 为目录页/34 展开层的最终显示文案（GENERIC 行已按
     QUERY_SUMMARY 折算为「查询条件：…」）。kyb 为抗菌办固定 10 项。管理员编辑目录 Markdown 后
     须同步本字典。 ---------- */
  var CATALOG_REPORTS={
    33:{name:'质控科报表',reports:[[32,'月工作报表（新）','住院与门诊两部分，共用统计月份'],[35,'月工作报表（二）新','查询条件：月份'],[36,'病区工作日报表','查询条件：日期'],[37,'手术量统计','查询条件：日期+门诊/住院'],[38,'报表科室维护（只读）','科室清单与床位配置，只读查询'],[39,'检查按开单科室查询人次','查询条件：日期+门诊/住院']]},
    26:{name:'护理部报表',reports:[[40,'床旁结算工作量','查询条件：日期'],[41,'护理工作量月报表','查询条件：月份'],[42,'护理工作量日报表','主表与汇总附区，共用统计日期'],[43,'护理单元工作量','查看报表结果']]},
    25:{name:'月报',reports:[[32,'月工作报表（新）','住院与门诊两部分，共用统计月份'],[35,'月工作报表（二）新','查询条件：月份'],[41,'护理工作量月报表','查询条件：月份'],[44,'月上报数据','查看报表结果'],[45,'医院医疗工作月报表','查看报表结果'],[46,'医院绩效工作月报表','查看报表结果']]},
    27:{name:'门诊',reports:[[47,'门诊转住院入院途径报表','查看报表结果'],[48,'责任组门诊报表','查看报表结果']]},
    28:{name:'急诊',reports:[[49,'急诊分诊统计','查看报表结果']]},
    29:{name:'手术',reports:[[50,'门诊手术数据提取','查看报表结果'],[51,'科室手术质量分析','查看报表结果'],[52,'科室住院手术数据提取','查看报表结果']]},
    30:{name:'门诊流量监测',reports:[[53,'门诊采血人次时段统计','查看报表结果'],[54,'门诊取药人次时段统计','查看报表结果'],[55,'门诊缴费人次查询','查看报表结果'],[56,'门诊挂号量时段统计','查看报表结果'],[57,'门诊超声流量监测','查看报表结果']]},
    31:{name:'绩效考核监测',reports:[[39,'检查按开单科室查询人次','查询条件：日期+门诊/住院'],[40,'床旁结算工作量','查询条件：日期'],[58,'检查人次按开单科室统计','查看报表结果'],[59,'检查人次按执行科室统计（门诊）','查看报表结果'],[60,'绩效考核暨高质量发展监测指标情况','查看报表结果']]}
  };
  /* 34 目录底部「其他专题」链接（20261121h18：逐链接按权限过滤） */
  var SPECIAL_LINKS=[[3,'核心统计报表'],[1,'病案统计'],[2,'病案明细']];
  /* ---------- 权限引擎（20261121h18）：单飞 GET /api/v1/dashboard/ 白名单，60s 内存缓存 ---------- */
  var perm={state:'idle',ids:null,at:0,listeners:[]};
  function permResolved(){return isAdmin()||perm.state==='ok'||perm.state==='fail';}
  function ensureAllowed(cb){
    if(isAdmin()){perm.state='ok';perm.ids=null;if(cb)cb(true);return;}
    if(perm.state==='ok'&&Date.now()-perm.at<60000){if(cb)cb(true);return;}
    if(perm.state==='pending'){if(cb)perm.listeners.push(cb);return;}
    perm.state='pending';if(cb)perm.listeners.push(cb);
    fetch('/api/v1/dashboard/?q=(page:0,page_size:200,columns:!(id,slug))',{credentials:'same-origin'}).then(function(r){
      if(!r.ok)throw new Error('HTTP '+r.status);
      return r.json();
    }).then(function(doc){
      var ids=[];
      ((doc&&doc.result)||[]).forEach(function(x){if(x&&typeof x.id==='number')ids.push(x.id);});
      perm.ids=ids;perm.state='ok';perm.at=Date.now();
      api.allowedIds=ids;api.allowedAt=perm.at;api.allowedTotal=(doc&&doc.count)||ids.length;
      /* 决出后：有权分类清掉未决期的 static 缓存，refresh 重取生产 Markdown（即时编辑生效） */
      Object.keys(categoryCache).forEach(function(k){
        var e=categoryCache[k];
        if(e&&e.static&&k!=='kyb'&&allowed(Number(k)))delete categoryCache[k];
      });
      notify();schedule();
    }).catch(function(){
      /* 失败按最保守空集处理（不渲染死链），下次进入页面重试 */
      perm.ids=[];perm.state='fail';perm.at=Date.now();api.allowedIds=[];notify();schedule();
    });
    function notify(){var ls=perm.listeners;perm.listeners=[];ls.forEach(function(f){try{f(perm.state==='ok');}catch(e){}});}
  }
  /* allowed(id)：Admin 恒真；白名单未决时乐观放行（决出后 schedule 重渲校正）；未决闪现由
     60~80ms 单帧合并抹平，绝不出现永久死链 */
  function allowed(id){
    if(isAdmin())return true;
    if(!permResolved()||!perm.ids)return true;
    return perm.ids.indexOf(id)>=0;
  }
  function staticReports(id){
    if(id==='kyb')return KYB_REPORTS.map(function(r){return {id:r.id,name:r.name,href:'/superset/dashboard/'+r.id+'/',description:QUERY_SUMMARY[r.id]?'查询条件：'+QUERY_SUMMARY[r.id]:''};});
    var c=CATALOG_REPORTS[id];
    if(!c)return [];
    return c.reports.map(function(r){return {id:r[0],name:r[1],href:'/superset/dashboard/'+r[0]+'/',description:r[2]};});
  }
  /* 某分类下当前用户真实可见的子报表（live 缓存优先，静态兜底，均按 allowed 过滤） */
  function visibleReports(id){
    var d=categoryCache[id];
    var src=(d&&d.reports&&d.reports.length)?d.reports:staticReports(id);
    return src.filter(function(r){
      var rid=Number((r.href.match(/\/dashboard\/(\d+)\//)||[])[1]||r.id||0);
      return allowed(rid);
    });
  }
  /* 分类目录页本身是否可达（目录也是看板，受 dashboard_roles 绑定） */
  function catVisible(id){return allowed(id);}
  function visibleBiLinks(){return BI_LINKS.filter(function(b){return allowed(b[3]);});}
  /* 除目录外壳外可见业务报表是否为 0（零报表权限引导态判定；未决按有内容保持布局稳定） */
  function hasAnyVisible(){
    if(!permResolved())return true;
    if(visibleBiLinks().length)return true;
    var key;for(key in CATALOG_REPORTS){if(visibleReports(Number(key)).length)return true;}
    if(visibleReports('kyb').length)return true;
    return allowed(2);
  }
  var categoryCache={},categoryPending={};
  var SS=window.sessionStorage;
  function ssGet(k){try{return SS?SS.getItem(k):null}catch(e){return null}}
  function ssSet(k,v){try{if(SS){if(v===null)SS.removeItem(k);else SS.setItem(k,v)}}catch(e){}}
  var recentAutoDone=false,programmatic=0,pollTimer=0;
  function isHome(){return location.pathname==='/'||/^\/superset\/welcome\/?$/.test(location.pathname);}
  /* 别名看板 → 数字 ID（20261111h10）：病案明细=2、月报=32、BI 驾驶舱=72/73/74 */
  var DASH_ALIASES={'mr-discharge-death-detail':2,'month-work-report-new':32,'bi-overview':72,'bi-outpatient-flow':73,'bi-surgery-quality':74,'bi-nursing-bed':75};
  function pageId(){var m=location.pathname.match(/^\/superset\/dashboard\/([^/]+)\/?$/);if(!m)return 0;if(/^\d+$/.test(m[1]))return +m[1];return DASH_ALIASES[m[1]]||0;}
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
  function isQuery(){var id=pageId();return !editing()&&((id===2||id===32||(id>=35&&id<=70)||(id>=72&&id<=75))||/^\/superset\/dashboard\/(?:mr-discharge-death-detail|month-work-report-new|bi-overview|bi-outpatient-flow|bi-surgery-quality|bi-nursing-bed)\/?$/.test(location.pathname));}
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

  /* ---------- 抗菌办分类（20261104h7 建；20261121h18 改由 allowedIds 精确判定） ---------- */
  function kybList(){
    return {reports:KYB_REPORTS.map(function(r){
      return {id:r.id,name:r.name,href:'/superset/dashboard/'+r.id+'/',description:QUERY_SUMMARY[r.id]?'查询条件：'+QUERY_SUMMARY[r.id]:''};
    })};
  }
  function checkKybAccess(){
    /* 20261121h18：静态清单常驻 categoryCache.kyb，可见性由 allowed(61)（抗菌办角色绑定 61–70）
       判定；不再对 /api/v1/dashboard/61 发探测请求（零盲请求、零 404） */
    if(!categoryCache.kyb)categoryCache.kyb=kybList();
  }
  function kybAllowed(){return allowed(61);}
  /* 首页侧栏：8 分类下方按权限追加“抗菌药物监测”，无权限不渲染（20261121h18：按可见张数） */
  function updateKybNav(){
    var nav=document.getElementById('hh-home-nav');if(!nav)return;
    var item=document.getElementById('hh-home-nav-kyb');
    var n=visibleReports('kyb').length;
    if(!kybAllowed()||!n){if(item)item.remove();return;}
    if(item){
      var c0=item.querySelector('[data-hh-cat-count="kyb"]');
      if(c0&&c0.textContent!==n+' 项')c0.textContent=n+' 项';
      return;
    }
    var all=nav.querySelector('.hh-home-nav-all');
    item=node('a','hh-home-nav-item');item.id='hh-home-nav-kyb';item.href='/superset/dashboard/34/#kyb';
    item.title='抗菌药物监测（'+n+' 项专项查询）';
    item.appendChild(node('span','hh-home-nav-label','抗菌药物监测'));
    var count=node('span','hh-home-nav-count',n+' 项');count.setAttribute('data-hh-cat-count','kyb');count.setAttribute('aria-hidden','true');
    item.appendChild(count);
    nav.insertBefore(item,all);
  }
  /* 34 目录：末尾追加与原生分类同构的可展开虚拟分组；#kyb 锚点自动展开一次 */
  var kybHashOpened=false;
  /* 20261117h13：锚点展开独立成函数，新建与已存在分组都应用（h12 版被 if(li) 早返回挡住） */
  function kybHashApply(li){
    if(location.hash!=='#kyb'||kybHashOpened)return;
    kybHashOpened=true;setCategoryOpen('kyb',true);
    li.setAttribute('data-hh-open','1');
    var hbox=li.querySelector('.hh-cat-children');
    if(hbox)hbox.style.display='block';
    var t=li.querySelector('.hh-cat-toggle');
    if(t){t.textContent='▾';t.setAttribute('aria-expanded','true');}
  }
  function kybGroup(){
    var md=document.querySelector('.dashboard-markdown');if(!md)return;
    var list=md.querySelector('ul');if(!list)return;
    var li=list.querySelector('li[data-hh-cat-group="kyb"]');
    if(!kybAllowed()||!visibleReports('kyb').length){if(li)li.remove();return;}
    if(li){
      /* 20261117h15：自愈——展开态子容器空则强制填充；内联显示与属性保持一致 */
      var hbox2=li.querySelector('.hh-cat-children');
      if(hbox2){
        var isOpen=li.getAttribute('data-hh-open')==='1';
        hbox2.style.display=isOpen?'block':'none';
        if(isOpen&&!hbox2.children.length&&categoryCache.kyb&&categoryCache.kyb.reports){
          hbox2.removeAttribute('data-hh-signature');renderGroup(li,'kyb');
        }else if(isOpen&&!hbox2.children.length&&!categoryCache.kyb){loadCategory('kyb');}
      }
      kybHashApply(li);return;
    }
    li=node('li');
    var a=node('a');a.setAttribute('data-hh-catalog-name','');a.href='/superset/dashboard/34/#kyb';
    a.textContent='抗菌药物监测';a.title='抗菌药物监测';
    var d=node('span');d.setAttribute('data-hh-catalog-description','');
    d.textContent='门急诊处方、住院医嘱、微生物与检验检查等 10 项专项查询';d.title=d.textContent;
    li.appendChild(a);li.appendChild(d);
    list.appendChild(li);
    setupCategoryGroup(li,'kyb');
    /* 20261117h13：头部整行点击切换展开（名称/描述/计数此前无响应，为用户下钻入口） */
    var head=li.querySelector('.hh-cat-head');
    if(head&&!head.getAttribute('data-hh-row-toggle')){
      head.setAttribute('data-hh-row-toggle','1');
      head.addEventListener('click',function(ev){
        if(ev.button!==0)return;
        var t=ev.target&&ev.target.closest?ev.target.closest('.hh-cat-toggle'):null;
        if(t)return; /* 箭头自身已带处理，避免双重切换 */
        var a=ev.target&&ev.target.closest?ev.target.closest('a'):null;
        if(a&&(ev.ctrlKey||ev.metaKey||ev.shiftKey||ev.altKey))return; /* 修饰键/中键走默认导航 */
        if(a)ev.preventDefault(); /* 名称链接指向本页锚点，普通点击改为切换展开 */
        var btn=li.querySelector('.hh-cat-toggle');
        if(btn)btn.click();
      });
    }
    var cbox0=li.querySelector('.hh-cat-children');
    if(cbox0)cbox0.style.display=li.getAttribute('data-hh-open')==='1'?'block':'none';
    kybHashApply(li);
    loadCategory('kyb');
  }
  /* 20261117h13：URL 锚点变为 #kyb 时自动展开一次（收起后不回弹，见 kybHashOpened 单发放行） */
  window.addEventListener('hashchange',function(){
    if(location.hash==='#kyb'&&!kybHashOpened){schedule();}
  });

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
    /* 20261121h18：候选池严格限制在当前用户 allowedIds 内（visibleReports 已按权限过滤），
       并纳入有权的 BI 驾驶舱；绝不搜出无权限报表；同一报表跨分类出现（如 41 同在 25/26）按
       href 去重只留一条 */
    var out=[],seen={};
    function catName(id){for(var i=0;i<NAV.length;i++)if(NAV[i][1]===id)return NAV[i][0];return id==='kyb'?'抗菌药物监测':'';}
    function push(id,reports){
      (reports||[]).forEach(function(r){
        var rid=Number((r.href.match(/\/dashboard\/(\d+)\//)||[])[1]||0);
        if(seen[r.href])return;
        seen[r.href]=1;
        out.push({name:r.name,href:r.href,cat:catName(id),cond:QUERY_SUMMARY[rid]||''});
      });
    }
    NAV.forEach(function(c){push(c[1],visibleReports(c[1]));});
    if(visibleReports('kyb').length)push('kyb',visibleReports('kyb'));
    visibleBiLinks().forEach(function(b){
      if(seen[b[1]])return;
      seen[b[1]]=1;
      out.push({name:b[0],href:b[1],cat:'可视化驾驶舱',cond:b[2]});
    });
    return out;
  }
  function ensureHomeSearch(){
    var hint=document.getElementById('hospital-home-hint');
    if(!hint||!directoryAllowed())return;
    /* 20261121h18：零报表权限员工隐藏搜索框（候选池为空，避免无效操作） */
    if(isZeroPerm()){var zw=document.getElementById('hh-search-wrap');if(zw)zw.remove();return;}
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
  /* 20261117h16：统一同步 展开属性 + 箭头 + 子容器内联display，杜绝三者失同步 */
  function syncGroupOpen(li,open){
    li.setAttribute('data-hh-open',open?'1':'0');
    var t=li.querySelector('.hh-cat-toggle');
    if(t){t.textContent=open?'▾':'▸';t.setAttribute('aria-expanded',open?'true':'false');}
    var cb=li.querySelector('.hh-cat-children');
    if(cb)cb.style.display=open?'block':'none';
  }
  /* 34 目录过滤：命中分类强制展开、只显示匹配报表行；无命中分类临时隐藏；清空恢复 sessionStorage 展开状态 */
  function applyDirectoryFilter(){
    if(pageId()!==34)return;
    var groups=document.querySelectorAll('.dashboard-markdown li[data-hh-cat-group]');
    if(!dirKw){
      Array.prototype.forEach.call(groups,function(li){
        li.style.display='';
        var id=li.getAttribute('data-hh-cat-group');
        var open=openSet().indexOf(String(id))>=0;
        syncGroupOpen(li,open);
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
      syncGroupOpen(li,true);
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
    /* 📊 可视化驾驶舱（20261107h8）：置顶分区，工作台下方、报表分类上方（20261121h18 按权限过滤） */
    nav.appendChild(node('div','hh-home-nav-section hh-home-nav-section-bi','可视化驾驶舱'));
    Array.prototype.forEach.call(BI_LINKS,function(b){
      var a=node('a','hh-home-nav-item hh-home-nav-bi');a.href=b[1];a.title=b[0];
      a.appendChild(node('span','hh-home-nav-label',b[0]));
      a.appendChild(node('span','hh-home-nav-count','BI'));
      a.setAttribute('data-hh-bi-link',b[1]);a.setAttribute('data-hh-bi-id',String(b[3]));nav.appendChild(a);
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
  /* 20261121h18：侧栏千人千面——BI 分区与分类行按真实权限/可见张数显隐（幂等，可反复调用） */
  function updateNavPerm(){
    var nav=document.getElementById('hh-home-nav');if(!nav)return;
    var biSec=nav.querySelector('.hh-home-nav-section-bi'),biN=0;
    Array.prototype.forEach.call(nav.querySelectorAll('[data-hh-bi-id]'),function(a){
      var vis=allowed(Number(a.getAttribute('data-hh-bi-id')));
      a.style.display=vis?'':'none';
      if(vis)biN++;
    });
    if(biSec)biSec.style.display=biN?'':'none';
    Array.prototype.forEach.call(NAV,function(c){
      var a=nav.querySelector('[data-hh-cat-link="'+c[1]+'"]');
      if(!a)return;
      /* 20261121h18：分类行同时要求 ①分类页本身可达（catVisible：目录看板绑定在角色上）
         ②至少 1 张可见子报表——仅持有子报表而无目录绑定的角色（如系统字典维护之于 33）
         不露出打不开的分类死链 */
      var n=visibleReports(c[1]).length;
      a.style.display=(catVisible(c[1])&&n)?'':'none';
    });
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
    /* 20261121h18：徽标显示该用户真实可见张数（visibleReports 已按 allowed 过滤） */
    var data=categoryCache[id];
    var list=visibleReports(id);
    var text=(list.length||(data&&data.reports))?list.length+' 项':(data&&data.error?'—':'…');
    Array.prototype.forEach.call(document.querySelectorAll('[data-hh-cat-count="'+id+'"]'),function(e){
      if(e.textContent!==text)e.textContent=text;
      var title=text;
      if(e.title!==title)e.title=title;
    });
    var group=document.querySelector('[data-hh-cat-group="'+id+'"]');
    if(group)renderGroup(group,id);
    if(pageId()===34&&dirKw)applyDirectoryFilter();
  }
  function loadCategory(id){
    if(categoryCache[id]){updateCounts(id);return Promise.resolve(categoryCache[id]);}
    /* 20261121h18：非 Admin 且白名单未决——allowed() 乐观放行会在此窗口对无权分类发盲请求
       （实测 34 目录对 25/26/33 等连发 404）。未决期一律以 CATALOG_REPORTS 静态清单渲染零请求，
       决出后 ensureAllowed 会清掉有权分类的 static 缓存并 refresh 重取生产 Markdown。 */
    if(!isAdmin()&&!permResolved()){
      categoryCache[id]={reports:staticReports(id),static:true};
      updateCounts(id);
      return Promise.resolve(categoryCache[id]);
    }
    /* 20261121h18：无权分类不再发 /api/v1/dashboard/<catId> 盲请求（控制台 404 刷屏根因），
       直接以 CATALOG_REPORTS 静态清单供渲染；有权分类仍取生产 Markdown（管理员改目录即时生效） */
    if(!catVisible(id)){
      categoryCache[id]={reports:staticReports(id)};
      updateCounts(id);
      return Promise.resolve(categoryCache[id]);
    }
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
    if(raw===null)return ['33'];
    try{var ids=JSON.parse(raw);return Array.isArray(ids)?ids.map(String):['33'];}catch(e){return ['33'];}
  }
  function setCategoryOpen(id,open){
    var sid=String(id);
    var set=openSet().filter(function(x){return x!==sid;});
    if(open)set.push(sid);
    ssSet('hhDirOpenIds',JSON.stringify(set));
  }
  function renderGroup(li,id){
    var box=li.querySelector('.hh-cat-children');if(!box)return;
    var data=categoryCache[id];
    /* 20261121h18：live 缓存优先、CATALOG_REPORTS 静态兜底，统一按 allowed 过滤——
       展开层绝不渲染无权报表死链 */
    var list=visibleReports(id);
    if(!data&&!list.length)return;
    var signature=id+':'+list.map(function(r){return r.name+'|'+r.href+'|'+r.description;}).join(';');
    if(box.getAttribute('data-hh-signature')===signature)return;
    box.setAttribute('data-hh-signature',signature);
    while(box.firstChild)box.removeChild(box.firstChild);
    if(!list.length){
      if(data&&data.error)box.appendChild(node('div','hh-cat-error','暂时无法加载，点击分类名进入分类页。'));
      else box.appendChild(node('div','hh-cat-error','当前账号在该分类下暂无授权报表。'));
      return;
    }
    Array.prototype.forEach.call(list,function(report){
      var a=node('a','hh-cat-report');a.href=report.href;a.title=report.name+(report.description?'：'+report.description:'');
      a.appendChild(node('span','hh-cat-report-name',report.name));
      if(report.description)a.appendChild(node('span','hh-cat-report-desc',report.description));
      box.appendChild(a);
    });
    /* 20261117h16：填充后按当前展开态兜底同步内联 display */
    if(li.getAttribute('data-hh-open')==='1')box.style.display='block';
  }
  function setupCategoryGroup(li,id){
    var root=li.querySelector('[data-hh-catalog-name]')||li.querySelector('a');
    var desc=li.querySelector('[data-hh-catalog-description]');
    var open=openSet().indexOf(String(id))>=0;
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
      /* 20261117h15：内联样式直写，不依赖属性+CSS 选择器联动 */
      var cbox=li.querySelector('.hh-cat-children');
      if(cbox)cbox.style.display=next?'block':'none';
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
      /* 20261121h18：0 可见报表或分类页本身无权的分类整行隐藏（不留死链不留空行）；
         权限未决时先渲染再校正 */
      if(permResolved()&&(!catVisible(id)||!visibleReports(id).length)){li.remove();return;}
      if(!li.hasAttribute('data-hh-cat-group'))setupCategoryGroup(li,id);
      loadCategory(id);
    });
    kybGroup();
    ensureDirectorySearch();
    ensureBiShowcase();
    applySpecialPerm();
    ensureNoPermGuide(md);
    applyDirectoryFilter();
  }
  /* 20261121h18：34 底部「其他专题」逐链接按权限过滤（3/1 为 Admin 保留，2 需病案离院明细角色） */
  function applySpecialPerm(){
    var p=document.querySelector('.dashboard-markdown [data-hh-special]');if(!p)return;
    var vis=0;
    Array.prototype.forEach.call(p.querySelectorAll('a'),function(a){
      var m=(a.getAttribute('href')||'').match(/\/dashboard\/(\d+)\//);
      var ok=!!m&&allowed(Number(m[1]));
      a.style.display=ok?'':'none';
      if(ok)vis++;
    });
    p.style.display=vis?'':'none';
  }
  /* 34 目录顶部：可视化驾驶舱入口条（20261107h8 建；20261121h18 按权限过滤 + 可见数 k 动态列） */
  function ensureBiShowcase(){
    try{
      var md=document.querySelector('.dashboard-markdown');if(!md)return;
      var list=md.querySelector('ul');if(!list)return;
      var old=document.getElementById('hh-bi-showcase');
      var links=visibleBiLinks();
      if(!links.length){if(old)old.remove();return;}
      var sig=links.map(function(b){return b[3];}).join(',');
      if(old&&old.getAttribute('data-hh-sig')===sig&&old.nextElementSibling===list)return;
      if(old)old.remove();
      var box=node('div');box.id='hh-bi-showcase';box.className='hh-bi-showcase';
      box.setAttribute('data-hh-sig',sig);
      /* 可见卡片数 k：1 半宽单列 / 2 双列 / 3 三列 / 4 沿用响应式四列（1366 屏 2×2） */
      box.setAttribute('data-hh-k',String(links.length));
      Array.prototype.forEach.call(links,function(b){
        var a=node('a','hh-bi-card');a.href=b[1];a.title=b[0];
        var t=node('span','hh-bi-card-title','📊 '+b[0]);
        var d=node('span','hh-bi-card-desc',b[2]);
        a.appendChild(t);a.appendChild(d);box.appendChild(a);
      });
      /* ul 不一定是 .dashboard-markdown 直接子节点：插到列表父节点，即落在搜索框与分类列表之间 */
      list.parentNode.insertBefore(box,list);
    }catch(e){/* 入口条自身失败不再拖垮搜索框与目录 */}
  }

  function updateNavCountsAndDirectory(){
    updateNavCounts();
    updateNavPerm();
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
      /* 修改密码快捷入口（20261108h9）：账号自助操作，与目录权限无关，全员可见 */
      var pwd=node('a','hh-home-pwd-btn','修改密码');pwd.href='/user_info/';pwd.title='修改登录密码';
      hint.appendChild(pwd);
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
  /* ---------- 20261121h18：零报表权限员工友好引导态 ---------- */
  function isZeroPerm(){return !isAdmin()&&permResolved()&&!hasAnyVisible();}
  function currentUserName(){
    var u=null;
    try{
      var app=document.getElementById('app'),raw=app&&app.getAttribute('data-bootstrap');
      if(raw){var j=JSON.parse(raw);u=j&&j.user;}
    }catch(e){}
    if(!u)return '';
    var name=String(u.last_name||'')+String(u.first_name||'');
    name=name.trim();
    if(name)return u.username?name+'（工号 '+u.username+'）':name;
    return u.username?'工号 '+u.username:'';
  }
  function noPermGuideNode(){
    var card=node('section');card.id='hh-no-perm-guide';card.setAttribute('role','note');
    card.appendChild(node('div','hh-npg-title','当前账号暂未开通统计报表查阅权限'));
    var who=currentUserName();
    var line1=node('p','hh-npg-text');
    line1.textContent=(who?who+'：':'')+'如需查看科室日常统计、管理月报、BI 驾驶舱或专项明细，请联系信息科为您分配对应的【报表授权】角色。';
    card.appendChild(line1);
    card.appendChild(node('p','hh-npg-sub','（您仍可点击右上角“修改密码”维护个人口令）'));
    return card;
  }
  /* 34 目录内引导卡（顶部，搜索框上方） */
  function ensureNoPermGuide(md){
    var old=document.getElementById('hh-no-perm-guide');
    if(!isZeroPerm()){if(old&&old.parentElement===md)old.remove();return;}
    if(old&&old.parentElement===md)return;
    if(old)old.remove();
    var card=noPermGuideNode();
    var wrap=md.querySelector('.hh-dir-search-wrap');
    if(wrap&&wrap.parentElement===md)md.insertBefore(card,wrap);
    else md.insertBefore(card,md.firstChild);
  }
  /* 工作台引导卡（hint 下方，占第 2 行；折叠面板顺移第 3 行） */
  function ensureNoPermHome(main,allowed){
    var need=!allowed&&permResolved();
    main.setAttribute('data-hh-npg',need?'1':'0');
    var old=document.getElementById('hh-no-perm-guide');
    if(!need){if(old&&old.parentElement===main)old.remove();return;}
    if(old&&old.parentElement===main)return;
    if(old)old.remove();
    var hint=document.getElementById('hospital-home-hint');
    var card=noPermGuideNode();
    if(hint&&hint.parentElement===main)main.insertBefore(card,hint.nextSibling);
    else main.insertBefore(card,main.firstChild);
  }

  function home(){
    var collapse=document.querySelector('main .ant-collapse'),main=collapse&&collapse.closest('main');if(!main)return;
    mark(main,'data-hh-home-content');
    Array.prototype.forEach.call(main.children,function(e){if(e.textContent.trim()==='首页'&&!e.querySelector('a,button,input'))mark(e,'data-hh-home-old-title');});
    /* 20261121h18：目录外壳可达 && 至少有 1 项可见业务内容才渲染侧栏；零报表权限收起侧栏单栏化。
       注意：局部变量命名 layoutAllowed——严禁用 allowed，否则遮蔽全局权限函数 allowed(id)
       （首版 h18 即因此 TypeError 中断最近使用过滤，本行注释即防回归） */
    var layoutAllowed=directoryAllowed()&&hasAnyVisible();
    document.documentElement.classList.toggle('hh-home-nonav',!layoutAllowed);
    buildNav(main,layoutAllowed);
    updateKybNav();
    updateNavPerm();
    header(main,layoutAllowed);
    ensureHomeSearch();
    ensureNoPermHome(main,layoutAllowed);
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
    /* 20261121h18：最近使用列表按权限过滤——已撤权看板的卡片行自动隐藏，不出死链。
       原生卡片标题多为 React onClick 导航（无 href 锚点，实测 003158 首页 5 卡全无 href）：
       先取锚点看板号，取不到再按标题对 CATALOG_REPORTS/BI_LINKS 名称前缀映射
       （容忍「（BI 驾驶舱）」等显示后缀；34 目录外壳对全员可见） */
    if(!isAdmin()){
      var nameMap=[];
      Object.keys(CATALOG_REPORTS).forEach(function(cid){
        CATALOG_REPORTS[cid].reports.forEach(function(r){nameMap.push([r[1],r[0]]);});
      });
      BI_LINKS.forEach(function(b){nameMap.push([b[0],b[3]]);});
      nameMap.push(['统计报表目录',34]);
      Array.prototype.forEach.call(main.querySelectorAll('[data-hh-home-card]'),function(item){
        var id=0,lnk=item.querySelector('a[href*="/dashboard/"]');
        var m=lnk?(lnk.getAttribute('href')||'').match(/\/dashboard\/(\d+)/):null;
        if(m)id=Number(m[1]);
        else{
          var tt=(item.querySelector('[data-hh-row-title]')||{}).textContent||'';
          for(var ni=0;ni<nameMap.length;ni++){
            if(tt&&nameMap[ni][0]&&tt.indexOf(nameMap[ni][0])===0){id=nameMap[ni][1];break;}
          }
        }
        /* h5 卡片压平规则 [data-hh-home-card]{display:block!important} 会压过普通内联
           display:'none'（实测 TypeError 修复后仍可见的根因）——必须 important 优先级写入 */
        if(id){
          if(allowed(id))item.style.removeProperty('display');
          else item.style.setProperty('display','none','important');
        }
      });
    }
    localizeRecent(collapse);
    api.homeReady=true;
  }
  function catalog(){
    /* 20261121h18：二级分类目录页（25–31,33）自动隐藏无权访问的子报表行（如仅有手术明细提取
       角色的员工进入 29 只见 50/51/52）；整分类无权时给出简明提示。34 目录页的分类行由
       directoryTree 整行移除，不在此列。 */
    var allRows=0,allowedRows=0;
    Array.prototype.forEach.call(document.querySelectorAll('.dashboard-markdown li'),function(li){
      var links=li.querySelectorAll('a');if(links.length!==1)return;
      var link=links[0];
      var mid=Number(((link.getAttribute('href')||'').match(/\/dashboard\/(\d+)\//)||[])[1]||0);
      if(mid)allRows++;
      if(mid&&!allowed(mid)){li.style.setProperty('display','none','important');return;}
      if(mid){allowedRows++;li.style.removeProperty('display');}
      tooltip(link);tooltip(li);
      var root=link;while(root.parentElement&&root.parentElement!==li)root=root.parentElement;
      if(root.parentElement!==li||root.textContent.trim()!==link.textContent.trim())return;
      mark(root,'data-hh-catalog-name');
      Array.prototype.forEach.call(li.children,function(e){if(e!==root&&!e.querySelector('a')){mark(e,'data-hh-catalog-description');tooltip(e);}});
    });
    var md=document.querySelector('.dashboard-markdown');
    var notice=document.getElementById('hh-cat-empty-note');
    if(pageId()!==34&&permResolved()&&allRows>0&&allowedRows===0&&md){
      if(!notice){
        notice=node('p','hh-cat-error');notice.id='hh-cat-empty-note';
        notice.textContent='当前账号在该分类下暂无授权报表，如需开通请联系信息科分配对应的【报表授权】角色。';
        md.appendChild(notice);
      }
    }else if(notice)notice.remove();
  }
  function restoreCatalog(){
    Array.prototype.forEach.call(document.querySelectorAll('[data-hh-catalog-description]'),function(e){e.removeAttribute('data-hh-catalog-description');});
  }
  /* ---------- ⭐ 我的常用报表（20261119h17）：纯 localStorage 收藏夹，按登录工号隔离，上限 12 条 ---------- */
  function favUserKey(){
    var u='anon';
    try{
      var app=document.getElementById('app'),raw=app&&app.getAttribute('data-bootstrap');
      if(raw){var j=JSON.parse(raw),un=j&&j.user&&j.user.username;if(un)u=String(un);}
    }catch(e){}
    return 'hh_fav_reports_v1_'+u;
  }
  function favsAll(){try{var a=JSON.parse(localStorage.getItem(favUserKey())||'[]');return Array.isArray(a)?a:[];}catch(e){return [];}}
  function favsSave(a){try{localStorage.setItem(favUserKey(),JSON.stringify(a.slice(0,12)));}catch(e){}}
  function canonHref(href){
    var m=String(href||'').match(/\/superset\/dashboard\/([^/?#]+)/);
    if(!m)return '';
    var k=m[1].replace(/\/$/,'');
    if(/^\d+$/.test(k))return '/superset/dashboard/'+k+'/';
    var id=DASH_ALIASES[k];
    return id?'/superset/dashboard/'+id+'/':href;
  }
  function favIndexOf(arr,href){for(var i=0;i<arr.length;i++)if(arr[i].href===href)return i;return -1;}
  function favToggle(item){
    var arr=favsAll(),i=favIndexOf(arr,item.href);
    if(i>=0)arr.splice(i,1);
    else arr.unshift({id:item.id||0,name:item.name||'',href:item.href,desc:item.desc||''});
    favsSave(arr);
  }
  function mkFavBtn(href,name,desc,id){
    var b=document.createElement('button');
    b.type='button';b.className='hh-fav-btn';b.textContent='☆';
    b.setAttribute('data-hh-fav-href',href);b.setAttribute('data-hh-fav-name',name||'');
    b.setAttribute('data-hh-fav-desc',desc||'');b.setAttribute('data-hh-fav-id',id||0);
    b.setAttribute('aria-label','收藏 '+(name||'报表'));
    if(favIndexOf(favsAll(),href)>=0){b.classList.add('hh-fav-on');b.textContent='★';b.title='从我的常用报表移除';}
    else b.title='加入我的常用报表';
    return b;
  }
  function syncFavBtn(b){
    var on=favIndexOf(favsAll(),b.getAttribute('data-hh-fav-href'))>=0;
    b.classList.toggle('hh-fav-on',on);
    b.textContent=on?'★':'☆';
    b.title=on?'从我的常用报表移除':'加入我的常用报表';
  }
  function favRow(f){
    var a=document.createElement('a');a.className='hh-fav-row';a.href=f.href;a.title=f.name;
    var nm=document.createElement('span');nm.className='hh-fav-name';nm.textContent=f.name||f.href;
    a.appendChild(nm);
    if(f.desc){var d=document.createElement('span');d.className='hh-fav-desc';d.textContent=f.desc;a.appendChild(d);}
    a.appendChild(mkFavBtn(f.href,f.name,f.desc,f.id));
    return a;
  }
  function favHead(n){
    var head=document.createElement('div');head.className='hh-fav-head';
    var t=document.createElement('span');t.setAttribute('class','hh-fav-star');t.textContent='★';
    var label=document.createElement('span');label.textContent=' 我的常用报表（'+n+'）';
    head.appendChild(t);head.appendChild(label);
    var clear=document.createElement('span');clear.className='hh-fav-clear';clear.textContent='清空';
    clear.setAttribute('role','button');clear.setAttribute('tabindex','0');
    clear.addEventListener('click',function(e){e.preventDefault();e.stopPropagation();favsSave([]);schedule();});
    head.appendChild(clear);
    return head;
  }
  /* 首页工作台置顶面板（收藏数≥1 才渲染，=0 不渲染空盒子） */
  function ensureFavHome(main){
    if(!main)return;
    var panel=document.getElementById('hh-fav-panel');
    /* 20261121h18：收藏渲染对照 allowedIds 过滤——已撤权报表自动隐藏不展示死链 */
    var list=favsAll().filter(function(f){
      var m=String(f.href||'').match(/\/dashboard\/(\d+)/);
      return !m||allowed(Number(m[1]));
    }),need=list.length>0&&!editing();
    main.setAttribute('data-hh-fav',need?'1':'0');
    if(!need){if(panel)panel.remove();return;}
    if(!panel){
      panel=document.createElement('div');panel.id='hh-fav-panel';panel.setAttribute('data-hh-home-v4','1');
      /* ant-collapse 嵌套在 React wrapper div 内（非 main 直接子节点）：insertBefore 参照必须是
         main 的直接子节点，否则 NotFoundError——取 collapse 的顶层祖先作锚点 */
      var collapse=main.querySelector('.ant-collapse');
      var anchor=collapse;
      while(anchor&&anchor.parentElement&&anchor.parentElement!==main)anchor=anchor.parentElement;
      if(anchor&&anchor.parentElement===main)main.insertBefore(panel,anchor);
      else main.appendChild(panel);
    }
    if(panel.getAttribute('data-hh-n')!==String(list.length)||!panel.querySelector('.hh-fav-row')){
      while(panel.firstChild)panel.removeChild(panel.firstChild);
      panel.setAttribute('data-hh-n',String(list.length));
      panel.appendChild(favHead(list.length));
      Array.prototype.forEach.call(list,function(f){panel.appendChild(favRow(f));});
    }
  }
  /* 34 目录：驾驶舱入口条下收藏盒（≥1）；=0 时搜索框旁仅 12px 灰字轻提示 */
  function ensureFavDir(){
    var md=document.querySelector('.dashboard-markdown');if(!md)return;
    var box=document.getElementById('hh-dir-fav-box');
    var hint=document.getElementById('hh-dir-fav-hint');
    /* 20261121h18：同 ensureFavHome，按 allowedIds 过滤已撤权收藏 */
    var list=favsAll().filter(function(f){
      var m=String(f.href||'').match(/\/dashboard\/(\d+)/);
      return !m||allowed(Number(m[1]));
    }),need=list.length>0&&!editing();
    if(!need){
      if(box)box.remove();
      var wrap=document.querySelector('.hh-dir-search-wrap');
      if(wrap&&!hint){
        hint=document.createElement('span');hint.id='hh-dir-fav-hint';
        hint.textContent='提示：点击报表旁的 ☆ 可将常用报表置顶到首页';
        wrap.insertBefore(hint,wrap.firstChild);
      }
      return;
    }
    if(hint)hint.remove();
    var showcase=document.getElementById('hh-bi-showcase');
    var anchor=showcase?showcase.nextSibling:null;
    if(!box){
      box=document.createElement('div');box.id='hh-dir-fav-box';
      if(anchor&&anchor.parentNode)anchor.parentNode.insertBefore(box,anchor);
      else md.appendChild(box);
    }
    if(box.getAttribute('data-hh-n')!==String(list.length)||!box.querySelector('.hh-fav-row')){
      while(box.firstChild)box.removeChild(box.firstChild);
      box.setAttribute('data-hh-n',String(list.length));
      box.appendChild(favHead(list.length));
      Array.prototype.forEach.call(list,function(f){box.appendChild(favRow(f));});
    }
  }
  /* 星标注入：34 目录报表行+驾驶舱卡、分类页（25–31,33）报表行、查询页/驾驶舱面包屑主标题右侧 */
  function ensureFavStars(){
    if(editing()){
      Array.prototype.forEach.call(document.querySelectorAll('.hh-fav-btn'),function(b){b.remove();});
      return;
    }
    var pid=pageId();
    if(pid===34||(pid>=25&&pid<=31)||pid===33){
      Array.prototype.forEach.call(document.querySelectorAll('.dashboard-markdown .hh-cat-report'),function(a){
        if(a.querySelector('.hh-fav-btn'))return;
        var nm=a.querySelector('.hh-cat-report-name'),ds=a.querySelector('.hh-cat-report-desc');
        var href=a.getAttribute('href')||'';
        var num=(href.match(/\/dashboard\/(\d+)/)||[])[1]||0;
        a.appendChild(mkFavBtn(canonHref(href),(nm?nm.textContent:'').trim(),(ds?ds.textContent:'').trim(),Number(num)));
      });
      Array.prototype.forEach.call(document.querySelectorAll('.hh-bi-card'),function(a){
        if(a.querySelector('.hh-fav-btn'))return;
        var t=a.querySelector('.hh-bi-card-title'),d=a.querySelector('.hh-bi-card-desc');
        a.appendChild(mkFavBtn(canonHref(a.getAttribute('href')),(t?t.textContent.replace(/^📊\s*/,''):'').trim(),(d?d.textContent:'').trim(),0));
      });
    }
    if((pid>=25&&pid<=31)||pid===33){
      Array.prototype.forEach.call(document.querySelectorAll('.dashboard-markdown li'),function(li){
        if(li.getAttribute('data-hh-cat-group')||li.querySelector('.hh-fav-btn'))return;
        var link=li.querySelector('a[href*="/superset/dashboard/"]');if(!link)return;
        var root=link;while(root.parentElement&&root.parentElement!==li)root=root.parentElement;
        var desc=li.querySelector('[data-hh-catalog-description]');
        var href=link.getAttribute('href')||'';
        var num=(href.match(/\/dashboard\/(\d+)/)||[])[1]||0;
        li.appendChild(mkFavBtn(canonHref(href),(root.textContent||'').trim(),(desc?desc.textContent:'').trim(),Number(num)));
      });
    }
    if(isQuery()&&pid!==34){
      var cur=document.querySelector('#hh-crumb .hh-crumb-cur');
      if(cur&&cur.parentElement&&!cur.parentElement.querySelector('.hh-fav-btn')){
        cur.parentElement.appendChild(mkFavBtn(canonHref(location.pathname),(cur.textContent||'').trim(),'',pid));
      }
    }
  }
  document.addEventListener('click',function(e){
    var b=e.target&&e.target.closest?e.target.closest('.hh-fav-btn'):null;
    if(!b)return;
    /* 防误触：只切换收藏状态，绝不触发外层链接跳转或分类收起 */
    e.preventDefault();e.stopPropagation();
    favToggle({href:b.getAttribute('data-hh-fav-href'),name:b.getAttribute('data-hh-fav-name'),
               desc:b.getAttribute('data-hh-fav-desc'),id:Number(b.getAttribute('data-hh-fav-id')||0)});
    Array.prototype.forEach.call(document.querySelectorAll('.hh-fav-btn'),function(x){syncFavBtn(x);});
    schedule();
  },true);

  function refresh(){
    pending=0;var h=isHome(),c=isCatalog(),q=isQuery();
    document.documentElement.classList.toggle('hh-home',h);document.documentElement.classList.toggle('hh-catalog-compact',c);document.documentElement.classList.toggle('hh-query-ui',q);
    document.documentElement.classList.toggle('hh-native-editor',editing());
    if(h){home();ensureFavHome(document.querySelector('main[data-hh-home-content]'));}
    else{
      recentAutoDone=false;
      document.documentElement.classList.remove('hh-home-nonav');
      removeById('hh-home-nav');removeById('hospital-home-hint');removeById('hh-home-management');
      var fp=document.getElementById('hh-fav-panel');if(fp)fp.remove();
      removeById('hh-no-perm-guide');
    }
    if(c){catalog();ensureFavDir();}
    else{restoreCatalog();var db=document.getElementById('hh-dir-fav-box');if(db)db.remove();var dh=document.getElementById('hh-dir-fav-hint');if(dh)dh.remove();}
    if(c||q)ensureFavStars();
    /* 20261121h18：进入首页/34 目录即静默校验白名单（60s 内存缓存），加角色后 F5 立即可见；
       checkKybAccess 仅固化静态抗菌办清单，不再发探测请求 */
    if(h||pageId()===34){ensureAllowed();checkKybAccess();updateNavCountsAndDirectory();}
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
      'html.hh-home main[data-hh-home-content]{display:grid!important;grid-template-columns:224px minmax(0,1fr);grid-template-rows:auto auto auto;gap:0 20px;align-items:start;align-content:start;width:100%;max-width:1440px;margin:0 auto;box-sizing:border-box;padding:16px 20px 24px!important;background:var(--hh-page)}',
      'html.hh-home.hh-home-nonav main[data-hh-home-content]{grid-template-columns:minmax(0,1fr)}',
      'html.hh-home.hh-home-nonav #hospital-home-hint,html.hh-home.hh-home-nonav main .ant-collapse{grid-column:1}',
      'html.hh-home [data-hh-home-old-title]{display:none!important}',
      /* 20261119h17：收藏面板行——有收藏时 main[data-hh-fav="1"]，面板占第 2 行、折叠面板顺移第 3 行，左侧导航跨全高 */
      'html.hh-home #hh-home-nav{grid-column:1;grid-row:1/4;display:flex;flex-direction:column;align-self:start;position:sticky;top:16px;background:var(--hh-panel);border:1px solid var(--hh-border);border-radius:var(--hh-radius);padding:8px 0 6px;margin:0;box-sizing:border-box;min-width:0}',
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
      /* 修改密码次要按钮（20261108h9）：白底细边框，悬停变蓝；无目录权限时独占右侧同样成立 */
      '#hospital-home-hint .hh-home-pwd-btn{flex:none;display:inline-flex;align-items:center;height:32px;margin-left:12px;padding:0 14px;border:1px solid #d9e1ea;border-radius:4px;background:#fff;color:#44536a!important;font-size:13px;line-height:30px;text-decoration:none!important;white-space:nowrap;box-sizing:border-box}',
      '#hospital-home-hint .hh-home-pwd-btn:hover{border-color:#1677c8;color:#1677c8!important;background:#f3f9ff}',
      '#hospital-home-hint .hh-home-pwd-btn:focus-visible{outline:2px solid #1677c8;outline-offset:2px}',
      'html.hh-home.hh-home-nonav #hospital-home-hint .hh-home-pwd-btn{margin-left:auto}',
      'html.hh-home main .ant-collapse{grid-column:2;grid-row:2;display:block;margin:0!important;padding:0!important;border:0!important;background:transparent}',
      'html.hh-home main[data-hh-fav="1"] .ant-collapse{grid-row:3}',
      /* ⭐ 我的常用报表（20261119h17）：首页置顶面板（标题行 38px + 行高 40px 紧凑列表） */
      '#hh-fav-panel{grid-column:2;grid-row:2;min-width:0;margin:0 0 12px;background:var(--hh-panel);border:1px solid var(--hh-border);border-radius:var(--hh-radius);box-sizing:border-box;overflow:hidden}',
      '#hh-fav-panel .hh-fav-head{display:flex;align-items:center;height:38px;padding:0 16px;border-bottom:1px solid var(--hh-line);font-size:14px;font-weight:600;color:var(--hh-text)}',
      '#hh-fav-panel .hh-fav-head .hh-fav-star{color:#f59e0b;margin-right:8px;font-size:14px}',
      '#hh-fav-panel .hh-fav-head .hh-fav-clear{margin-left:auto;font-size:12px;font-weight:400;color:var(--hh-muted);cursor:pointer}',
      '#hh-fav-panel .hh-fav-head .hh-fav-clear:hover{color:var(--hh-blue)}',
      '#hh-fav-panel .hh-fav-row{display:flex;align-items:center;height:40px;padding:0 16px;border-bottom:1px solid var(--hh-line);font-size:14px;text-decoration:none;color:var(--hh-text);min-width:0}',
      '#hh-fav-panel .hh-fav-row:last-child{border-bottom:0}',
      '#hh-fav-panel .hh-fav-row:hover{background:#f3f8fc}',
      '#hh-fav-panel .hh-fav-row .hh-fav-name{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--hh-text);font-size:14px;line-height:22px}',
      '#hh-fav-panel .hh-fav-row:hover .hh-fav-name{color:var(--hh-blue)}',
      '#hh-fav-panel .hh-fav-row .hh-fav-desc{flex:none;max-width:40%;margin-left:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;color:var(--hh-muted)}',
      '#hh-fav-panel .hh-fav-row .hh-fav-btn{flex:none;margin-left:10px}',
      /* 星标按钮（34 目录行/分类页行/驾驶舱卡/查询页面包屑共用） */
      '.hh-fav-btn{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;padding:0;border:0;border-radius:4px;background:transparent;color:#a8b3bf;font-size:16px;line-height:26px;cursor:pointer;flex:none;font-family:inherit}',
      '.hh-fav-btn:hover{color:#f59e0b;background:#fff7e6}',
      '.hh-fav-btn.hh-fav-on{color:#f59e0b}',
      '.hh-fav-btn:focus-visible{outline:2px solid #1677c8;outline-offset:1px}',
      '.hh-bi-card .hh-fav-btn{position:absolute;top:6px;right:6px}',
      'html.hh-native-editor .hh-fav-btn,html.hh-native-editor #hh-fav-panel,html.hh-native-editor #hh-dir-fav-box{display:none!important}',
      'html.hh-catalog-compact .dashboard-markdown .hh-cat-report{grid-template-columns:minmax(220px,300px) minmax(0,1fr) 30px}',
      /* 34 目录置顶收藏盒 + 无收藏轻提示 */
      '#hh-dir-fav-box{margin:0 0 12px;background:#fff;border:1px solid #e4e9ef;border-radius:8px;overflow:hidden;box-sizing:border-box}',
      '#hh-dir-fav-box .hh-fav-head{display:flex;align-items:center;height:38px;padding:0 16px;border-bottom:1px solid #eef2f6;font-size:14px;font-weight:600;color:#263445}',
      '#hh-dir-fav-box .hh-fav-head .hh-fav-star{color:#f59e0b;margin-right:8px}',
      '#hh-dir-fav-box .hh-fav-row{display:flex;align-items:center;height:40px;padding:0 16px;border-bottom:1px solid #eef2f6;font-size:14px;text-decoration:none;color:#263445;min-width:0}',
      '#hh-dir-fav-box .hh-fav-row:last-child{border-bottom:0}',
      '#hh-dir-fav-box .hh-fav-row:hover{background:#f3f8fc}',
      '#hh-dir-fav-box .hh-fav-row .hh-fav-name{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#1677c8}',
      '#hh-dir-fav-box .hh-fav-row .hh-fav-desc{flex:none;max-width:40%;margin-left:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;color:#909399}',
      '#hh-dir-fav-box .hh-fav-row .hh-fav-btn{flex:none;margin-left:10px}',
      '#hh-dir-fav-hint{font-size:12px;color:#909399;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1;min-width:0;margin-right:8px}',
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
      /* 可视化驾驶舱入口条（34 目录）：20261119h17 起 4 卡响应式网格——≥1440px 四列单排，
         901–1439px（含 1366×768）两列双排；卡片 56px 蓝左边框不变 */
      '.hh-bi-showcase{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:0 0 12px}',
      '@media(min-width:1440px){.hh-bi-showcase{grid-template-columns:repeat(4,minmax(0,1fr))}}',
      /* 20261121h18：BI 入口条按实际可见卡片数 k 动态列（1 半宽单列 / 2 双列 / 3 三列；k=4 沿用上方响应式） */
      '.hh-bi-showcase[data-hh-k="1"]{grid-template-columns:minmax(0,560px)}',
      '.hh-bi-showcase[data-hh-k="2"]{grid-template-columns:repeat(2,minmax(0,1fr))}',
      '.hh-bi-showcase[data-hh-k="3"]{grid-template-columns:repeat(3,minmax(0,1fr))}',
      '@media(max-width:900px){.hh-bi-showcase[data-hh-k="1"]{grid-template-columns:minmax(0,1fr)}.hh-bi-showcase[data-hh-k="3"]{grid-template-columns:repeat(2,minmax(0,1fr))}}',
      /* 20261121h18：零报表权限引导卡（工作台 + 34 目录共用，白底 3px 蓝左边框） */
      'html.hh-home #hh-no-perm-guide{grid-column:2;grid-row:2;min-width:0;margin:0 0 12px;padding:18px 22px;background:var(--hh-panel);border:1px solid var(--hh-border);border-left:3px solid #1677c8;border-radius:8px;box-sizing:border-box}',
      'html.hh-home.hh-home-nonav #hh-no-perm-guide{grid-column:1}',
      'html.hh-home main[data-hh-npg="1"] .ant-collapse{grid-row:3}',
      'html.hh-home main[data-hh-npg="1"][data-hh-fav="1"] #hh-fav-panel{grid-row:2}',
      '#hh-no-perm-guide .hh-npg-title{margin:0 0 8px;font-size:15px;line-height:24px;font-weight:600;color:#263445}',
      '#hh-no-perm-guide .hh-npg-text{margin:0;font-size:14px;line-height:24px;color:#44536a}',
      '#hh-no-perm-guide .hh-npg-sub{margin:8px 0 0;font-size:12px;line-height:20px;color:#8a97a5}',
      'html.hh-catalog-compact .dashboard-markdown #hh-no-perm-guide{margin:0 0 12px;padding:16px 20px;background:#fff;border:1px solid #e4e9ef;border-left:3px solid #1677c8;border-radius:8px}',
      'html.hh-catalog-compact .dashboard-markdown #hh-no-perm-guide .hh-npg-title{font-size:15px;line-height:24px;font-weight:600;color:#263445}',
      'html.hh-catalog-compact .dashboard-markdown #hh-no-perm-guide .hh-npg-text{font-size:14px;line-height:24px;color:#44536a}',
      'html.hh-catalog-compact .dashboard-markdown #hh-no-perm-guide .hh-npg-sub{font-size:12px;color:#8a97a5}',
      '.hh-bi-card{display:flex;flex-direction:column;justify-content:center;gap:2px;height:56px;padding:0 12px;background:#fff;border:1px solid #e4e9ef;border-left:3px solid #1677c8;border-radius:6px;text-decoration:none;box-sizing:border-box;min-width:0;position:relative}',
      '.hh-bi-card:hover{background:#f3f8fc}',
      '.hh-bi-card .hh-bi-card-title{font-size:14px;font-weight:600;color:#263445;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '.hh-bi-card .hh-bi-card-desc{font-size:12px;color:#909399;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      /* 首页侧栏「可视化驾驶舱」分区标题：蓝色小标识 */
      'html.hh-home #hh-home-nav .hh-home-nav-section-bi{display:flex;align-items:center;gap:6px;font-weight:600;color:var(--hh-blue)}',
      'html.hh-home #hh-home-nav .hh-home-nav-section-bi::before{content:"";flex:none;width:4px;height:12px;border-radius:2px;background:var(--hh-blue)}',
      'html.hh-query-ui .dashboard-markdown .dashboard-component{background:#fafbfc!important;border-left-color:var(--hui-border)!important;color:#606266!important;box-shadow:none!important}',
      'html.hh-query-ui .superset-chart-table table,html.hh-query-ui #hospital-monthly-report table{font-size:14px!important}',
      'html.hh-query-ui .superset-chart-table th,html.hh-query-ui #hospital-monthly-report th{background:var(--hui-page)!important;color:var(--hui-text)!important;border-color:var(--hui-line)!important}',
      'html.hh-query-ui .superset-chart-table td,html.hh-query-ui #hospital-monthly-report td{height:var(--hui-row)!important;box-sizing:border-box;border-color:var(--hui-line)!important}',
      'html.hh-query-ui #hospital-monthly-report{border-color:var(--hui-border);border-radius:var(--hui-radius);box-shadow:none;color:var(--hui-text)}',
      'html.hh-query-ui #hospital-monthly-report h2{font-size:16px;color:var(--hui-text)}',
      'html.hh-query-ui #hospital-monthly-report th.hm-group{font-size:15px;background:#f0f2f5!important}',
      'html.hh-query-ui .superset-chart-table tbody tr:hover td,html.hh-query-ui #hospital-monthly-report tr:hover td{background:#f3f8fc!important}',
      '@media(min-width:901px) and (max-width:1199px){html.hh-home main[data-hh-home-content]{grid-template-columns:200px minmax(0,1fr)}html.hh-home #hospital-home-hint{flex-wrap:wrap;gap:8px 12px}#hospital-home-hint .hh-home-desc{white-space:normal;overflow:visible;text-overflow:clip}}',
      '@media(max-width:900px){html.hh-home main[data-hh-home-content]{grid-template-columns:minmax(0,1fr);padding:14px 12px 20px!important}html.hh-home #hh-home-nav{grid-column:1/-1;grid-row:1;position:static;flex-direction:row;align-items:center;gap:0;padding:0 4px;margin:0 0 12px;overflow-x:auto;overflow-y:hidden}html.hh-home #hh-home-nav .hh-home-nav-title,html.hh-home #hh-home-nav .hh-home-nav-section,html.hh-home #hh-home-nav .hh-home-nav-count{display:none}html.hh-home #hh-home-nav .hh-home-nav-item{flex:none;height:36px;margin:4px 2px;padding:0 10px}html.hh-home #hh-home-nav .hh-home-nav-badge{display:none}html.hh-home #hh-home-nav .hh-home-nav-all{flex:none;height:36px;margin:4px 2px;padding:0 10px;border-top:0}html.hh-home #hospital-home-hint{grid-column:1/-1;grid-row:2;flex-wrap:wrap;gap:8px 12px}#hospital-home-hint h1{white-space:normal}#hospital-home-hint .hh-home-desc{white-space:normal;overflow:visible;text-overflow:clip;flex-basis:100%}html.hh-home main .ant-collapse{grid-column:1/-1;grid-row:3}html.hh-home [data-hh-home-grid]{--hui-columns:minmax(0,1fr) 120px 78px 68px}html.hh-home [data-hh-home-grid][data-hh-has-state=false]{--hui-columns:minmax(0,1fr) 120px 68px}html.hh-catalog-compact [data-hh-catalog-name]{flex-basis:200px}html.hh-catalog-compact .dashboard-markdown .hh-cat-head [data-hh-catalog-description]{display:none}html.hh-catalog-compact .dashboard-markdown .hh-cat-report{grid-template-columns:minmax(180px,240px) minmax(0,1fr) 30px}}',
      '@media(max-width:600px){#hospital-home-hint .hh-home-desc{display:none}#hospital-home-hint .hh-home-primary{padding:0 10px}#hospital-home-hint .hh-home-pwd-btn{margin-left:8px;padding:0 10px}html.hh-home [data-hh-home-grid]{--hui-columns:minmax(0,1fr) 72px 64px}html.hh-home [data-hh-home-grid][data-hh-has-state=false]{--hui-columns:minmax(0,1fr) 64px}html.hh-home [data-hh-row-info],html.hh-home .hh-list-columns>span:nth-child(2){display:none}html.hh-home [data-hh-row-state]{grid-column:2}html.hh-home [data-hh-home-toolbar] .nav-right{flex-wrap:wrap}html.hh-catalog-compact [data-hh-catalog-name]{flex-basis:150px}html.hh-catalog-compact .dashboard-markdown .hh-cat-head{gap:8px;padding-left:8px;padding-right:8px}html.hh-catalog-compact .dashboard-markdown .hh-cat-head [data-hh-catalog-name]{flex:1;min-width:0}html.hh-catalog-compact .dashboard-markdown .hh-cat-children{margin-left:38px;padding-left:6px}html.hh-catalog-compact .dashboard-markdown .hh-cat-report{grid-template-columns:minmax(0,1fr) 30px;min-height:40px}html.hh-catalog-compact .dashboard-markdown .hh-cat-report-desc{display:none}}'
    ].join('\n');document.head.appendChild(style);
    var push=history.pushState;history.pushState=function(){var r=push.apply(history,arguments);schedule();return r;};
    window.addEventListener('popstate',schedule);window.addEventListener('resize',schedule);window.addEventListener('hashchange',schedule);new MutationObserver(schedule).observe(document.body,{childList:true,subtree:true});
    refresh();watchDirectory();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
