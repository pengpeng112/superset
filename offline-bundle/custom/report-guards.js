/* 20261115g6（FINAL-CLOSEOUT 收尾续）：版本串自 20261112g5 递增——2026-11-14 g5 初版与
   250ms 节流热修版共用同一版本号，老客户端（Chromium 80/87）可能残留初版缓存；本版代码
   逻辑与 g5 节流热修终版完全一致，仅推进版本串强制全量客户端重校验。
   守卫页 39/51/52/58/59/62/65 均为纯数字路径（无别名），page() 数字匹配无需改动。
   20261112g5（WARMUP-PERF 批）：慢报表大跨度查询防呆闭环——
   59（检查人次按执行科室统计·门诊，ds337）：草稿跨度 >31 自然日拦截（Oracle PIVOT
   多项目交叉汇总大跨度 >300s 超时）；>7 天且 visit_id 范围跨度 >20 时温和橙色提示
   （预计 20~50 秒，不拦截）。
   39（ds281）/58（ds336）：跨度过大逼近前端 60s 上限，>31 天温和橙色提示不拦截；
   39 号 ds281 无筛选兜底窗已核实为“当天减 7 天”（合理默认窗），不动业务 SQL。
   20261105g4：62（住院检验）/65（住院医嘱）跨度 >15 自然日拦截。
   20261022g3：按当前控件草稿校验，避免用已应用旧值拦掉合法查询。
   51/52 科室、58 分支、59 visit_id 缺端/倒置在提交前提示。
   58/59 日期说明里“默认最近7个自然日”与 336/337 两端为空时的 SQL 不一致，只改页面提示。
   不改任何业务 SQL，不给 visit_id 设默认，不把 1..99 收成唯一合法域。 */
