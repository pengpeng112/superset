/* 报表目录与查询页显示增强。仅作用于已迁移页面；不修改查询结果和访问权限。
   20261105f10（TOOLBAR-GUARD 批）：单表查询页（2/35–70，不含 32 月报）注入显式报表工具条
   .hh-query-toolbar——左侧实时数据摘要（loading 秒级计时 / 成功后行数与耗时，读自 Redux
   queriesResponse[0] 与 chartStatus），右侧显式「导出 Excel (.xlsx)」「导出 CSV」「紧凑/标准行高」
   按钮；导出采用「查询偷听重放」：hook fetch 缓存图表数据查询的 QueryContext payload（含 native
   filter 展开后的 filters，与页面行数严格同条件），导出时原样重放仅改 result_format=xlsx/csv、
   result_type=full、仅保留主数据查询（多查询会被后端打包 zip）、分页图表恢复图表 row_limit 全量；
   服务端分页图表的总数自前端分页器（末页×页长）估算并标“（约）”；CSV 前置 UTF-8 BOM 防医院 Office 乱码；
   loading/失败/0 行时导出禁用；行高切换 html.hh-density-compact 并记忆 sessionStorage(hhTableDensity)；
   成功且行数 ≥ row_limit 时在工具条下插入 .hh-truncation-banner 橙色截断强警告（低于上限自动移除）；
   fitTables 扣除工具条与横幅高度。不改任何业务 SQL 与统计口径。
   20261104f9（NAV-SEARCH 批）：FILTER_SUMMARY 补看板 2 与抗菌办 61–70；
   pageId()/pageState() 支持 month-work-report-new=32、mr-discharge-death-detail=2 别名并把查询页范围扩到 2/32/35–70；
   crumb() 为抗菌办 61–70 固定“报表目录/抗菌药物监测/当前报表”（原生通用返回链接统一隐藏），看板 2 固定“报表目录/病案专项/当前报表”。
   20261025f8（OTHERUI 批，f7 成功空集基础上隐藏原生空态整容器，避免双提示）：顶部菜单按“首页/报表目录/资源管理”分组（资源链接实时取自原生菜单，
   原生权限过滤不变，普通员工不出现新菜单）；当前页 active 与 aria-current；右侧图标按钮补 title/aria；
   设置菜单服务端词条（信息/List Groups/Database Connections）按 href 精确改显示；
   目录/分类/查询页统一面包屑并复用 Markdown 返回链接（原链接隐藏，不出现两个可见返回入口）；
   查看态隐藏草稿/作者/修改时间（编辑态由 hh-native-editor 完整保留）；
   34 既有专项收口为底部“其他专题”、看板管理移至页面头部次要按钮（仅有权者可见）；
   分类目录行以真实筛选契约摘要替换通用空话；visit_id 下界/上界 仅改显示为“就诊次数下限/上限”；
   成功空集提示改写（加载/失败/必选缺失/权限错误的原生状态不动）；管理列表头部收口与筛选两行换行。 */
