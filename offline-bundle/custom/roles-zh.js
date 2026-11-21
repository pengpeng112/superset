/* 医院角色管理中文显示。仅处理浏览器显示和只读查询，不改角色/权限标识。
   20261121d2（RBAC-FRONTEND-POLISH 批）：新增 ROLE_SCOPE_DESC——为 11 个「报表授权_*」角色
   （20261120-RBAC-BACKEND 建立）附一句简明管辖说明：/roles/list/ 角色列表行名称下方 12px
   浅蓝辅助小字；编辑用户的角色多选下拉选项右侧附同款短标签（纯 DOM 显示层装饰，绝不改动
   提交给后端的 role.name）。管辖看板清单依据 2026-11-21 生产 dashboard_roles 只读导出核对。
   「人工冻结」为 001283/001643 专项的管理口径描述而非独立角色，无对应行。 */
(function () {
  'use strict';
  function clearChildren(el){while(el.firstChild)el.removeChild(el.firstChild);}
  if (window.hospitalRolesZh) return;
  window.hospitalRolesZh = true;
  var actions = {
    all_database_access:'访问全部数据库',all_datasource_access:'访问全部数据集',all_query_access:'访问全部查询',
    can_activate:'启用',can_add:'新增',can_add_role_permissions:'分配角色权限',can_bulk_create:'批量创建',
    can_cache_dashboard_screenshot:'缓存看板截图',can_csv:'导出表格',can_dashboard:'查看看板',
    can_dashboard_permalink:'获取看板永久链接',can_delete:'删除',can_delete_embedded:'删除嵌入配置',
    can_delete_query:'删除查询',can_download:'下载',can_drill:'下钻分析',can_duplicate:'复制',can_edit:'编辑',
    can_estimate_query_cost:'估算查询成本',can_execute_sql_query:'执行SQL查询',can_expanded:'查看展开内容',
    can_explore:'分析数据',can_explore_json:'获取分析数据',can_export:'导出',can_export_as_example:'导出为示例',
    can_export_csv:'导出CSV',can_export_streaming_csv:'流式导出CSV',can_external_metadata:'读取外部元数据',
    can_external_metadata_by_name:'按名称读取外部元数据',can_fetch_datasource_metadata:'读取数据源元数据',
    can_file_handler:'处理文件',can_format_sql:'格式化SQL',can_get:'查看',can_get_column_values:'读取列值',
    can_get_drill_info:'获取下钻信息',can_get_embedded:'查看嵌入配置',can_get_or_create_dataset:'获取或创建数据集',
    can_get_results:'获取查询结果',can_grant_guest_token:'签发访客令牌',can_import_:'导入',can_info:'查看配置信息',
    can_invalidate:'清除缓存',can_language_pack:'读取语言包',can_list:'查看列表',can_list_role_permissions:'查看角色权限',
    can_list_roles:'查看角色列表',can_log:'记录日志',can_migrate_query:'迁移查询',can_post:'新增',can_put:'更新',
    can_put_chart_customizations:'设置图表定制',can_query:'查询',can_query_form_data:'查询表单数据',can_read:'查看',
    can_recent_activity:'查看最近活动',can_samples:'查看样例数据',can_save:'保存',can_set_embedded:'设置嵌入配置',
    can_share_chart:'分享图表',can_share_dashboard:'分享看板',can_show:'查看详情',can_slice:'查看图表',
    can_sqllab:'使用SQL工作台',can_sqllab_history:'查看SQL历史',can_tag:'管理标签',can_tags:'查看标签',
    can_this_form_get:'打开表单',can_this_form_post:'提交表单',can_time_range:'获取时间范围',
    can_update_role_groups:'更新角色用户组',can_update_role_users:'更新角色成员',can_upload:'上传',
    can_userinfo:'查看个人信息',can_validate_expression:'校验表达式',can_view_chart_as_table:'查看图表明细表',
    can_view_query:'查看查询语句',can_warm_up_cache:'预热缓存',can_write:'编辑',copyrole:'复制角色',
    database_access:'访问数据库',datasource_access:'访问数据集',menu_access:'访问菜单',resetmypassword:'修改本人密码',
    resetpasswords:'重置用户密码',schema_access:'访问数据库模式',userinfoedit:'编辑个人信息'
  };
  var resources = {
    'Action Log':'操作日志',AdvancedDataType:'高级数据类型','Alerts & Report':'告警与报表',Annotation:'注释',
    'Annotation Layers':'注释层',Api:'数据接口',AsyncEventsRestApi:'异步事件',AvailableDomains:'可用域名',
    'CSS Templates':'样式模板',CacheRestApi:'缓存',Chart:'图表',Charts:'图表',CssTemplate:'样式模板',
    CurrentUserRestApi:'当前用户',Dashboard:'看板',DashboardFilterStateRestApi:'看板筛选状态',
    DashboardPermalinkRestApi:'看板永久链接',Dashboards:'看板',Data:'数据',Database:'数据库',Databases:'数据库',
    Dataset:'数据集',Datasets:'数据集',Datasource:'数据源',DynamicPlugin:'动态插件',EmbeddedDashboard:'嵌入看板',
    Explore:'数据分析',ExploreFormDataRestApi:'分析表单',ExplorePermalinkRestApi:'分析永久链接',Extensions:'扩展功能',
    Group:'用户组',Home:'首页',ImportExportRestApi:'导入导出','List Groups':'用户组列表','List Roles':'角色列表',
    'List Users':'用户列表',Log:'日志',Manage:'管理',MenuApi:'菜单',OpenApi:'开放接口',Permission:'权限',
    PermissionViewMenu:'权限与资源',Plugins:'插件',Query:'查询','Query Search':'查询搜索',ReportSchedule:'报表计划',
    ResetMyPasswordView:'本人密码',ResetPasswordView:'用户密码',Role:'角色',RoleModelView:'角色管理',
    RoleRestAPI:'角色接口','Row Level Security':'行级数据权限',RowLevelSecurity:'行级数据权限',
    'SQL Editor':'SQL编辑器','SQL Lab':'SQL工作台',SQLLab:'SQL工作台','Saved Queries':'已保存查询',SavedQuery:'已保存查询',
    Security:'安全管理',SecurityRestApi:'安全接口',SqlLabPermalinkRestApi:'SQL永久链接',Superset:'系统功能',
    SwaggerView:'接口文档',TabStateView:'查询页签',TableSchemaView:'表结构',Tag:'标签',TagView:'标签管理',Tags:'标签',
    Task:'任务',Tasks:'任务',Theme:'主题',Themes:'主题',User:'用户','User Registrations':'用户注册',
    UserDBModelView:'用户管理',UserGroupModelView:'用户组管理',UserInfoEditView:'个人信息',
    UserRegistrationsRestAPI:'用户注册接口',ViewMenu:'资源菜单',security:'安全管理',user:'用户',
    all_database_access:'全部数据库',all_datasource_access:'全部数据集',all_query_access:'全部查询'
  };
  var builtins = {Admin:'系统管理员',Alpha:'报表开发人员',Gamma:'普通报表用户',Public:'匿名访问',sql_lab:'SQL查询人员'};
  /* 20261121d2：11 个报表授权_ 角色的管辖说明（信息科 1~2 人赋权时一眼看懂）。
     看板编号与 20261120-RBAC-BACKEND 终态绑定一致；管理员新增/改绑看板后同步本字典。 */
  var ROLE_SCOPE_DESC = {
    '报表授权_病案离院明细': '管辖：2 病案首页非医嘱离院与死亡明细（病案室专项）',
    '报表授权_抗菌办': '管辖：61–70 抗菌药物监测 10 项专项查询（人工冻结，仅指定人员）',
    '报表授权_门急诊患者明细': '管辖：47 门诊转住院途径 / 49 急诊分诊明细＋目录 27、28',
    '报表授权_手术明细提取': '管辖：50 门诊手术 / 51 科室手术质量 / 52 住院手术提取＋目录 29',
    '报表授权_院领导与运营驾驶舱': '管辖：72 全院运营 / 73 门急诊流量 / 74 手术质量 / 75 护理床位四大驾驶舱',
    '报表授权_质控与全院月报': '管辖：32/35 月报、36 病区日报、37 手术统计、39 检查开单、44 月上报、45 医疗月报＋目录 25/29/33',
    '报表授权_绩效考核管理': '管辖：40 床旁结算、46 绩效月报、58/59 检查统计、60 高质量发展监测＋目录 31',
    '报表授权_护理部管理': '管辖：41 护理月报、42 护理日报、43 护理单元＋75 护理驾驶舱＋目录 26',
    '报表授权_门诊与窗口管理': '管辖：48 责任组门诊、53–57 门诊流量五表＋73 门急诊驾驶舱＋目录 27/28/30',
    '报表授权_临床科室日常统计': '管辖：36 病区日报、37 手术量、39 检查开单、41 护理月报＋目录 26/29/33',
    '报表授权_系统字典维护': '管辖：38 报表科室维护（信息网络中心 BI 运维）'
  };
  var categories = {managed:'常用角色',business:'业务授权',department:'科室数据范围',system:'系统内置',all:'全部角色'};
  function isRolePage() { return /^\/roles(?:\/|$)/.test(location.pathname); }
  function category() {
    try { var c=sessionStorage.getItem('hospital-role-category'); return categories[c] ? c : 'managed'; }
    catch (_) { return 'managed'; }
  }
  function type(name) { return builtins[name] ? 'system' : /^(科室_|role_)/.test(name) ? 'department' : 'business'; }
  function permissionLabel(item) {
    var a=item.permission.name, r=item.view_menu.name;
    return (actions[a] || a.replace(/_/g,' '))+' · '+(resources[r] || r);
  }
  // API 的 q 使用 Rison；解析只读查询，保留原有成员/权限/名称筛选。
  function decodeRison(s) {
    var i=0;
    function read() {
      var c=s[i++], out, key;
      if(c==='(') {
        out={}; if(s[i]===')'){i++;return out;}
        do {key=read();if(s[i++]!==':')throw Error('Rison colon');out[key]=read();c=s[i++];} while(c===',');
        if(c!==')')throw Error('Rison object');return out;
      }
      if(c==='!') {
        c=s[i++];if(c==='t')return true;if(c==='f')return false;if(c==='n')return null;
        if(c!=='(')throw Error('Rison literal');out=[];if(s[i]===')'){i++;return out;}
        do {out.push(read());c=s[i++];} while(c===',');if(c!==')')throw Error('Rison array');return out;
      }
      if(c==="'") {
        out='';while(i<s.length){c=s[i++];if(c==="'")return out;if(c==='!')c=s[i++];out+=c;}throw Error('Rison string');
      }
      out=c;while(i<s.length && !/[:,()]/.test(s[i]))out+=s[i++];
      return /^-?\d+(?:\.\d+)?$/.test(out) ? Number(out) : out;
    }
    var value=read();if(i!==s.length)throw Error('Rison trailing');return value;
  }
  function encodeRison(v) {
    if(v===null)return '!n';if(v===true)return '!t';if(v===false)return '!f';
    if(Array.isArray(v))return '!('+v.map(encodeRison).join(',')+')';
    if(typeof v==='object')return '('+Object.keys(v).map(function(k){return encodeRison(k)+':'+encodeRison(v[k]);}).join(',')+')';
    if(typeof v==='number')return String(v);
    return "'"+String(v).replace(/!/g,'!!').replace(/'/g,"!'")+"'";
  }
  var nativeFetch=window.fetch.bind(window), permissionCache=null;
  async function collect(url, init, q) {
    var items=[], first, page=0;
    do {
      var requestUrl=new URL(url);requestUrl.searchParams.set('q',encodeRison(Object.assign({},q,{page:page,page_size:100})));
      var response=await nativeFetch(requestUrl.href,init);
      if(!response.ok)return {response:response};
      var body=await response.json();if(!Array.isArray(body.result))throw Error('Invalid list response');
      if(!first)first=body;items=items.concat(body.result);page++;
      if(!body.result.length && items.length<body.count)throw Error('Incomplete list');
      if(page>100)throw Error('List exceeds display limit');
    } while(items.length<first.count);
    return {body:first,items:items};
  }
  function resultResponse(source, items, q) {
    var size=Math.max(1,Number(q.page_size)||100),page=Math.max(0,Number(q.page)||0);
    var slice=items.slice(page*size,(page+1)*size);
    return new Response(JSON.stringify(Object.assign({},source,{count:items.length,result:slice,ids:slice.map(function(x){return x.id;})})),
      {status:200,headers:{'Content-Type':'application/json'}});
  }
  window.fetch=async function(input,init) {
    var url=new URL(typeof input==='string' ? input : input.url || String(input),location.href);
    var method=(init && init.method || input.method || 'GET').toUpperCase();
    var roleQuery=isRolePage() && url.origin===location.origin && url.pathname==='/api/v1/security/roles/search/';
    var permQuery=isRolePage() && url.origin===location.origin && url.pathname==='/api/v1/security/permissions-resources/';
    if(method!=='GET' || (!roleQuery && !permQuery))return nativeFetch(input,init);
    try {
      var q=decodeRison(url.searchParams.get('q') || '()');
      if(roleQuery && category()==='all')return nativeFetch(input,init);
      if(roleQuery) {
        var data=await collect(url,init,q);if(data.response)return data.response;
        var c=category();var roles=data.items.filter(function(r){var t=type(r.name);return c==='managed' ? t!=='department' : t===c;});
        return resultResponse(data.body,roles,q);
      }
      // 权限以 ID 保存。中文标签只进入当前浏览器，搜索同时匹配中文和内部名称。
      var filters=(q.filters || []).map(function(f){return Object.assign({},f,{op:f.op || f.opr});});
      if(filters.some(function(f){return !['id','permission.name','view_menu.name'].includes(f.col) || !['ct','eq','sw','in'].includes(f.op);})) {
        var fallback=await nativeFetch(input,init);if(!fallback.ok)return fallback;
        var fb=await fallback.json();fb.result=fb.result.map(translatePermission);
        return new Response(JSON.stringify(fb),{headers:{'Content-Type':'application/json'}});
      }
      if(!permissionCache)permissionCache=collect(url,init,{order_column:'id',order_direction:'asc'}).catch(function(e){permissionCache=null;throw e;});
      var perms=await permissionCache;if(perms.response){permissionCache=null;return perms.response;}
      var rows=perms.items.filter(function(item){
        return filters.every(function(f){
          if(f.col==='id')return f.op==='in' && Array.isArray(f.value) ? f.value.map(Number).includes(Number(item.id)) : Number(item.id)===Number(f.value);
          var original=f.col==='permission.name' ? item.permission.name : item.view_menu.name;
          var translated=f.col==='permission.name' ? actions[original] || original : resources[original] || original;
          var needle=String(f.value).toLowerCase();var values=[original,original.replace(/_/g,' '),translated,permissionLabel(item)].map(function(x){return x.toLowerCase();});
          return values.some(function(v){return f.op==='eq' ? v===needle : f.op==='sw' ? v.startsWith(needle) : v.includes(needle);});
        });
      }).map(translatePermission);
      return resultResponse(perms.body,rows,q);
    } catch(e) {
      console.warn('角色中文显示回退',e.name);
      return nativeFetch(input,init);
    }
  };
  function translatePermission(item) {
    var a=item.permission.name,r=item.view_menu.name;
    return Object.assign({},item,{permission:Object.assign({},item.permission,{name:actions[a] || a}),
      view_menu:Object.assign({},item.view_menu,{name:resources[r] || r})});
  }
  function setText(el,text) {if(el && el.textContent!==text)el.textContent=text;}
  function legacyPermission(text) {
    var split=text.indexOf(' on ');if(split<0)return text;
    var a=text.slice(0,split).replace(/ /g,'_'),r=text.slice(split+4);
    return (actions[a] || text.slice(0,split))+' · '+(resources[r] || r);
  }
  var permissionGroups = {
    reports:'看板与图表',data:'数据集与数据库',scope:'数据范围授权',
    sql:'SQL查询与导出',security:'用户与角色管理',system:'系统与其他'
  };
  function permissionGroup(item) {
    var a=item.permission.name,r=item.view_menu.name;
    if(/^(all_.*_access|database_access|datasource_access|schema_access)$/.test(a))return 'scope';
    if(/SQL|SqlLab|Query|TabState|TableSchema/.test(r))return 'sql';
    if(/Role|User|Group|Permission|Security|security|ViewMenu|Password/.test(r) || r==='user')return 'security';
    if(/Chart|Dashboard|Explore|Annotation|ReportSchedule/.test(r) || /^(Alerts & Report|Annotation Layers)$/.test(r))return 'reports';
    if(/Data|Datasource|ImportExport/.test(r))return 'data';
    return 'system';
  }
  function permissionBridge(input) {
    var key=Object.keys(input).find(function(k){return k.startsWith('__reactFiber');});
    var fiber=input[key],candidate;
    while(fiber) {
      var p=fiber.memoizedProps || {};
      if(p.id==='rolePermissions' && p.mode==='multiple' && typeof p.onChange==='function')candidate=p;
      fiber=fiber.return;
    }
    return candidate;
  }
  function selectedIds(bridge) {
    return (bridge.value || []).map(function(v){return Number(typeof v==='object' ? v.value : v);});
  }
  function sameIds(a,b) {return a.length===b.length && a.every(function(v,i){return v===b[i];});}
  var permissionEditor=null;
  function buildPermissionEditor(input) {
    var bridge=permissionBridge(input);
    if(!bridge)return; // 组件接口不匹配时保留原编辑器。
    var native=input.closest('.ant-select');if(!native)return;
    if(permissionEditor && permissionEditor.input===input)return;
    var panel=document.createElement('section');panel.className='hospital-permission-editor';
    panel.setAttribute('aria-label','分类功能权限');
    panel.innerHTML='<div class="hp-loading" role="status">正在加载权限名称与分类…</div>';
    native.parentElement.appendChild(panel);
    var initialIds=selectedIds(bridge);
    var state={input:input,native:native,panel:panel,group:'all',query:'',selectedOnly:initialIds.length>0,items:[],selected:initialIds,ready:false};
    permissionEditor=state;
    var url=new URL('/api/v1/security/permissions-resources/',location.origin);
    if(!permissionCache)permissionCache=collect(url,undefined,{order_column:'id',order_direction:'asc'}).catch(function(e){permissionCache=null;throw e;});
    permissionCache.then(function(data){
      if(!panel.isConnected)return;
      if(data.response)throw Error('Permissions unavailable');
      state.items=data.items.map(function(item){return {id:Number(item.id),label:permissionLabel(item),group:permissionGroup(item),raw:item,
        broad:/^all_.*_access$/.test(item.permission.name)};});
      state.selected=selectedIds(permissionBridge(input));
      state.selected.forEach(function(id){if(!state.items.some(function(x){return x.id===id;}))state.items.push({id:id,label:'未找到定义的权限（编号 '+id+'）',group:'system',missing:true});});
      state.items.sort(function(a,b){return a.label.localeCompare(b.label,'zh-CN') || a.id-b.id;});
      state.ready=true;native.style.display='none';
      var modal=input.closest('.ant-modal');if(modal){modal.style.width='960px';modal.style.maxWidth='calc(100vw - 32px)';}
      panel.innerHTML='<div class="hp-tools"><input type="search" aria-label="搜索功能权限" placeholder="搜索权限或报表名称，例如：图表、导出、病案"><label><input type="checkbox" aria-label="只看已选权限">只看已选</label><strong class="hp-summary" aria-live="polite"></strong></div><div class="hp-layout"><nav aria-label="权限分类"></nav><div class="hp-content"><p class="hp-count" aria-live="polite"></p><div class="hp-list"></div></div></div><p class="hp-note">勾选后点击页面“保存”才生效。“数据范围授权”控制可访问的数据对象；科室数据隔离由行级规则控制。</p>';
      panel.querySelector('[aria-label="搜索功能权限"]').addEventListener('input',function(e){state.query=e.target.value.trim().toLowerCase();paintPermissionEditor(state);});
      panel.querySelector('[aria-label="只看已选权限"]').addEventListener('change',function(e){state.selectedOnly=e.target.checked;paintPermissionEditor(state);});
      panel.querySelector('[aria-label="只看已选权限"]').checked=state.selectedOnly;
      paintPermissionEditor(state);
    }).catch(function(){
      if(!panel.isConnected)return;panel.textContent='权限分类加载失败，请关闭后重试。原权限选择框仍可使用。';
      native.style.display='';permissionCache=null;
    });
  }
  function paintPermissionEditor(state) {
    if(!state.ready || !state.panel.isConnected)return;
    var selected=new Set(state.selected),panel=state.panel;
    setText(panel.querySelector('.hp-summary'),'已选 '+selected.size+' 项');
    var nav=panel.querySelector('nav');clearChildren(nav);
    Object.keys(Object.assign({all:'全部权限'},permissionGroups)).forEach(function(group){
      var items=state.items.filter(function(item){return group==='all' || item.group===group;});
      var count=items.filter(function(item){return selected.has(item.id);}).length;
      var button=document.createElement('button');button.type='button';button.dataset.group=group;
      button.setAttribute('aria-pressed',String(state.group===group));
      button.textContent=(group==='all'?'全部权限':permissionGroups[group])+' '+count+'/'+items.length;
      button.addEventListener('click',function(){state.group=group;paintPermissionEditor(state);});nav.appendChild(button);
    });
    var visible=state.items.filter(function(item){
      return (state.group==='all'||item.group===state.group) && (!state.selectedOnly||selected.has(item.id)) &&
        (!state.query||(item.label+' '+(item.raw?item.raw.permission.name+' '+item.raw.view_menu.name:'')).toLowerCase().includes(state.query));
    });
    setText(panel.querySelector('.hp-count'),(state.group==='all'?'全部权限':permissionGroups[state.group])+' · 当前显示 '+visible.length+' 项');
    var list=panel.querySelector('.hp-list');clearChildren(list);
    if(!visible.length){var empty=document.createElement('p');empty.textContent='没有匹配的权限';list.appendChild(empty);}
    visible.forEach(function(item){
      var row=document.createElement('label');row.className='hp-permission';row.dataset.permissionId=String(item.id);
      var checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.checked=selected.has(item.id);checkbox.setAttribute('aria-label',item.label);
      var text=document.createElement('span');text.textContent=item.label;row.appendChild(checkbox);row.appendChild(text);
      if(state.group==='all'){var tag=document.createElement('small');tag.textContent=permissionGroups[item.group];row.appendChild(tag);}
      if(item.broad){var wide=document.createElement('small');wide.className='hp-broad';wide.textContent='全部数据';row.appendChild(wide);}
      checkbox.addEventListener('change',function(){
        var bridge=permissionBridge(state.input);if(!bridge){checkbox.checked=selected.has(item.id);return;}
        var ids=selectedIds(bridge);ids=ids.filter(function(id){return id!==item.id;});if(checkbox.checked)ids.push(item.id);
        var values=ids.map(function(id){var definition=state.items.find(function(x){return x.id===id;});return {value:id,label:definition?definition.label:String(id)};});
        // 调用原表单控件的变更回调，只更新未保存的表单值。
        bridge.onChange(values,values);state.selected=ids;paintPermissionEditor(state);
      });list.appendChild(row);
    });
  }
  function installPermissionStyles() {
    if(document.getElementById('hospital-permission-style'))return;
    var style=document.createElement('style');style.id='hospital-permission-style';
    style.textContent='.hospital-permission-editor{border:1px solid #d7e3ef;border-radius:8px;background:#fff;padding:12px;color:#35516c}.hp-tools{display:flex;align-items:center;flex-wrap:wrap}.hp-tools>*{margin:0 14px 8px 0}.hp-tools label input{margin-right:6px}.hp-layout nav button{margin-bottom:6px}.hp-permission input{margin-right:8px}.hp-tools input[type=search]{flex:1;min-width:210px;padding:8px 10px;border:1px solid #a8bdcf;border-radius:6px}.hp-tools label{display:flex;align-items:center}.hp-summary{color:#0e4c86}.hp-layout{display:grid;grid-template-columns:190px minmax(0,1fr);gap:12px;margin-top:12px}.hp-layout nav{display:flex;flex-direction:column}.hp-layout nav button{padding:9px 10px;border:1px solid #d7e3ef;border-radius:6px;background:#f8fafc;color:#35516c;text-align:left;cursor:pointer}.hp-layout nav button[aria-pressed=true]{background:#e8f1fa;border-color:#0e4c86;color:#0e4c86;font-weight:600}.hp-count{margin:0 0 8px}.hp-list{max-height:310px;min-height:140px;overflow:auto;border:1px solid #e7edf3;border-radius:6px;padding:4px 10px}.hp-permission{display:flex;align-items:flex-start;padding:8px 0;border-bottom:1px solid #edf1f5;cursor:pointer;line-height:1.6}.hp-permission input{margin-top:5px;flex-shrink:0}.hp-permission>span{flex:1;overflow-wrap:anywhere}.hp-permission small{color:#637b91;white-space:nowrap}.hp-permission .hp-broad{color:#a3560b}.hp-note{font-size:12px;line-height:1.6;margin:10px 0 0;color:#637b91}@media(max-width:650px){.hp-layout{grid-template-columns:1fr}.hp-layout nav{flex-direction:row;flex-wrap:wrap}.hp-layout nav button{font-size:12px}.hp-permission small{display:none}}';
    document.head.appendChild(style);
  }
  /* 20261121d2：管辖说明注入样式（角色列表行 + 用户编辑角色下拉选项，纯显示层） */
  function installScopeStyles() {
    if(document.getElementById('hospital-role-scope-style'))return;
    var st=document.createElement('style');st.id='hospital-role-scope-style';
    st.textContent='.hh-role-scope{margin-top:2px;font-size:12px;line-height:18px;color:#5f8bb4;font-weight:400;white-space:normal;word-break:break-all}'
      +'.ant-table-tbody tr[data-test="table-row"] [data-test="table-row-cell"]{min-width:230px}'
      +'.hh-role-scope-opt{display:block;margin-top:1px;font-size:11px;line-height:16px;color:#7fa3c4;font-weight:400;white-space:normal}';
    document.head.appendChild(st);
  }
  /* 角色多选下拉选项短标签（/roles/list 与用户编辑页通用；不改提交值，仅 DOM 装饰） */
  function decorateRoleOptions() {
    var opts=document.querySelectorAll('.ant-select-item-option');
    if(!opts.length)return;
    installScopeStyles();
    opts.forEach(function(opt){
      var name=(opt.getAttribute('title')||'').trim();
      var host=opt.querySelector('.ant-select-item-option-content')||opt;
      var tag=host.querySelector('.hh-role-scope-opt');
      if(!ROLE_SCOPE_DESC[name]){if(tag)tag.remove();return;}
      if(!tag){
        tag=document.createElement('span');tag.className='hh-role-scope-opt';
        tag.textContent='· '+ROLE_SCOPE_DESC[name].replace(/^管辖：/,'');
        host.appendChild(tag);
      }
    });
  }
  /* 20261121d2：/roles/list/ 实为 FAB 服务端渲染表格（第 3 列纯文本角色名，非 antd）——
     逐行按名称单元格文本命中 ROLE_SCOPE_DESC 时，在名称单元格内追加管辖说明小字 */
  function decorateFabRows() {
    if(!/\/roles\/list/.test(location.pathname))return;
    document.querySelectorAll('.table tbody tr').forEach(function(tr){
      var cells=tr.cells;
      if(!cells||cells.length<3)return;
      /* 行结构（生产实测）：[0]选择框 [1]操作按钮组 [2]角色名(纯文本) [3]权限摘要 */
      var td=cells[2];
      /* 名称只取首次纯文本（缓存进 dataset），避免追加的管辖说明在重复渲染时混入名称匹配 */
      if(!td.dataset.hospitalOriginal){
        td.dataset.hospitalOriginal=(td.textContent||'').replace(/\s+/g,' ').trim();
      }
      var name=td.dataset.hospitalOriginal;
      if(!name||name.length>60||td.querySelector('a,button'))return;
      var scope=ROLE_SCOPE_DESC[name];
      var sub=td.querySelector('.hh-role-scope');
      if(scope){
        installScopeStyles();
        if(!sub){sub=document.createElement('div');sub.className='hh-role-scope';td.appendChild(sub);}
        setText(sub,scope);
      } else if(sub) sub.remove();
    });
  }
  function render() {
    decorateRoleOptions();
    if(!isRolePage())return;
    decorateFabRows();
    var permissionInput=document.getElementById('rolePermissions');
    if(permissionInput){installPermissionStyles();buildPermissionEditor(permissionInput);}
    if(permissionEditor && !permissionEditor.panel.isConnected)permissionEditor=null;
    if(permissionEditor && permissionEditor.ready){
      var bridge=permissionBridge(permissionEditor.input);
      if(bridge){var ids=selectedIds(bridge);if(!sameIds(ids,permissionEditor.selected)){permissionEditor.selected=ids;paintPermissionEditor(permissionEditor);}}
    }
    document.querySelectorAll('label[for="roleName"],label[for="name"]').forEach(function(el){setText(el,'角色名称');el.title='角色名称';});
    document.querySelectorAll('label[for="rolePermissions"],label[for="permissions"]').forEach(function(el){setText(el,'功能权限');el.title='功能权限';});
    document.querySelectorAll('#permissions option').forEach(function(el){setText(el,legacyPermission(el.textContent));});
    document.querySelectorAll('[data-test="add-role-button"] > span:last-child').forEach(function(el){setText(el,'新增角色');});
    document.querySelectorAll('.ant-table-column-title').forEach(function(el){if(el.textContent==='名称')setText(el,'角色名称');});
    document.querySelectorAll('[data-test="permissions-select"] .ant-select-selection-placeholder').forEach(function(el){setText(el,'请选择功能权限，可输入中文搜索');});
    document.querySelectorAll('.ant-table-tbody tr[data-test="table-row"]').forEach(function(row){
      var cell=row.querySelector('[data-test="table-row-cell"]');if(!cell)return;
      var span=cell.querySelector('span');if(!span)return;
      var original=cell.getAttribute('title') || cell.dataset.hospitalOriginal || span.textContent;
      cell.dataset.hospitalOriginal=original;
      var label=builtins[original] ? builtins[original]+'（'+original+'）' : original.startsWith('科室_') ? '科室范围 · '+original.slice(3) : original;
      setText(span,label);
      /* 20261121d2：报表授权_ 角色行附管辖说明（12px 浅蓝小字，不撑破行高） */
      var scope=ROLE_SCOPE_DESC[original];
      var sub=cell.querySelector('.hh-role-scope');
      if(scope){
        installScopeStyles();
        if(!sub){sub=document.createElement('div');sub.className='hh-role-scope';cell.appendChild(sub);}
        setText(sub,scope);
      } else if(sub) sub.remove();
    });
    var add=document.querySelector('[data-test="add-role-button"]');
    if(location.pathname==='/roles/' && add && !document.getElementById('hospital-role-categories')) {
      var panel=document.createElement('section');panel.id='hospital-role-categories';
      panel.style.cssText='margin:16px 24px;padding:16px 20px;border:1px solid #d7e3ef;border-radius:10px;background:#fff;color:#35516c';
      var title=document.createElement('strong');title.textContent='角色分类';panel.appendChild(title);
      var select=document.createElement('select');select.setAttribute('aria-label','角色分类');select.style.cssText='margin-left:16px;padding:6px 10px;border:1px solid #a8bdcf;border-radius:6px';
      Object.keys(categories).forEach(function(k){var opt=document.createElement('option');opt.value=k;opt.textContent=categories[k];select.appendChild(opt);});
      select.value=category();select.addEventListener('change',function(){sessionStorage.setItem('hospital-role-category',select.value);location.reload();});panel.appendChild(select);
      var help=document.createElement('p');help.style.cssText='margin:10px 0 0;line-height:1.7';
      help.textContent='业务授权决定能使用哪些报表；科室数据范围用于限定数据范围。常用角色显示业务授权与系统内置角色，科室角色请切换分类查看。';panel.appendChild(help);
      var table=document.querySelector('.ant-table-wrapper');if(table)table.parentElement.insertBefore(panel,table);else add.parentElement.insertAdjacentElement('afterend',panel);
    }
  }
  var scheduled=false;
  new MutationObserver(function(){if(scheduled)return;scheduled=true;requestAnimationFrame(function(){scheduled=false;render();});}).observe(document,{childList:true,subtree:true,characterData:true});
  document.addEventListener('DOMContentLoaded',render);render();
})();