(function(){
  'use strict';
  if(window.hospitalVisitGuard)return;
  var api=window.hospitalVisitGuard={version:'20261115g6'};
  var V1='NATIVE_FILTER-P59-V1',V2='NATIVE_FILTER-P59-V2';
  var REQUIRED={51:{id:'NATIVE_FILTER-P51-DEPT',name:'手术科室'},52:{id:'NATIVE_FILTER-P52-DEPT',name:'手术科室'},58:{id:'NATIVE_FILTER-P58-BRANCH',name:'门诊或住院分支'}};
  var SPAN_LIMIT={62:15,65:15}; /* 单次查询最大跨度（自然日，含端）；两表单月 5 万~15 万行必超时/截断 */
  var SPAN_MSG='该明细表数据量极大（单月超 10 万行），单次查询跨度请勿超过 15 天（建议按单日或单周查询导出）。';
  var BLOCK31={59:31}; /* 59 号页拦截阈值（自然日，含端；31 天及以下放行） */
  var BLOCK31_MSG='检查执行统计涉及全院多项目交叉汇总，单次查询日期跨度请勿超过 31 天';
  /* 温和橙色提示（不拦截提交）：39/58 为 >31 天；59 为 >7 天且就诊次数跨度 >20 */
  var SOFT_IDS={39:1,58:1,59:1};
  var SOFT_MSGS={
    39:'提示：检查按开单科室统计为多源交叉汇总，当前日期跨度较大，预计耗时 20~60 秒，请耐心等待或缩小范围',
    58:'提示：检查人次按开单科室统计当前日期跨度较大，预计耗时 20~60 秒，请耐心等待或缩小范围',
    59:'提示：当前日期与就诊次数范围较宽，查询预计耗时 20~50 秒，请耐心等待'
  };
  function isGuardPage(id){return id===59||!!REQUIRED[id]||!!SPAN_LIMIT[id]||!!SOFT_IDS[id];}
  function dateSpan(){
    /* 读当前日历草稿起止：{days:含端自然日数} / {none:true 未选} / {ready:false 条件未就绪} */
    var ui=window.hospitalDateUI,pickers=document.querySelectorAll('.hdt-picker[data-filter-id]');
    for(var i=0;i<pickers.length;i++){
      var fid=pickers[i].getAttribute('data-filter-id');
      var v=ui&&typeof ui.draftFor==='function'?ui.draftFor(fid):undefined;
      var pr=(v!=null&&ui&&typeof ui.parseRange==='function')?ui.parseRange(v):null;
      if(pr&&pr.a&&pr.b)return {days:Math.round((pr.b-pr.a)/86400000)}; /* 草稿值为排他上界，差值即含端天数 */
      if(v==='No filter'||v==='')return {none:true};
    }
    /* 草稿接口不可用时退回日历输入框显示值（range 显示“起 至 止”，止为含端日期） */
    var inp=document.querySelector('.hdt-picker[data-mode=range] input');
    if(inp&&inp.value){
      var m=inp.value.match(/(\d{4})-(\d{2})-(\d{2})\s*至\s*(\d{4})-(\d{2})-(\d{2})/);
      if(m){var a=new Date(+m[1],+m[2]-1,+m[3]),b=new Date(+m[4],+m[5]-1,+m[6]+1);
        return {days:Math.round((b-a)/86400000)};}
      if(/^(开始|.*至.*)?$/.test(inp.value)&&!/\d{4}-\d{2}-\d{2}/.test(inp.value))return {none:true};
    }
    return {ready:false};
  }
  var OLD='默认最近7个自然日';
  var NEW='未选日期时按原 SQL 只含当天减 7 天的那一天（结束为该日次日零点）。日期候选中的近 7 天不是这条默认窗';
  function page(){var m=location.pathname.match(/\/superset\/dashboard\/(\d+)\/?$/);return m?+m[1]:0;}
  function norm(v){
    if(v==null)return {missing:true};
    if(Array.isArray(v)){if(!v.length)return {missing:true};if(v.length!==1)return {bad:true};return norm(v[0]);}
    if(typeof v==='boolean'||typeof v==='object')return {bad:true};
    if(typeof v==='number'){
      if(!isFinite(v)||Math.floor(v)!==v||v<0||v>99)return {bad:true};
      var ns=String(v);if(!/^\d{1,2}$/.test(ns))return {bad:true};
      return {s:ns,n:v};
    }
    if(typeof v==='string'){
      if(v==='')return {missing:true};
      if(!/^\d{1,2}$/.test(v))return {bad:true};
      return {s:v,n:parseInt(v,10)};
    }
    return {bad:true};
  }
  function classify(v1,v2){
    var a=norm(v1),b=norm(v2);
    if(a.bad||b.bad)return {ok:false,reason:'visit_id 只能是 1 到 2 位数字'};
    if(a.missing||b.missing)return {ok:false,reason:'请同时选择 visit_id 下界和上界'};
    if(a.n>b.n)return {ok:false,reason:'visit_id 上界不能小于下界'};
    return {ok:true,low:a.s,high:b.s};
  }
  function findStore(){
    var e=document.querySelector('[data-test=grid-content]');if(!e)return null;
    var k=Object.keys(e).find(function(k){return k.indexOf('__reactFiber')===0;});if(!k)return null;
    var f=e[k];while(f){var p=f.memoizedProps,s=p&&(p.store||(p.value&&p.value.store));if(s&&s.getState)return s;f=f.return;}
    return null;
  }
  function maskValue(state,id){
    var dm=state&&state.dataMask&&state.dataMask[id];
    var fs=dm&&dm.filterState;
    if(!fs||!('value' in fs))return undefined;
    return fs.value;
  }
  function draftValue(id){
    var input=document.getElementById(id);if(!input)return {ready:false};
    var key=Object.keys(input).find(function(k){return k.indexOf('__reactFiber')===0;});
    if(!key)return {ready:false};
    var f=input[key],nativeResult=null,fallback=null;
    while(f){var p=f.memoizedProps||{};
      if(p.formData&&p.formData.native_filter_id===id&&p.filterState&&'value' in p.filterState)nativeResult={ready:true,value:p.filterState.value};
      if(p.name===id&&typeof p.onChange==='function'&&'value' in p)fallback={ready:true,value:p.value};
      f=f.return;
    }
    return nativeResult||fallback||{ready:false};
  }
  function ensureMsg(){
    var bar=document.querySelector('[data-test="filter-bar"]');if(!bar)return null;
    var n=document.getElementById('hdt-visit-msg');
    if(!n){n=document.createElement('div');n.id='hdt-visit-msg';n.setAttribute('role','status');n.style.cssText='color:#b64236;font-size:12px;line-height:1.4;margin:4px 0';bar.appendChild(n);}
    return n;
  }
  function ensureTip(){
    /* 温和橙色提示条（不拦截提交）：与红色拦截消息分离，避免语义混淆 */
    var bar=document.querySelector('[data-test="filter-bar"]');if(!bar)return null;
    var n=document.getElementById('hdt-span-tip');
    if(!n){n=document.createElement('div');n.id='hdt-span-tip';n.setAttribute('role','status');n.style.cssText='color:#d46b08;font-size:12px;line-height:1.4;margin:4px 0';bar.appendChild(n);}
    return n;
  }
  function softTip(){
    var id=page();
    if(!SOFT_IDS[id])return '';
    var s=dateSpan();
    if(typeof s.days!=='number')return '';
    if(id===59){
      if(s.days<=7)return '';
      var low=draftValue(V1),high=draftValue(V2);
      if(!low.ready||!high.ready)return '';
      var c=classify(low.value,high.value);
      if(!c.ok)return '';
      if(parseInt(c.high,10)-parseInt(c.low,10)+1>20)return SOFT_MSGS[59];
      return '';
    }
    return s.days>31?SOFT_MSGS[id]:'';
  }
  function currentCheck(){
    var id=page(),required=REQUIRED[id];
    if(required){var selected=draftValue(required.id);
      if(!selected.ready)return {ok:false,reason:'查询条件未就绪，请稍候再查询'};
      var value=selected.value;if(Array.isArray(value))value=value.length===1?value[0]:null;
      if(typeof value!=='string'||!value)return {ok:false,reason:'请选择'+required.name};
      if(id===58&&value!=='门诊'&&value!=='住院')return {ok:false,reason:'请选择有效的门诊或住院分支'};
      return {ok:true};
    }
    if(SPAN_LIMIT[id]){
      var s=dateSpan();
      if(s.ready===false)return {ok:false,reason:'日期条件未就绪，请稍候再查询'};
      if(typeof s.days==='number'&&s.days>SPAN_LIMIT[id])return {ok:false,reason:SPAN_MSG};
      return {ok:true};
    }
    if(id!==59)return {ok:true,skip:true};
    /* 59：先拦大跨度，再校验 visit_id */
    var sp=dateSpan();
    if(sp.ready===false)return {ok:false,reason:'日期条件未就绪，请稍候再查询'};
    if(typeof sp.days==='number'&&sp.days>BLOCK31[59])return {ok:false,reason:BLOCK31_MSG};
    var low=draftValue(V1),high=draftValue(V2);
    if(!low.ready||!high.ready)return {ok:false,reason:'就诊次数条件未就绪，请稍候再查询'};
    return classify(low.value,high.value);
  }
  function typingEnter(e){
    if(!e||e.type!=='keydown'||e.key!=='Enter'||!e.target)return false;
    if(e.target.closest&&e.target.closest('[data-test="filter-bar__apply-button"]'))return false;
    var tag=String(e.target.tagName||'').toLowerCase();
    if(tag==='input'||tag==='textarea'||tag==='select')return true;
    return !!(e.target.closest&&(e.target.closest('.ant-select')||e.target.closest('.ant-picker')||e.target.closest('.flatpickr-calendar')));
  }
  function block(e){
    if(!isGuardPage(page()))return;
    if(e.type==='keydown'&&e.key!=='Enter')return;
    if(typingEnter(e))return;
    var onApply=e.target.closest&&e.target.closest('[data-test="filter-bar__apply-button"]');
    var inBar=e.target.closest&&e.target.closest('[data-test="filter-bar"]');
    if(e.type==='click'&&!onApply)return;
    if(e.type==='keydown'&&!onApply&&!inBar)return;
    var result=currentCheck();
    var msg=ensureMsg();
    if(result.ok){if(msg)msg.textContent='';return;}
    if(msg)msg.textContent=result.reason;
    e.preventDefault();e.stopImmediatePropagation();
    api.lastBlock=result.reason;
  }
  function fixWording(node){
    if(!node)return;
    if(node.nodeType===3){if(node.nodeValue&&node.nodeValue.indexOf(OLD)>=0)node.nodeValue=node.nodeValue.split(OLD).join(NEW);return;}
    if(node.nodeType!==1||node.id==='hdt-visit-msg'||node.id==='hdt-span-tip')return;
    ['title','aria-label'].forEach(function(attr){
      if(!node.getAttribute)return;
      var v=node.getAttribute(attr);
      if(v&&v.indexOf(OLD)>=0)node.setAttribute(attr,v.split(OLD).join(NEW));
    });
    Array.prototype.forEach.call(node.childNodes||[],fixWording);
  }
  function surfaces(){
    var nodes=[],bar=document.querySelector('[data-test="filter-bar"]');
    if(bar)nodes.push(bar);
    Array.prototype.forEach.call(document.querySelectorAll('.ant-tooltip-inner,[role="tooltip"]'),function(n){nodes.push(n);});
    return nodes;
  }
  function render(){
    var id=page();
    if(!isGuardPage(id)){
      var old=document.getElementById('hdt-visit-msg');if(old)old.remove();
      var oldTip=document.getElementById('hdt-span-tip');if(oldTip)oldTip.remove();
      return;
    }
    if(id===58||id===59)surfaces().forEach(fixWording);
    var msg=document.getElementById('hdt-visit-msg');if(msg&&msg.textContent&&currentCheck().ok)msg.textContent='';
    /* 软提示：仅在需要时创建节点，空则移除；计算经 softTip()（含 fiber 遍历），
       由 observer 节流兜底，避免 antd 下拉/虚拟列表变更风暴下主线程被 render 饿死 */
    var tipEl=document.getElementById('hdt-span-tip');
    var txt=softTip();
    if(txt){var el=tipEl||ensureTip();if(el)el.textContent=txt;}
    else if(tipEl){tipEl.remove();}
  }
  var lastRenderTs=0;
  api.classify=classify;api.norm=norm;api.currentCheck=currentCheck;api.typingEnter=typingEnter;api.wording={old:OLD,next:NEW};
  api.draftValue=draftValue;api.dateSpan=dateSpan;api.spanLimit=SPAN_LIMIT;api.spanMsg=SPAN_MSG;
  api.block31=BLOCK31;api.block31Msg=BLOCK31_MSG;api.softTip=softTip;api.softMsgs=SOFT_MSGS;
  document.addEventListener('click',block,true);
  document.addEventListener('keydown',block,true);
  /* 节流：antd 下拉/虚拟列表滚动会产生高频变更批，render() 里的 softTip() 含 fiber 遍历，
     不节流会在 59 页 visit_id 下拉交互时把主线程饿死（2026-11-14 实测冻结）。 */
  new MutationObserver(function(){
    var now=Date.now();
    if(now-lastRenderTs<250)return;
    lastRenderTs=now;
    render();
  }).observe(document.body,{childList:true,subtree:true,characterData:true});
  render();
})();