(function () {
  'use strict';
  if (window.hospitalReportUI) return;
  window.hospitalReportUI = { version: '20261105f10' };
  var categories = [25, 26, 27, 28, 29, 30, 31, 33, 34];
  var CATEGORY_NAMES = {25:'月报',26:'护理部报表',27:'门诊',28:'急诊',29:'手术',30:'门诊流量监测',31:'绩效考核监测',33:'质控科报表',34:'报表目录'};
  var canOpenDirectory = false;
  var pending = 0;
  var querySubmitSeen = {};
  // 目录“查询条件”摘要：仅来自 2026-10-25 生产只读采集的原生筛选标题（filter-contracts.json），
  // 无可靠摘要的页不在此列，保留原说明。
  var FILTER_SUMMARY = {
    2: '出院日期',
    32: '日期', 35: '月份', 36: '日期', 37: '日期+门诊/住院', 39: '日期', 40: '日期',
    41: '月份', 42: '日期', 43: '日期', 44: '日期', 45: '月份', 46: '月份', 47: '日期',
    48: '日期', 49: '日期', 50: '月份', 51: '月份+科室', 52: '月份+科室', 53: '日期',
    54: '日期', 55: '日期', 56: '日期', 57: '日期', 58: '日期+门诊/住院',
    59: '日期+就诊次数上下限', 60: '统计期间',
    /* 抗菌办查询页（20261104f9，摘要来自各页原生筛选标题） */
    61: '开单日期', 62: '出院日期', 63: '统计季度', 64: '出院日期', 65: '医嘱日期',
    66: '出院日期', 67: '出院日期', 68: '出院日期', 69: '出院日期', 70: '记录日期'
  };
  var GENERIC_DESC = '设置查询条件，查看报表结果';
  var st = document.createElement('style');
  st.id = 'hospital-report-ui-style';
  st.textContent = [
    /* 明亮底色：目录/分类/查询/管理页面统一 #f5f7fa，杜绝黑底 */
    'html.hh-catalog-compact body,html.hh-report-page body{background:#f5f7fa!important}',
    'html.hh-catalog-compact [data-test="dashboard-content-wrapper"],html.hh-report-page [data-test="dashboard-content-wrapper"]{background:#f5f7fa!important}',
    'html.hh-admin-page body{background:#f5f7fa!important}',
    /* 查看态只保留面包屑中的一个主标题；编辑态由下方作用域退出，原生标题完整恢复 */
    'html.hh-catalog-compact .dashboard-header-container [data-hh-native-title],html.hh-report-page .dashboard-header-container [data-hh-native-title]{display:none!important}',
    /* 查看态管理元信息退出（编辑态时 hh-catalog-compact/hh-query-ui 由 home-ui 摘除，原生完整恢复） */
    'html.hh-catalog-compact .dashboard-header-container .ant-tag,html.hh-report-page .dashboard-header-container .ant-tag{display:none!important}',
    'html.hh-catalog-compact .dashboard-header-container [data-hh-metadata],html.hh-report-page .dashboard-header-container [data-hh-metadata]{display:none!important}',
    'html.hh-catalog-compact .dashboard-header-container [class*=metadata-text],html.hh-catalog-compact .dashboard-header-container [class*=metadata-icon],html.hh-report-page .dashboard-header-container [class*=metadata-text],html.hh-report-page .dashboard-header-container [class*=metadata-icon]{display:none!important}',
    /* 面包屑（当前段承担唯一主标题，前级为 13px 导航） */
    '.hh-crumb{display:flex;align-items:baseline;gap:6px;min-height:28px;margin:0 0 2px;font-size:13px;line-height:22px;color:#718096;white-space:nowrap;overflow:hidden}',
    '.hh-crumb a{color:#1677c8;text-decoration:none}',
    '.hh-crumb a:hover{text-decoration:underline}',
    '.hh-crumb .hh-crumb-sep{color:#a8b3bf}',
    '.hh-crumb .hh-crumb-cur{color:#263445;border:0;margin:0;padding:0;font-size:16px;line-height:26px;font-weight:600;background:transparent;max-width:min(520px,48vw);overflow:hidden;text-overflow:ellipsis}',
    /* 编辑看板降为次要按钮（仅查看态页面；编辑态原生按钮完整保留） */
    'html.hh-catalog-compact .right-button-panel [data-test="edit-dashboard-button"],html.hh-report-page .right-button-panel [data-test="edit-dashboard-button"]{height:28px!important;padding:0 12px!important;font-size:13px!important;background:#fff!important;border-color:#d9e1ea!important;color:#44536a!important}',
    /* 页面头部次要链接（看板管理 / 返回报表目录） */
    '.hh-head-link{display:inline-flex;align-items:center;height:28px;padding:0 12px;margin-right:8px;border:1px solid #d9e1ea;border-radius:4px;background:#fff;color:#1677c8!important;font-size:13px;line-height:26px;text-decoration:none!important;white-space:nowrap}',
    '.hh-head-link:hover{border-color:#9ec7e8;color:#0f5da4!important}',
    '.hh-list-back{margin-left:12px;font-size:13px}',
    '.hh-list-back a{color:#1677c8!important;text-decoration:none}',
    '.hh-list-back a:hover{text-decoration:underline}',
    /* Markdown 返回链接隐藏（面包屑复用其地址，不出现两个可见返回入口） */
    'html.hh-catalog-compact .dashboard-markdown [data-hh-backlink],html.hh-report-page .dashboard-markdown [data-hh-backlink]{display:none!important}',
    'html.hh-catalog-compact .dashboard-markdown [data-hh-backlink-empty],html.hh-report-page .dashboard-markdown [data-hh-backlink-empty]{display:none!important}',
    /* 目录页：隐藏与主标题重复的 Markdown 标题；既有专项收口为底部“其他专题” */
    'html.hh-catalog-compact .dashboard-markdown h2{display:none!important}',
    'html.hh-catalog-compact .dashboard-markdown [data-hh-special]{margin:16px 0 0!important;padding:10px 12px 2px!important;border-top:1px solid #e4e9ef;font-size:13px!important;color:#718096}',
    'html.hh-catalog-compact .dashboard-markdown [data-hh-special] .hh-special-title{display:block;margin:0 0 6px;font-size:13px;font-weight:600;color:#44536a}',
    'html.hh-catalog-compact .dashboard-markdown [data-hh-special] a{margin-right:14px;color:#1677c8!important}',
    'html.hh-catalog-compact .dashboard-markdown [data-hh-manage-link]{display:none!important}',
    /* 顶部菜单：资源管理分组（弹层挂 body、fixed 定位，避免菜单容器的命中测试异常） */
    'header .ant-menu li.hh-menu-off{display:none!important}',
    '.hh-res-item{position:relative}',
    '.hh-res-title{cursor:pointer;outline-offset:2px}',
    '.hh-res-title:focus-visible{outline:2px solid #1677c8}',
    '.hh-res-title .hh-caret{display:inline-block;margin-left:4px;font-size:10px;color:#8a97a5;transition:transform .12s}',
    '.hh-res-item[data-open="1"] .hh-caret{transform:rotate(180deg)}',
    '.hh-res-item.hh-res-active > .hh-res-title{color:#1677c8;font-weight:600}',
    '.hh-res-popup{display:none;position:fixed;z-index:1300;min-width:150px;padding:4px 0;background:#fff;border:1px solid #e1e8f0;border-radius:6px;box-shadow:0 6px 20px rgba(16,42,67,.14)}',
    '.hh-res-popup.hh-open{display:block}',
    '.hh-res-popup a{display:block;padding:0 16px;line-height:34px;font-size:13px;color:#3b4a5a;text-decoration:none;white-space:nowrap}',
    '.hh-res-popup a:hover{background:#eaf3fb;color:#1677c8}',
    '.hh-res-popup a:focus-visible{outline:2px solid #1677c8;outline-offset:-2px}',
    /* 管理列表：筛选允许两行；图标按钮可见焦点 */
    'html.hh-admin-page [data-test="card-filters"],html.hh-admin-page .filterBar{flex-wrap:wrap;row-gap:8px}',
    'html.hh-admin-page .ant-btn:focus-visible>span,html.hh-admin-page .ant-btn:focus-visible{outline:2px solid #1677c8!important}',
    '[data-hh-icon-button]{min-width:30px!important;min-height:30px!important;display:inline-flex!important;align-items:center!important;justify-content:center!important}',
    '[data-hh-icon-button]:focus-visible{outline:2px solid #1677c8!important;outline-offset:2px!important}',
    'header .ant-menu .ant-menu-submenu-title:focus-visible{outline:2px solid #1677c8;outline-offset:-2px}',
    'html.hh-directory [data-test="dashboard-filters-panel"]{display:none!important}',
    'html.hh-directory [data-test="dashboard-content-wrapper"]{margin-left:0!important;width:100%!important}',
    'html.hh-directory .dashboard-markdown .dashboard-component{padding:24px 32px!important;background:#fff;border:1px solid #e1e8f0;border-radius:12px;overflow:auto!important}',
    'html.hh-directory .dashboard-markdown h2{margin:0 0 10px!important;font-size:26px;color:#153f66}',
    'html.hh-directory .dashboard-markdown p{font-size:14px;line-height:1.8;color:#62768a;margin:0 0 18px}',
    'html.hh-directory .dashboard-markdown ul{list-style:none;padding:0!important;margin:18px 0!important;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}',
    'html.hh-directory .dashboard-markdown li{position:relative;margin:0!important;padding:18px 44px 18px 20px;border:1px solid #dce6f0;border-radius:10px;background:#f8fbfe;color:#60758a;line-height:1.9;font-size:14px;min-height:96px;transition:background .15s,border-color .15s}',
    'html.hh-directory .dashboard-markdown li:hover{background:#edf5ff;border-color:#83afd6}',
    'html.hh-directory .dashboard-markdown li a{display:block;font-size:18px;line-height:1.5;font-weight:600;color:#124e82;margin-bottom:8px}',
    'html.hh-directory .dashboard-markdown li a:after{content:"";position:absolute;inset:0;border-radius:10px}',
    'html.hh-directory .dashboard-markdown li:after{content:"›";position:absolute;right:18px;top:18px;font-size:28px;color:#7399bc;pointer-events:none}',
    'html.hh-directory .dashboard-markdown li p{margin:0;font-size:14px}',
    'html.hh-report-page .dashboard-markdown .dashboard-component{padding:6px 12px!important;border-left:3px solid #246598;background:#f0f6fc;border-radius:6px;font-size:13px;line-height:24px;white-space:nowrap;overflow:auto!important}',
    'html.hh-report-page .dashboard-markdown p{display:inline;margin:0!important}',
    'html.hh-report-page .dashboard-markdown p+p:before{content:" · ";color:#8ba0b3}',
    'html.hh-report-page .dashboard-chart-id-340 table td:first-child{background-image:none!important;background-color:transparent!important}',
    'html.hh-report-page .dashboard-chart-id-340 table td:first-child .cell-bar{display:none!important}',
    'html.hh-report-page [data-test="slice-header"]{font-size:17px;color:#153f66;border-bottom:1px solid #edf1f6;padding-bottom:8px;margin-bottom:8px}',
    'html.hh-report-page .superset-chart-table table{font-size:14px!important}',
    'html.hh-report-page .superset-chart-table th{background:#edf4fb!important;color:#224967;font-weight:600;padding:9px 10px!important;white-space:nowrap}',
    'html.hh-report-page .superset-chart-table td{padding:8px 10px!important;line-height:1.5!important}',
    'html.hh-report-page .superset-chart-table .dt-controls{margin-bottom:10px}',
    'html.hh-report-page [data-test="filter-bar"]{border-bottom:1px solid #dce6f0}',
    /* 查询页单结果且图表标题与页面标题相同：隐藏重复图表标题（保留更多菜单与 explore 入口） */
    'html.hh-report-page [data-hh-dup-slice-title]{display:none!important}',
    /* 真实成功空集：原生空态替换为统一提示，其他状态不进入此分支 */
    'html.hh-report-page [data-hh-native-empty]{display:none!important}',
    '.hh-empty-success{display:flex;align-items:center;justify-content:center;min-height:180px;padding:40px 16px;box-sizing:border-box;font-size:13px;line-height:22px;color:#718096;text-align:center}',
    /* 兼容 f2 旧提示块清理 */
    '#hospital-directory-hint{margin:16px 24px;padding:16px 20px;background:#edf5ff;border:1px solid #c8ddf0;border-radius:10px;font-size:15px}',
    '#hospital-directory-hint a{font-weight:600;margin-right:16px}',
    /* 查询页显式报表工具条（20261105f10）：企业后台紧凑条，位于图表容器顶部 */
    '.hh-query-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;height:36px;box-sizing:border-box;padding:0 12px;background:#f8fafc;border-bottom:1px solid #e4e9ef;font-size:13px;color:#44536a;flex:none}',
    '.hh-query-toolbar .hh-qt-left{display:flex;align-items:center;min-width:0;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}',
    '.hh-query-toolbar .hh-qt-left strong{color:#153f66;font-weight:600;margin:0 2px}',
    '.hh-query-toolbar .hh-qt-right{display:flex;align-items:center;gap:8px;flex:none}',
    '.hh-query-toolbar button{height:26px;padding:0 10px;border:1px solid #c9d6e2;border-radius:4px;background:#fff;color:#2f4257;font-size:12px;line-height:24px;cursor:pointer;white-space:nowrap;font-family:inherit}',
    '.hh-query-toolbar button:hover:not(:disabled){border-color:#9ec7e8;color:#0f5da4;background:#f2f9ff}',
    '.hh-query-toolbar button:disabled{opacity:.45;cursor:not-allowed;background:#fafcfe}',
    '.hh-query-toolbar button:focus-visible{outline:2px solid #1677c8;outline-offset:1px}',
    '.hh-query-toolbar .hh-btn-xlsx{background:#1677c8;border-color:#1677c8;color:#fff}',
    '.hh-query-toolbar .hh-btn-xlsx:hover:not(:disabled){background:#1268b3;border-color:#1268b3;color:#fff}',
    /* 5 万/10 万行上限截断强警告横幅（E3 数据完整性隐患） */
    '.hh-truncation-banner{display:flex;align-items:center;height:34px;box-sizing:border-box;padding:0 12px;background:#fff7e6;border-bottom:1px solid #ffd591;color:#d46b08;font-size:13px;font-weight:600;flex:none}',
    /* 紧凑行高模式（hhTableDensity=compact）：一屏看更多行 */
    'html.hh-density-compact .superset-chart-table td{height:32px!important;max-height:32px!important;padding:4px 8px!important;line-height:24px!important;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:320px}',
    'html.hh-density-compact .superset-chart-table td > div{line-height:24px!important;max-height:24px!important;overflow:hidden}',
    'html.hh-density-compact .superset-chart-table td *{line-height:24px!important}',
    '@media(max-width:1200px){html.hh-directory .dashboard-markdown ul{grid-template-columns:repeat(2,minmax(0,1fr))}}',
    '@media(max-width:760px){html.hh-directory .dashboard-markdown ul{grid-template-columns:1fr}html.hh-directory .dashboard-markdown .dashboard-component{padding:18px!important}}'
  ].join('\n');
  document.head.appendChild(st);

  /* 别名看板 → 数字 ID（20261104f9）：月报别名=32，病案明细别名=2 */
  var DASHBOARD_ALIASES = {
    '/superset/dashboard/month-work-report-new/': 32,
    '/superset/dashboard/mr-discharge-death-detail/': 2
  };
  function pageId() {
    var m = location.pathname.match(/^\/superset\/dashboard\/(\d+)\/?$/);
    if (m) return Number(m[1]);
    var p = location.pathname.replace(/\/?$/, '/');
    return Object.prototype.hasOwnProperty.call(DASHBOARD_ALIASES, p) ? DASHBOARD_ALIASES[p] : 0;
  }
  function pageState() {
    var id = pageId();
    var editing = /(?:\?|&)edit=true/.test(location.search) || !!(window.hospitalHomeUI && window.hospitalHomeUI.isEditing && window.hospitalHomeUI.isEditing());
    document.documentElement.classList.toggle('hh-directory', !editing && categories.indexOf(id) >= 0);
    document.documentElement.classList.toggle('hh-report-page', !editing && (id === 2 || id === 32 || (id >= 35 && id <= 70)));
    var p = location.pathname;
    var adminPage = /^\/(dashboard|chart|tablemodelview)\/list\//.test(p) || /^\/sqllab(\/|$)/.test(p) || /^\/savedqueryview\/list\//.test(p);
    document.documentElement.classList.toggle('hh-admin-page', adminPage);
  }

  function isCatalogPage() { return document.documentElement.classList.contains('hh-catalog-compact'); }
  function isQueryPage() { return document.documentElement.classList.contains('hh-report-page'); }

  /* ---------- 顶部菜单重组与状态 ---------- */
  var SQL_ITEMS = [['SQL 查询', '/sqllab/'], ['已保存查询', '/savedqueryview/list/'], ['历史查询', '/sqllab/history/']];

  function navMenu() {
    var menus = document.querySelectorAll('header .ant-menu');
    for (var i = 0; i < menus.length; i++) {
      if ((menus[i].className || '').indexOf('main-nav') >= 0) return menus[i];
    }
    return null;
  }

  function menuReorg() {
    var menu = navMenu();
    if (!menu) return;
    var items = menu.querySelectorAll(':scope > li');
    var map = {};
    Array.prototype.forEach.call(items, function (li) {
      var a = li.querySelector('.ant-menu-title-content a');
      var title = li.querySelector('.ant-menu-submenu-title');
      var text = a ? a.textContent.trim() : (title ? title.textContent.trim() : '');
      if (text === '首页') map.home = { li: li, a: a };
      else if (text === '报表目录') map.catalog = { li: li, a: a };
      else if (text === '图表') map.chart = { li: li, a: a };
      else if (text === '数据集') map.dataset = { li: li, a: a };
      else if (text === 'SQL' && li.className.indexOf('ant-menu-submenu') >= 0) map.sql = { li: li };
    });
    var hasRes = !!(map.chart || map.dataset || map.sql);
    var res = document.getElementById('hh-res-menu');
    /* React 重渲染导航后可能残留旧节点：仅保留一个资源管理节点 */
    Array.prototype.forEach.call(document.querySelectorAll('.hh-res-item'), function (n) {
      if (n !== res) n.remove();
    });
    if (!hasRes) {
      if (res) res.remove();
      var popupOld = document.getElementById('hh-res-popup');
      if (popupOld) popupOld.remove();
      Array.prototype.forEach.call(menu.querySelectorAll('li.hh-menu-off'), function (li) { li.classList.remove('hh-menu-off'); });
    } else {
      var chartHref = map.chart && map.chart.a && map.chart.a.getAttribute('href');
      var dataHref = map.dataset && map.dataset.a && map.dataset.a.getAttribute('href');
      var entries = [];
      if (canOpenDirectory || isAdminUser()) entries.push(['看板管理', '/dashboard/list/']);
      if (chartHref) entries.push(['图表', chartHref]);
      if (dataHref) entries.push(['数据集', dataHref]);
      if (map.sql) Array.prototype.push.apply(entries, SQL_ITEMS);
      if (map.chart) map.chart.li.classList.add('hh-menu-off');
      if (map.dataset) map.dataset.li.classList.add('hh-menu-off');
      if (map.sql) map.sql.li.classList.add('hh-menu-off');
      if (!entries.length) { if (res) res.remove(); return; }
      if (!res) {
        res = document.createElement('li');
        res.id = 'hh-res-menu';
        res.className = 'ant-menu-item ant-menu-item-only-child hh-res-item';
        res.setAttribute('data-open', '0');
        var title = document.createElement('span');
        title.className = 'ant-menu-title-content hh-res-title';
        title.tabIndex = 0;
        title.setAttribute('role', 'button');
        title.setAttribute('aria-haspopup', 'true');
        title.setAttribute('aria-expanded', 'false');
        title.appendChild(document.createTextNode('资源管理'));
        var caret = document.createElement('span');
        caret.className = 'hh-caret';
        caret.setAttribute('aria-hidden', 'true');
        caret.textContent = '▾';
        title.appendChild(caret);
        res.appendChild(title);
        var popup = document.createElement('div');
        popup.className = 'hh-res-popup';
        popup.id = 'hh-res-popup';
        popup.setAttribute('role', 'menu');
        document.body.appendChild(popup);
        var anchor = map.catalog && map.catalog.li ? map.catalog.li.nextSibling : null;
        menu.insertBefore(res, anchor);
        title.addEventListener('click', function (e) {
          if (e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
          toggleRes(true);
        });
        title.addEventListener('keydown', function (e) {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault(); e.stopPropagation(); toggleRes(true);
          } else if (e.key === 'Escape') {
            e.preventDefault(); e.stopPropagation(); toggleRes(false);
          } else if (e.key === 'ArrowDown') {
            e.preventDefault(); e.stopPropagation(); toggleRes(true);
            var f = popup.querySelector('a'); if (f) f.focus();
          }
        });
        /* 悬停：li 与 body 级弹层共享延迟关闭，鼠标在两者间移动不关闭 */
        res.addEventListener('mouseenter', function () { hoverCancel(); toggleRes(true); });
        popup.addEventListener('mouseenter', hoverCancel);
        res.addEventListener('mouseleave', hoverClose);
        popup.addEventListener('mouseleave', hoverClose);
        popup.addEventListener('keydown', function (e) {
          if (e.key === 'Escape') { toggleRes(false); title.focus(); }
        });
        document.addEventListener('click', function (e) {
          if (!res.contains(e.target) && !popup.contains(e.target)) toggleRes(false);
        }, true);
        document.addEventListener('keydown', function (e) {
          if (e.key === 'Escape' && popup.classList.contains('hh-open')) {
            e.preventDefault(); e.stopPropagation(); toggleRes(false); title.focus();
          }
        }, true);
        window.addEventListener('scroll', function () { toggleRes(false); }, true);
      }
      var popup = document.getElementById('hh-res-popup');
      var want = entries.map(function (en) { return en[0] + '|' + en[1]; }).join(';');
      var have = Array.prototype.map.call(popup.children, function (a) { return a.textContent + '|' + a.getAttribute('href'); }).join(';');
      if (want !== have) {
        while (popup.firstChild) popup.removeChild(popup.firstChild);
        entries.forEach(function (en) {
          var a = document.createElement('a');
          a.href = en[1];
          a.setAttribute('role', 'menuitem');
          a.textContent = en[0];
          popup.appendChild(a);
        });
      }
    }
    /* 当前页 active 与 aria-current */
    var p = location.pathname;
    var onHome = p === '/' || p.indexOf('/superset/welcome') === 0;
    var onDashboard = /^\/superset\/dashboard\//.test(p);
    var onResource = /^\/(dashboard|chart|tablemodelview)\/list\//.test(p) || /^\/sqllab(\/|$)/.test(p) || /^\/savedqueryview\/list\//.test(p);
    setAria(map.home && map.home.a, onHome);
    setAria(map.catalog && map.catalog.a, onDashboard);
    if (res) {
      res.classList.toggle('hh-res-active', onResource);
      var t = res.querySelector('.hh-res-title');
      if (t) { if (onResource) t.setAttribute('aria-current', 'page'); else t.removeAttribute('aria-current'); }
    }
  }

  /* 悬停关闭的共享定时器（li 与 body 级弹层之间移动鼠标不触发关闭） */
  var resHoverTimer = 0;
  function hoverClose() {
    if (resHoverTimer) clearTimeout(resHoverTimer);
    resHoverTimer = setTimeout(function () { resHoverTimer = 0; toggleRes(false); }, 260);
  }
  function hoverCancel() {
    if (resHoverTimer) { clearTimeout(resHoverTimer); resHoverTimer = 0; }
  }

  function toggleRes(open) {
    var res = document.getElementById('hh-res-menu');
    var popup = document.getElementById('hh-res-popup');
    if (!res || !popup) return;
    res.setAttribute('data-open', open ? '1' : '0');
    var title = res.querySelector('.hh-res-title');
    if (title) title.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) {
      var rect = res.getBoundingClientRect();
      popup.style.left = Math.round(rect.left) + 'px';
      popup.style.top = Math.round(rect.bottom + 2) + 'px';
      if (!popup.classList.contains('hh-open')) popup.classList.add('hh-open');
    } else {
      popup.classList.remove('hh-open');
      popup.style.left = '';
      popup.style.top = '';
    }
  }

  function setAria(a, current) {
    if (!a) return;
    if (current) a.setAttribute('aria-current', 'page');
    else if (a.getAttribute('aria-current') === 'page') a.removeAttribute('aria-current');
  }

  function isAdminUser() {
    try {
      var app = document.getElementById('app');
      var raw = app && app.getAttribute('data-bootstrap');
      if (!raw) return false;
      var roles = (JSON.parse(raw).user || {}).roles;
      if (!roles) return false;
      return Array.isArray(roles) ? roles.indexOf('Admin') >= 0 : Object.prototype.hasOwnProperty.call(roles, 'Admin');
    } catch (e) { return false; }
  }

  /* 右侧图标触发器补 title/aria；设置菜单服务端词条按 href 精确改显示 */
  function menuFixups() {
    var icons = [['anticon-plus', '新建'], ['anticon-format-painter', '主题'], ['anticon-sun', '主题'], ['anticon-moon', '主题'], ['anticon-caret-down', '语言']];
    Array.prototype.forEach.call(document.querySelectorAll('header .ant-menu-submenu-title'), function (t) {
      for (var i = 0; i < icons.length; i++) {
        if (t.querySelector('.' + icons[i][0])) {
          if (!t.hasAttribute('title')) t.setAttribute('title', icons[i][1]);
          if (!t.hasAttribute('aria-label')) t.setAttribute('aria-label', icons[i][1]);
        }
      }
    });
    var fixes = [['/user_info/', '信息', '账号信息'], ['/list_groups/', 'List Groups', '用户组'], ['/databaseview/list/', 'Database Connections', '数据库连接']];
    Array.prototype.forEach.call(document.querySelectorAll('header a, [role=menu] a, .ant-menu-submenu-popup a'), function (a) {
      var href = a.getAttribute('href') || '';
      var text = a.textContent.trim();
      for (var i = 0; i < fixes.length; i++) {
        if (href === fixes[i][0] && text === fixes[i][1]) { a.textContent = fixes[i][2]; break; }
      }
    });
  }

  /* ---------- 面包屑与页面头部 ---------- */
  function nativeTitle() {
    var sizer = document.querySelector('.dashboard-header-container .input-sizer');
    if (sizer && sizer.textContent.trim()) return sizer.textContent.trim();
    var input = document.querySelector('[data-test="editable-title-input"]');
    if (input && input.value) return input.value;
    return document.title;
  }

  function markdownBackLink() {
    var links = document.querySelectorAll('.dashboard-markdown a');
    for (var i = 0; i < links.length; i++) {
      var t = links[i].textContent.trim();
      if (t.indexOf('←') === 0 || t.indexOf('返回') === 0) return links[i];
    }
    return null;
  }

  /* 查看态/编辑态页头切换：编辑态移除面包屑并恢复原生标题，不遗留 aria-hidden。 */
  function pageHeaderMode() {
    var view = isCatalogPage() || isQueryPage();
    var input = document.querySelector('.dashboard-header-container [data-test="editable-title-input"]');
    var wrap = input && input.parentElement;
    if (wrap && wrap.classList.contains('title-panel') === false) {
      if (view) {
        wrap.setAttribute('data-hh-native-title', '1');
        wrap.setAttribute('aria-hidden', 'true');
      } else {
        wrap.removeAttribute('data-hh-native-title');
        wrap.removeAttribute('aria-hidden');
      }
    }
    if (!view) {
      var oldCrumb = document.getElementById('hh-crumb');
      if (oldCrumb) oldCrumb.remove();
      var oldManage = document.getElementById('hh-head-manage');
      if (oldManage) oldManage.remove();
    }
  }

  function crumb() {
    var header = document.querySelector('.dashboard-header-container .header-with-actions, .dashboard-header-container');
    if (!header) return;
    if (!isCatalogPage() && !isQueryPage()) return;
    var box = document.getElementById('hh-crumb');
    var back = markdownBackLink();
    var key = location.pathname + '|' + nativeTitle() + '|' + (back ? back.getAttribute('href') : '');
    if (box && box.getAttribute('data-hh-key') === key) { hideBackLinks(); headerExtras(); return; }
    if (!box) {
      box = document.createElement('div');
      box.id = 'hh-crumb';
      box.className = 'hh-crumb';
      var panel = header.querySelector('.title-panel');
      (panel || header).insertBefore(box, (panel || header).firstChild);
    }
    while (box.firstChild) box.removeChild(box.firstChild);
    var id = pageId();
    function seg(text, href) {
      var el;
      if (href) { el = document.createElement('a'); el.href = href; }
      else { el = document.createElement('span'); el.className = 'hh-crumb-cur'; el.setAttribute('title', text); }
      el.textContent = text;
      return el;
    }
    function sep() { var s = document.createElement('span'); s.className = 'hh-crumb-sep'; s.textContent = '/'; return s; }
    var title = nativeTitle();
    if (id === 34) {
      box.appendChild(seg('报表目录', null));
    } else if (categories.indexOf(id) >= 0) {
      box.appendChild(seg('报表目录', '/superset/dashboard/34/'));
      box.appendChild(sep());
      box.appendChild(seg(CATEGORY_NAMES[id] || title, null));
    } else if (id === 2) {
      /* 病案专项（20261104f9）：固定中间层级，不再依赖 Markdown 返回链接 */
      box.appendChild(seg('报表目录', '/superset/dashboard/34/'));
      box.appendChild(sep());
      box.appendChild(seg('病案专项', null));
      box.appendChild(sep());
      box.appendChild(seg(title, null));
    } else if (id >= 61 && id <= 70) {
      /* 抗菌办查询页（20261104f9）：固定层级（61–70 页 Markdown 带通用“返回工作台”链接，
         统一隐藏，面包屑以“报表目录”为唯一返回入口，中间层固定为“抗菌药物监测”） */
      box.appendChild(seg('报表目录', '/superset/dashboard/34/'));
      box.appendChild(sep());
      box.appendChild(seg('抗菌药物监测', null));
      box.appendChild(sep());
      box.appendChild(seg(title, null));
    } else {
      box.appendChild(seg('报表目录', '/superset/dashboard/34/'));
      box.appendChild(sep());
      if (back) {
        var label = back.textContent.trim().replace(/^←\s*/, '').replace(/^返回\s*/, '').replace(/^统计报表·/, '');
        if (label) { box.appendChild(seg(label, back.getAttribute('href'))); box.appendChild(sep()); }
      }
      box.appendChild(seg(title, null));
    }
    box.setAttribute('data-hh-key', key);
    var sizer = header.querySelector('.input-sizer');
    if (sizer) sizer.setAttribute('aria-hidden', 'true');
    hideBackLinks();
    headerExtras();
  }

  function hideBackLinks() {
    var md = document.querySelector('.dashboard-markdown');
    if (!md) return;
    Array.prototype.forEach.call(md.querySelectorAll('a'), function (a) {
      var t = a.textContent.trim();
      if (t.indexOf('←') === 0 || t.indexOf('返回') === 0) {
        if (!a.hasAttribute('data-hh-backlink')) a.setAttribute('data-hh-backlink', '1');
        var p = a.parentElement;
        if (p && p.tagName === 'P') {
          var rest = '';
          Array.prototype.forEach.call(p.childNodes, function (n) {
            if (n !== a) rest += n.textContent ? n.textContent.trim() : '';
          });
          if (!rest && !p.querySelector('img')) p.setAttribute('data-hh-backlink-empty', '1');
        }
      }
    });
  }

  /* 作者/修改时间容器：按内容锚定标记后隐藏（容器类名随 emotion 版本变化） */
  function metaHide() {
    if (!isCatalogPage() && !isQueryPage()) return;
    Array.prototype.forEach.call(document.querySelectorAll('.dashboard-header-container [class*="metadata-text"], .dashboard-header-container [class*="metadata-icon"]'), function (e) {
      var item = e.parentElement;
      if (item && !item.hasAttribute('data-hh-metadata')) item.setAttribute('data-hh-metadata', '1');
      var bar = item && item.parentElement;
      /* 只隐藏纯元信息容器；包含星标/刷新/草稿的共享父容器必须保留 */
      if (bar && bar.querySelector('[class*="metadata-icon"]') &&
          !bar.querySelector('.fave-unfave-icon, [data-test="refresh-button"], .ant-tag, .title-panel, .right-button-panel') &&
          !bar.hasAttribute('data-hh-metadata')) {
        bar.setAttribute('data-hh-metadata', '1');
      }
    });
  }

  /* 34：看板管理移至页面头部次要按钮（仅有权者）；Markdown 原链接隐藏 */
  function headerExtras() {
    var btn = document.getElementById('hh-head-manage');
    var on34 = pageId() === 34;
    var allowed = canOpenDirectory || isAdminUser();
    if (!on34 || !allowed) { if (btn) btn.remove(); return; }
    if (btn) return;
    var panel = document.querySelector('.dashboard-header-container .right-button-panel, .dashboard-header-container .button-container');
    if (!panel) return;
    btn = document.createElement('a');
    btn.id = 'hh-head-manage';
    btn.className = 'hh-head-link';
    btn.href = '/dashboard/list/';
    btn.title = '看板管理';
    btn.textContent = '看板管理';
    panel.insertBefore(btn, panel.firstChild);
  }

  /* ---------- 目录页内容增强 ---------- */
  function catalogEnhance() {
    if (!isCatalogPage()) return;
    var md = document.querySelector('.dashboard-markdown');
    if (!md) return;
    if (pageId() === 34) {
      /* 既有专项 → 底部“其他专题”；看板管理原链接隐藏（入口已移至页面头部） */
      Array.prototype.forEach.call(md.querySelectorAll('p'), function (p) {
        var t = p.textContent.trim();
        var links = p.querySelectorAll('a');
        if (links.length >= 2 && t.indexOf('既有专项') === 0 && !p.querySelector('[data-hh-special]')) {
          var head = document.createTextNode(t.split('：')[0]);
          p.setAttribute('data-hh-special', '1');
          while (p.firstChild && p.firstChild.nodeType === 3) p.removeChild(p.firstChild);
          var title = document.createElement('span');
          title.className = 'hh-special-title';
          title.textContent = '其他专题';
          p.insertBefore(title, p.firstChild);
        }
        if (links.length === 1 && links[0].textContent.trim() === '看板管理' && t === '看板管理') {
          p.setAttribute('data-hh-manage-link', '1');
        }
      });
    }
    /* 分类目录行：真实筛选摘要替换通用空话 */
    Array.prototype.forEach.call(md.querySelectorAll('li'), function (li) {
      var links = li.querySelectorAll('a');
      if (links.length !== 1) return;
      var m = (links[0].getAttribute('href') || '').match(/\/dashboard\/(\d+)\//);
      if (!m) return;
      var summary = FILTER_SUMMARY[Number(m[1])];
      if (!summary) return;
      var desc = li.querySelector('[data-hh-catalog-description]');
      if (!desc) {
        Array.prototype.forEach.call(li.children, function (c) {
          if (!c.contains(links[0]) && !c.querySelector('a') && c.textContent.trim() === GENERIC_DESC) desc = c;
        });
      }
      if (desc && desc.textContent.trim() === GENERIC_DESC) {
        desc.textContent = '查询条件：' + summary;
        desc.setAttribute('data-hh-summary', '1');
      } else if (desc && desc.hasAttribute('data-hh-summary') && desc.textContent.indexOf('查询条件：') !== 0) {
        desc.textContent = '查询条件：' + summary;
      }
    });
  }

  /* ---------- 查询页文案 ---------- */
  function visitIdLabels() {
    if (!/\/superset\/dashboard\//.test(location.pathname)) return;
    var fixes = [['visit_id 下界', '就诊次数下限'], ['visit_id 上界', '就诊次数上限']];
    Array.prototype.forEach.call(document.querySelectorAll('label, .ant-form-item-label, [class*=filter-title]'), function (el) {
      var t = el.textContent.trim();
      for (var i = 0; i < fixes.length; i++) {
        if (t === fixes[i][0]) { el.textContent = fixes[i][1]; break; }
      }
    });
  }

  /* 成功空集提示：只有本页发生有效提交、原生图表成功且数据为 0 行时才替换。
     加载/失败/必选缺失/权限错误以及未提交的初始空态均保留原生呈现。 */
  var chartGrid = null, chartStore = null;
  function dashboardCharts() {
    var grid = document.querySelector('[data-test="grid-content"]');
    if (grid !== chartGrid || (grid && !chartStore)) {
      chartGrid = grid; chartStore = null;
      var fiberKey = grid && Object.keys(grid).filter(function (k) { return k.indexOf('__reactFiber') === 0; })[0];
      var f = grid && grid[fiberKey];
      while (f) {
        var p = f.memoizedProps, s = p && (p.store || (p.value && p.value.store));
        if (s && s.getState) { chartStore = s; break; }
        f = f.return;
      }
    }
    var state = chartStore && chartStore.getState();
    return (state && state.charts) || {};
  }
  function emptyStateText() {
    if (!isQueryPage()) return;
    Array.prototype.forEach.call(document.querySelectorAll('.superset-chart-table, #hospital-monthly-report'), function (root) {
      Array.prototype.forEach.call(root.querySelectorAll('.dt-empty, .ant-empty-description, [data-test=empty-description]'), function (el) {
        if (el.textContent.trim() === '没有找到任何记录') el.textContent = '当前条件无数据，请调整查询条件后重试';
      });
    });
    var charts = dashboardCharts();
    Array.prototype.forEach.call(document.querySelectorAll('.dashboard-component-chart-holder'), function (holder) {
      var m = (holder.className || '').match(/dashboard-chart-id-(\d+)/);
      if (!m) return;
      var id = m[1], c = charts[id], response = c && c.queriesResponse && c.queriesResponse[0];
      var success = !!(querySubmitSeen[location.pathname] && c &&
        (c.chartStatus === 'success' || c.chartStatus === 'rendered') && response &&
        c.chartUpdateEndTime && c.chartUpdateEndTime >= querySubmitSeen[location.pathname] &&
        Array.isArray(response.data) && response.data.length === 0 && !response.error);
      if (id === '321' && window.hospitalVisitGuard && window.hospitalVisitGuard.currentCheck) {
        try { if (!window.hospitalVisitGuard.currentCheck().ok) success = false; } catch (e) { success = false; }
      }
      var nativeEmpty = holder.querySelectorAll('.ant-empty, .ant-empty-description');
      var line = holder.querySelector('.hh-empty-success');
      if (success && nativeEmpty.length) {
        var container = holder.querySelector('.slice_container') || holder;
        var nativeRoot = holder.querySelector('.ant-empty');
        /* 原生空态的标题/图标/说明可能分散在不同节点，统一隐藏其直接容器 */
        while (nativeRoot && nativeRoot.parentElement && nativeRoot.parentElement !== container) nativeRoot = nativeRoot.parentElement;
        if (nativeRoot) nativeRoot.setAttribute('data-hh-native-empty', '1');
        Array.prototype.forEach.call(nativeEmpty, function (e) {
          e.setAttribute('data-hh-native-empty', '1');
        });
        if (!line) {
          line = document.createElement('div');
          line.className = 'hh-empty-success';
          line.textContent = '当前条件无数据，请调整查询条件后重试';
          container.appendChild(line);
        }
      } else {
        if (line) line.remove();
        Array.prototype.forEach.call(holder.querySelectorAll('[data-hh-native-empty]'), function (e) {
          e.removeAttribute('data-hh-native-empty');
        });
      }
    });
  }

  /* ---------- 查询页显式报表工具条（20261105f10：行数/耗时摘要 + 显式导出 + 行高切换 + 截断警告） ---------- */
  var exportNote = { text: '', until: 0 };
  var exporting = {}; /* chartId -> {fmt:'xlsx'|'csv'}，导出期间保持按钮禁用与忙碌文案 */

  function csrfToken() {
    var m = document.cookie.match(/(?:^|;\s*)(?:csrf_token|csrftoken)=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }
  /* 服务端分页图表（server_pagination=true）响应 rowcount/sql_rowcount 均为当前页行数，
     匹配总数只存在于前端分页器（末页码 × 每页行数）；非分页图表 sql_rowcount/rowcount 即总数。 */
  function pagedTotal(root, qfd, resp) {
    var pg = root ? root.querySelector('.pagination') : null;
    if (!pg) return null;
    var items = pg.querySelectorAll('li');
    var last = 0;
    for (var i = items.length - 1; i >= 0; i--) {
      var t = (items[i].textContent || '').trim();
      if (/^\d+$/.test(t)) { last = parseInt(t, 10); break; }
    }
    var per = (qfd && typeof qfd.server_page_length === 'number' && qfd.server_page_length) ||
      (resp && Array.isArray(resp.data) ? resp.data.length : 0);
    return (last && per) ? last * per : null;
  }
  function toolbarInfo(c, root) {
    var status = c ? c.chartStatus : null;
    var resp = c && c.queriesResponse && c.queriesResponse[0];
    var qfd = c && c.latestQueryFormData;
    var rowLimit = (qfd && typeof qfd.row_limit === 'number') ? qfd.row_limit : 0;
    var rows = 0;
    var serverPag = !!(qfd && qfd.server_pagination);
    if (resp && !resp.error) {
      if (serverPag) {
        rows = pagedTotal(root, qfd, resp) ||
          (typeof resp.sql_rowcount === 'number' ? resp.sql_rowcount
            : (typeof resp.rowcount === 'number' ? resp.rowcount
              : (Array.isArray(resp.data) ? resp.data.length : 0)));
      } else {
        /* 非分页图表 sql_rowcount/rowcount 即总数（受 row_limit 上限约束），缺省退 data.length */
        rows = typeof resp.sql_rowcount === 'number' ? resp.sql_rowcount
          : (typeof resp.rowcount === 'number' ? resp.rowcount
            : (Array.isArray(resp.data) ? resp.data.length : 0));
      }
    }
    var phase = 'idle';
    if (status === 'loading') phase = 'loading';
    else if ((status === 'rendered' || status === 'success') && resp && !resp.error) phase = 'ok';
    else if (status === 'failed' || (resp && resp.error)) phase = 'failed';
    var elapsed = null;
    if (c && c.chartUpdateStartTime) {
      elapsed = Math.max(0, (c.chartUpdateEndTime || Date.now()) - c.chartUpdateStartTime) / 1000;
    }
    return { phase: phase, rows: rows, rowLimit: rowLimit, elapsed: elapsed, est: serverPag };
  }
  function toolbarSummary(info) {
    if (exportNote.text && Date.now() < exportNote.until) return exportNote.text;
    if (info.phase === 'loading') {
      return '⏳ 正在查询数据（已用时 ' + Math.floor(info.elapsed || 0) + ' 秒，大表可能需 15~45 秒，请稍候）…';
    }
    if (info.phase === 'failed') return '查询失败，请调整查询条件后重试';
    if (info.phase === 'ok') {
      var t = '共返回 <strong>' + info.rows.toLocaleString() + '</strong> 行数据' + (info.est ? '（约）' : '');
      if (info.elapsed != null) t += ' · 耗时 ' + info.elapsed.toFixed(1) + ' 秒';
      return t;
    }
    return '等待查询…';
  }
  function pad2(n) { return ('0' + n).slice(-2); }
  function ymd(d) { return d.getFullYear() + pad2(d.getMonth() + 1) + pad2(d.getDate()); }
  /* 文件名日期段：优先当前日历草稿（hospitalDateUI 草稿值，排他上界折回含端末日），退回上次查询 time_range，再退回当日 */
  function exportDatePart(c) {
    var ui = window.hospitalDateUI;
    if (ui && typeof ui.draftFor === 'function') {
      var panels = document.querySelectorAll('.hdt-picker[data-filter-id]');
      for (var i = 0; i < panels.length; i++) {
        var v = ui.draftFor(panels[i].getAttribute('data-filter-id'));
        var pr = (v && typeof ui.parseRange === 'function') ? ui.parseRange(v) : null;
        if (pr && pr.a && pr.b) {
          var end = new Date(pr.b.getFullYear(), pr.b.getMonth(), pr.b.getDate() - 1);
          if (end < pr.a) end = pr.a;
          return ymd(pr.a) === ymd(end) ? ymd(pr.a) : ymd(pr.a) + '-' + ymd(end);
        }
      }
    }
    var m = String((c && c.latestQueryFormData && c.latestQueryFormData.time_range) || '').match(/^(\d{4}-\d{2}-\d{2})\s*:\s*(\d{4}-\d{2}-\d{2})/);
    if (m) {
      var a = m[1].split('-'), b = m[2].split('-');
      var A = new Date(+a[0], +a[1] - 1, +a[2]);
      var B = new Date(+b[0], +b[1] - 1, (+b[2]) - 1);
      if (B < A) B = A;
      return ymd(A) === ymd(B) ? ymd(A) : ymd(A) + '-' + ymd(B);
    }
    return ymd(new Date());
  }
  function downloadBlob(blob, filename) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 5000);
  }
  /* 偷听图表数据查询（QueryContext payload）并按图表缓存——导出时原样重放，仅改 result_format，
     保证导出条件与页面最近一次查询完全一致（含 native filter 展开后的 filters）。 */
  var lastQueryContext = {};
  function hookQueryFetch() {
    if (window.__hhFetchHooked) return;
    window.__hhFetchHooked = true;
    var orig = window.fetch ? window.fetch.bind(window) : null;
    if (!orig) return;
    window.fetch = function (input, init) {
      try {
        var url = typeof input === 'string' ? input : ((input && input.url) || '');
        if (init && String(init.method || '').toUpperCase() === 'POST' && url.indexOf('/api/v1/chart/data') >= 0 &&
            typeof init.body === 'string' && init.body.indexOf('"queries"') >= 0) {
          var parsed = JSON.parse(init.body);
          if (parsed && parsed.queries && parsed.form_data && parsed.form_data.slice_id &&
              !parsed.form_data.native_filter_id) {
            lastQueryContext[String(parsed.form_data.slice_id)] = init.body;
          }
        }
      } catch (e) {}
      return orig(input, init);
    };
  }
  /* 与 Superset 原生导出一致的 /api/v1/chart/data 请求：重放缓存的图表查询 QueryContext，
     result_format=xlsx/csv + result_type=full；分页图表恢复 row_limit 全量、去分页页号。 */
  function exportChart(id, fmt) {
    var raw = lastQueryContext[id];
    var c = dashboardCharts()[id];
    if (!raw) {
      exportNote.text = '❌ 未捕获到本图表的查询请求，请先点击“查询”出数后再导出';
      exportNote.until = Date.now() + 30000;
      queryToolbar();
      return;
    }
    var payload = JSON.parse(raw);
    payload.result_format = fmt;
    payload.result_type = 'full';
    payload.force = false;
    /* 偷听到的查询 payload 内嵌 form_data.result_format='json' 会让后端把 CSV 打包成 zip，
       导出时必须同步覆盖（实测：不覆盖则 35 页返回 zip(query_1.csv)，覆盖后为纯 CSV） */
    if (payload.form_data && typeof payload.form_data === 'object') {
      payload.form_data.result_format = fmt;
      payload.form_data.result_type = 'full';
    }
    try {
      var cfgLimit = (payload.form_data && payload.form_data.row_limit) || 0;
      /* 后端对多查询（如 time_compare 生成的对比查询）的 CSV/XLSX 会打包成 zip 下载，
         医院用户需要双击即开的单文件：只重放主数据查询（buildQuery 的第 1 项）。 */
      if (payload.queries && payload.queries.length > 1) payload.queries = payload.queries.slice(0, 1);
      payload.queries.forEach(function (q) {
        delete q.page;
        delete q.row_offset;
        if (cfgLimit) q.row_limit = cfgLimit; /* 服务端分页图表按图表上限全量导出 */
        if (Array.isArray(q.post_processing)) q.post_processing = [];
      });
    } catch (e) {}
    var fname = (nativeTitle() || '报表').replace(/[\\/:*?"<>|]/g, '-') + '_' + exportDatePart(c) + (fmt === 'xlsx' ? '.xlsx' : '.csv');
    exporting[id] = { fmt: fmt };
    queryToolbar();
    fetch('/api/v1/chart/data', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
      body: JSON.stringify(payload)
    }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return fmt === 'csv' ? r.text() : r.blob();
    }).then(function (data) {
      if (fmt === 'csv') {
        if (!data) throw new Error('服务器返回空文件');
        /* 医院旧版 Office 无 BOM 打开中文 CSV 乱码：未带 UTF-8 BOM 则前端前置 */
        if (data.charAt(0) !== '\uFEFF') data = '\uFEFF' + data;
        downloadBlob(new Blob([data], { type: 'text/csv;charset=utf-8' }), fname);
      } else {
        if (!data || !data.size) throw new Error('服务器返回空文件');
        downloadBlob(data, fname);
      }
      exportNote.text = '✅ 已导出 ' + fname;
      exportNote.until = Date.now() + 30000;
    }).catch(function (err) {
      exportNote.text = '❌ 导出失败：' + (err && err.message ? err.message : '未知错误，请重试');
      exportNote.until = Date.now() + 30000;
    }).then(function () {
      delete exporting[id];
      queryToolbar();
    });
  }
  function toggleDensity() {
    var compact = !document.documentElement.classList.contains('hh-density-compact');
    document.documentElement.classList.toggle('hh-density-compact', compact);
    try { sessionStorage.setItem('hhTableDensity', compact ? 'compact' : 'standard'); } catch (e) {}
    refresh();
  }
  function queryToolbar() {
    var on = isQueryPage() && pageId() !== 32;
    if (!on) {
      Array.prototype.forEach.call(document.querySelectorAll('.hh-query-toolbar,.hh-truncation-banner'), function (n) { n.remove(); });
      return;
    }
    var charts = dashboardCharts();
    Array.prototype.forEach.call(document.querySelectorAll('.dashboard-component-chart-holder'), function (holder) {
      var m = (holder.className || '').match(/dashboard-chart-id-(\d+)/);
      if (!m) return;
      var id = m[1];
      var root = holder.querySelector('.superset-chart-table') || holder;
      var info = toolbarInfo(charts[id], root);
      var bar = root.firstElementChild && root.firstElementChild.classList.contains('hh-query-toolbar') ? root.firstElementChild : null;
      if (!bar) {
        var stale = holder.querySelector('.hh-query-toolbar[data-hh-chart="' + id + '"]');
        if (stale) stale.remove();
        bar = document.createElement('div');
        bar.className = 'hh-query-toolbar';
        bar.setAttribute('data-hh-chart', id);
        var left = document.createElement('span');
        left.className = 'hh-qt-left';
        var summary = document.createElement('span');
        summary.className = 'hh-qt-summary';
        left.appendChild(summary);
        var right = document.createElement('span');
        right.className = 'hh-qt-right';
        var bx = document.createElement('button');
        bx.type = 'button';
        bx.className = 'hh-btn-xlsx';
        bx.textContent = '导出 Excel (.xlsx)';
        bx.addEventListener('click', function () { exportChart(id, 'xlsx'); });
        var bc = document.createElement('button');
        bc.type = 'button';
        bc.className = 'hh-btn-csv';
        bc.textContent = '导出 CSV';
        bc.addEventListener('click', function () { exportChart(id, 'csv'); });
        var bd = document.createElement('button');
        bd.type = 'button';
        bd.className = 'hh-btn-density';
        bd.addEventListener('click', toggleDensity);
        right.appendChild(bx);
        right.appendChild(bc);
        right.appendChild(bd);
        bar.appendChild(left);
        bar.appendChild(right);
        root.insertBefore(bar, root.firstChild);
      }
      var html = toolbarSummary(info);
      var s = bar.querySelector('.hh-qt-summary');
      if (s.getAttribute('data-hh-html') !== html) {
        s.innerHTML = html;
        s.setAttribute('data-hh-html', html);
      }
      var okExport = info.phase === 'ok' && info.rows > 0;
      var busy = exporting[id];
      function syncExportBtn(btn, fmt, label) {
        if (busy && busy.fmt === fmt) {
          btn.disabled = true;
          if (btn.textContent !== label.busy) btn.textContent = label.busy;
        } else {
          btn.disabled = !okExport; /* loading/failed/0 行时禁用，防止导出空文件或旧数据 */
          if (btn.textContent !== label.idle) btn.textContent = label.idle;
        }
      }
      syncExportBtn(bar.querySelector('.hh-btn-xlsx'), 'xlsx', { idle: '导出 Excel (.xlsx)', busy: '正在生成 Excel…' });
      syncExportBtn(bar.querySelector('.hh-btn-csv'), 'csv', { idle: '导出 CSV', busy: '正在生成 CSV…' });
      var bd = bar.querySelector('.hh-btn-density');
      var wantDensity = document.documentElement.classList.contains('hh-density-compact') ? '标准行高' : '紧凑行高';
      if (bd.textContent !== wantDensity) bd.textContent = wantDensity;
      /* 5 万/10 万行上限截断强警告（E3）：成功且行数 ≥ row_limit 时弹出，低于上限自动移除 */
      var showBanner = info.phase === 'ok' && info.rowLimit > 0 && info.rows >= info.rowLimit;
      var bn = holder.querySelector('.hh-truncation-banner[data-hh-chart="' + id + '"]');
      if (showBanner) {
        if (!bn) {
          bn = document.createElement('div');
          bn.className = 'hh-truncation-banner';
          bn.setAttribute('data-hh-chart', id);
          bn.setAttribute('role', 'alert');
          root.insertBefore(bn, bar.nextSibling);
        }
        var txt = '⚠️ 数据截断警告：当前查询结果已达到单次上限（' + info.rowLimit.toLocaleString() + ' 行），超出的明细已被截断！为保证数据完整，请将左侧【日期范围】缩短（如按周或单日）后重新点击“查询”再导出。';
        if (bn.textContent !== txt) bn.textContent = txt;
      } else if (bn) {
        bn.remove();
      }
    });
  }

  /* ---------- 管理列表头部 ---------- */
  function listHeader() {
    if (!/^\/(dashboard|chart|tablemodelview)\/list\//.test(location.pathname)) return;
    var existing = document.getElementById('hospital-directory-hint');
    if (existing) existing.remove();
    if (!canOpenDirectory) return;
    if (document.getElementById('hh-list-back')) return;
    var head = document.querySelector('.ant-row.menu .header, [data-test$="-list-view"] .header');
    if (!head) return;
    var wrap = document.createElement('span');
    wrap.id = 'hh-list-back';
    wrap.className = 'hh-list-back';
    var a = document.createElement('a');
    a.href = '/superset/dashboard/34/';
    a.textContent = '返回报表目录';
    a.title = '返回报表目录';
    wrap.appendChild(a);
    head.appendChild(wrap);
  }

  function navigation() {
    if (!canOpenDirectory) return;
    Array.prototype.forEach.call(document.querySelectorAll('a[href="/dashboard/list/"], a[data-hospital-directory]'), function (a) {
      if (a.closest('.dashboard-markdown') || a.id === 'hospital-manage-dashboards' || a.id === 'hh-head-manage') return;
      if (a.textContent.trim() !== '看板' && !a.hasAttribute('data-hospital-directory')) return;
      a.setAttribute('data-hospital-directory', 'true');
      a.setAttribute('href', '/superset/dashboard/34/');
      if (a.textContent !== '报表目录') a.textContent = '报表目录';
    });
    var home = document.getElementById('hospital-home-hint');
    if (home && !home.querySelector('a')) home.innerHTML = '<strong>统计报表系统</strong><a href="/superset/dashboard/34/">打开报表目录</a>，按分类选择报表并设置查询条件。';
  }

  function fitTables() {
    if (!document.documentElement.classList.contains('hh-report-page')) return;
    Array.prototype.forEach.call(document.querySelectorAll('.superset-chart-table'), function (chart) {
      var body = chart.querySelector('tbody');
      if (!body) return;
      var table = body.closest('table');
      var scroll = table.parentElement;
      var frame = scroll && scroll.parentElement;
      if (!frame || !frame.parentElement || !frame.parentElement.querySelector('.dt-controls')) return;
      var wrapper = frame.parentElement;
      var controls = wrapper.querySelector('.dt-controls');
      var pagination = wrapper.querySelector('.pagination');
      function outer(el) {
        if (!el) return 0;
        var s = getComputedStyle(el);
        return el.getBoundingClientRect().height + (parseFloat(s.marginTop) || 0) + (parseFloat(s.marginBottom) || 0);
      }
      var available = Math.max(120, wrapper.clientHeight - outer(controls) - outer(pagination) - 8);
      /* 20261105f10：扣除挂在表格容器内、frame 之前的工具条与截断横幅高度 */
      var extra = 0, prev = frame.previousElementSibling;
      while (prev) {
        if (prev.classList.contains('hh-query-toolbar') || prev.classList.contains('hh-truncation-banner')) extra += outer(prev);
        prev = prev.previousElementSibling;
      }
      available = Math.max(120, available - extra);
      var header = frame.querySelector('thead');
      var headerHeight = header ? header.getBoundingClientRect().height : 0;
      // 旧兼容资源的 sticky table 高度会停在初始值；依据现有图表容器重新量取。
      frame.style.setProperty('height', available + 'px', 'important');
      scroll.style.setProperty('height', Math.max(80, available - headerHeight) + 'px', 'important');
    });
  }
  function queryLabel() {
    if (!/\/superset\/dashboard\//.test(location.pathname)) return;
    Array.prototype.forEach.call(document.querySelectorAll('[data-test="filter-bar__apply-button"]'), function (b) {
      var walker = document.createTreeWalker(b, NodeFilter.SHOW_TEXT), node;
      while ((node = walker.nextNode())) {if (/^(应用|应用过滤器|应用筛选器|Apply|Applyfilters)$/i.test(node.nodeValue.replace(/\s/g, ''))) node.nodeValue = '查询';}
      b.setAttribute('aria-label', '查询');
    });
  }
  /* 单结果查询页：图表标题与页面标题相同则隐藏重复标题（保留更多菜单） */
  function sliceTitleDedup() {
    if (!isQueryPage()) return;
    var headers = document.querySelectorAll('[data-test="slice-header"]');
    if (headers.length !== 1) return;
    var title = nativeTitle();
    var name = headers[0].querySelector('[data-test="editable-title"], .header-title');
    if (name && name.textContent.trim() === title) {
      var a = name.querySelector('a') || name;
      if (!a.hasAttribute('data-hh-dup-slice-title')) a.setAttribute('data-hh-dup-slice-title', '1');
    }
  }
  /* 表格工具栏：页大小仅在表格专用容器内把“显示”呈现为“每页”，不全局改 Show 译文。 */
  function tableToolbarText() {
    if (!isQueryPage()) return;
    Array.prototype.forEach.call(document.querySelectorAll('.superset-chart-table .dt-select-page-size'), function (box) {
      Array.prototype.forEach.call(box.childNodes, function (n) {
        if (n.nodeType === 3 && n.nodeValue.trim() === '显示') n.nodeValue = n.nodeValue.replace('显示', '每页');
      });
    });
  }

  /* 管理列表与页头图标按钮：仅补可访问名称和焦点，不改事件与权限。 */
  function iconA11y() {
    var names = [['edit', '编辑'], ['delete', '删除'], ['download', '下载'], ['upload', '上传'],
      ['star', '收藏'], ['sync', '刷新'], ['reload', '刷新'], ['ellipsis', '更多操作'], ['more', '更多操作'],
      ['plus-square', '展开面板'], ['minus-square', '收起面板'], ['plus-circle', '新建查询'], ['plus', '新建'],
      ['link', '复制链接'], ['pushpin', '固定'],
      ['search', '搜索'], ['filter', '筛选'], ['setting', '筛选设置'], ['info-circle', '显示信息提示'],
      ['unordered-list', '列表视图'], ['appstore', '卡片视图'], ['close', '关闭'],
      ['vertical-align-top', '第一页'], ['vertical-align-bottom', '最后一页'],
      ['double-left', '上一组页'], ['double-right', '下一组页'], ['left', '上一页'], ['right', '下一页'],
      ['menu-fold', '收起菜单'], ['menu-unfold', '展开菜单']];
    Array.prototype.forEach.call(document.querySelectorAll('main button, main a, main [role="button"], main [role="tab"], .dashboard-header-container button, .dashboard-header-container a, .ant-table button, .ant-table a'), function (el) {
      if (el.textContent.trim()) return;
      if (!el.querySelector('svg,.anticon')) return;
      var existingAria = el.getAttribute('aria-label');
      if (existingAria && !el.getAttribute('title')) el.setAttribute('title', existingAria);
      if (existingAria) {
        if (el.getAttribute('title')) el.setAttribute('data-hh-icon-button', '1');
        if (el.getAttribute('title') && el.getAttribute('aria-label')) return;
      }
      var cls = (el.className || '').toString() + ' ' + Array.prototype.map.call(el.querySelectorAll('.anticon'), function (i) { return (i.className || '').toString(); }).join(' ');
      var label = '';
      for (var i = 0; i < names.length; i++) {
        if (cls.indexOf('anticon-' + names[i][0]) >= 0) { label = names[i][1]; break; }
      }
      if (!label) {
        var test = el.getAttribute('data-test') || '';
        if (test === 'refresh-button') label = '刷新';
        else if (test === 'actions-trigger') label = '更多操作';
        else if (test === 'fave-unfave-icon') label = '收藏';
        else if (test === 'filter-bar__collapse-button') label = '收起筛选区';
      }
      if (!label) return;
      if (!el.getAttribute('title')) el.setAttribute('title', label);
      if (!el.getAttribute('aria-label')) el.setAttribute('aria-label', label);
      el.setAttribute('data-hh-icon-button', '1');
    });
  }

  function refresh() {pending = 0;pageState();pageHeaderMode();navigation();fitTables();queryLabel();menuReorg();menuFixups();crumb();metaHide();catalogEnhance();visitIdLabels();tableToolbarText();emptyStateText();queryToolbar();listHeader();sliceTitleDedup();iconA11y();}
  function schedule() {if (!pending) pending = setTimeout(refresh, 120);}
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('[data-test="filter-bar__apply-button"]');
    if (b && !b.disabled) querySubmitSeen[location.pathname] = Date.now();
  }, true);
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[data-hospital-directory]');
    if (!a) return;
    if (e.button || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
    e.preventDefault();e.stopPropagation();location.assign(a.getAttribute('href'));
  }, true);
  var push = history.pushState;
  history.pushState = function () {var r = push.apply(history, arguments);schedule();return r;};
  window.addEventListener('popstate', schedule);
  window.addEventListener('resize', schedule);
  /* 20261105f10：行高偏好记忆恢复 + 图表查询偷听（供导出重放） + loading 已用时秒级跳动 */
  try { if (sessionStorage.getItem('hhTableDensity') === 'compact') document.documentElement.classList.add('hh-density-compact'); } catch (e) {}
  hookQueryFetch();
  setInterval(function () {
    if (!document.querySelector('.hh-query-toolbar')) return;
    queryToolbar();
  }, 1000);
  new MutationObserver(schedule).observe(document.body, {childList:true, subtree:true});
  if (window.ResizeObserver) new ResizeObserver(schedule).observe(document.body);
  pageState();schedule();
  if (location.pathname.indexOf('/login') !== 0) {
    fetch('/api/v1/dashboard/34', {credentials:'same-origin'}).then(function (r) {
      canOpenDirectory = r.ok;window.hospitalReportUI.directoryAccess = r.ok;schedule();
    }).catch(function () {});
  }
})();
