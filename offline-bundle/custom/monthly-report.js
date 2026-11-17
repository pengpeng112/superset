/* 老 HIS 月工作报表。20261022m12：
   请求开始即作废可交互快照；按每侧请求/AbortSignal及实际响应内容关联代次。
   快速缓存响应不依赖轮询恰好观察到 loading，草稿读取统一日历的真实值。
   查询代次绑定图表 queryController 的 AbortSignal 与本次 chart/data 请求。
   不用点击时刻、完成时刻、两侧空签名或 cache_key 判断成功。
   已完成且签名有效的缓存可以采纳。旧请求晚到不能覆盖新代。
   双空禁止导出；失败、加载、条件不一致和不支持时不保留旧表。 */
(function(){
  'use strict';if(window.hospitalMonthlyReport)return;
  var controller=window.hospitalMonthlyReport={version:'20261022m12'},store,unsubscribe,root,signature='',timer=0,page=0,search='';
  var SIDES={out:{chart:342,label:'门诊'},in:{chart:324,label:'住院'}};
  var FID='NATIVE_FILTER-MONTHNEW1';
  var SNAP=null,STATE='idle',WAVE=null,waveSeq=0,pendingFetches=[],TIMEOUT_MS=120000,waveTimer=0,requestSeq=0,requestEpoch=0;
  var responseMarks=typeof WeakMap==='function'?new WeakMap():null;
  var mz=[['KSDM','科别'],['JGS','机构数'],['TOTAL_NUM','诊疗人次总数'],['JI','门急诊合计'],['MEN_ZHENS','门诊人次数'],['JIZHENS','急诊人次数'],['JIZHEN_SIWANG','其中：死亡人数'],['GUANCHA','观察室收容病人数'],['GUANCHA_SIWANG','其中：死亡人数'],['JIANCHA','健康检查人数']];
  var zy=[['KSDM','科别'],['ORIAL','上月原有人数'],['RUMEN','入院人数'],['ZHUANRU','转入人数'],['CHUYUAN','出院人数总计'],['RECOVER','治愈'],['EFFECT','好转'],['UNTREAT','未愈'],['DIED','死亡'],['OTHER_N','其他'],['WILL_N','自动'],['XFER','转院'],['ZHUANCHU','转出人数'],['CURR','月末现有人数']];
  var style=document.createElement('style');style.id='hospital-monthly-style';
  style.textContent=[
    'html.hm-unified [data-hm-source]{position:absolute!important;left:-100000px!important;width:calc(100% - 32px)!important;visibility:hidden!important;pointer-events:none!important}',
    'html.hm-unified [data-hm-wrapper]{position:absolute!important;left:0!important;width:100%!important;height:0!important;margin:0!important}',
    'html.hm-unified [data-test=grid-content]{height:auto!important}',
    '#hospital-monthly-report{border:1px solid #dce6ef;border-radius:8px;background:#fff;padding:10px 12px;margin-top:4px;color:#243d53}',
    '#hospital-monthly-report .hm-heading{display:flex;align-items:baseline;justify-content:center;gap:16px;flex-wrap:wrap;margin-bottom:8px}',
    '#hospital-monthly-report h2{font-size:18px;color:#173e61;margin:0;text-align:center}',
    '#hospital-monthly-report .hm-period{color:#697f92;font-size:13px}',
    '#hospital-monthly-report .hm-toolbar{display:flex;align-items:center;gap:12px;margin-bottom:8px;flex-wrap:wrap;font-size:14px}',
    '#hospital-monthly-report input{border:1px solid #bccfdf;border-radius:6px;padding:7px 10px;width:240px;font:inherit}',
    '#hospital-monthly-report button{border:1px solid #bfd2e2;border-radius:6px;padding:7px 12px;background:#f4f8fc;color:#205982;font:inherit;cursor:pointer}',
    '#hospital-monthly-report button:disabled{opacity:.45;cursor:default}',
    '#hospital-monthly-report .hm-scroll{overflow:auto;max-height:calc(100vh - 410px);min-height:200px;border:1px solid #cbd9e5}',
    '#hospital-monthly-report table{border-collapse:separate;border-spacing:0;table-layout:fixed;width:3000px;font-size:14px}',
    '#hospital-monthly-report th,#hospital-monthly-report td{border-right:1px solid #dce5ed;border-bottom:1px solid #dce5ed;padding:9px 8px;text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;height:37px;box-sizing:border-box}',
    '#hospital-monthly-report thead{position:sticky;top:0;z-index:2}#hospital-monthly-report th{background:#edf4fa;color:#254c6d;text-align:center;white-space:normal;line-height:1.5}',
    '#hospital-monthly-report th.hm-group{background:#215c8b;color:#fff;font-size:16px;height:38px}',
    '#hospital-monthly-report .hm-dept{width:180px;text-align:left}#hospital-monthly-report td.hm-divider,#hospital-monthly-report th.hm-divider{border-left:3px solid #86a4bf}',
    '#hospital-monthly-report tr:nth-child(even) td{background:#f7fafc}#hospital-monthly-report tr:hover td{background:#edf5fc}',
    '#hospital-monthly-report .hm-footer{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:14px;font-size:13px;color:#6a7e90}',
    '#hospital-monthly-report .hm-footer>div{display:flex;align-items:center;gap:10px;white-space:nowrap}',
    '#hospital-monthly-report .hm-status{padding:26px;text-align:center;color:#657c91}',
    '#hospital-monthly-report .hm-export{margin-left:auto}'
  ].join('\n');document.head.appendChild(style);
  function active(){return /\/superset\/dashboard\/(?:32|month-work-report-new)\/?$/.test(location.pathname)&&!/(?:\?|&)edit=true/.test(location.search);}
  function findStore(){var e=document.querySelector('[data-test=grid-content]');if(!e)return;var k=Object.keys(e).find(function(k){return k.indexOf('__reactFiber')===0;});if(!k)return;var f=e[k];while(f){var p=f.memoizedProps,s=p&&(p.store||(p.value&&p.value.store));if(s&&s.getState)return s;f=f.return;}}
  function el(tag,cls,text){var e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;}
  function value(row,key){var v=row&&row[key];return v===null||v===undefined?'':String(v);}
  function dateValue(row,key){var v=row&&row[key];if(typeof v==='number'||/^\d{10,13}$/.test(String(v))){var n=Number(v);return fmtD(new Date(n*(n>100000000000?1:1000)));}return value(row,key).slice(0,10);}
  function parseD(str){var m=String(str).match(/^(\d{4})-(\d{2})-(\d{2})/);return m?new Date(+m[1],+m[2]-1,+m[3]):null;}
  function dayD(d,n){return new Date(d.getFullYear(),d.getMonth(),d.getDate()+n);}
  function fmtD(d){function z(n){return('0'+n).slice(-2);}return d.getFullYear()+'-'+z(d.getMonth()+1)+'-'+z(d.getDate());}
  function canon(v){
    if(v===null||typeof v!=='object')return JSON.stringify(v);
    if(Array.isArray(v))return '['+v.map(canon).join(',')+']';
    var keys=Object.keys(v).sort();
    return '{'+keys.map(function(k){return JSON.stringify(k)+':'+canon(v[k]);}).join(',')+'}';
  }
  function sigOf(c){
    if(!c||!c.latestQueryFormData||typeof c.latestQueryFormData!=='object')return null;
    var fd=c.latestQueryFormData,bag={};
    ['time_range','extra_form_data','extra_filters','filters','adhoc_filters','url_params'].forEach(function(k){
      var v=fd[k];
      if(v===undefined||v===null)return;
      if(typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).length===0)return;
      bag[k]=v;
    });
    return Object.keys(bag).length?canon(bag):null;
  }
  function readSide(state,side){
    var c=state.charts&&state.charts[SIDES[side].chart];
    if(!c)return {chart:null};
    var resp=c.queriesResponse&&c.queriesResponse[0];
    return {chart:c,status:c.chartStatus||'',resp:resp||null,sig:sigOf(c),
      start:c.chartUpdateStartTime||0,end:c.chartUpdateEndTime||0,controller:c.queryController||null,
      timeRange:(c.latestQueryFormData&&(c.latestQueryFormData.time_range||(c.latestQueryFormData.extra_form_data||{}).time_range))||null};
  }
  function draftValue(state){var ui=window.hospitalDateUI,v=ui&&ui.draftFor&&ui.draftFor(FID);if(v!==undefined)return v;var dm=state.dataMask&&state.dataMask[FID];return dm&&dm.filterState&&dm.filterState.value||null;}
  function terminalOk(live){return live.chart&&(live.status==='success'||live.status==='rendered');}
  function failed(live){if(!live.chart||live.status==='loading'||live.status==='stopped')return false;return live.status==='failed'||!!(live.resp&&live.resp.error);}
  function dataOk(live){return !!(live.resp&&Array.isArray(live.resp.data)&&!live.resp.error);}
  function resetWave(){if(waveTimer)clearTimeout(waveTimer);waveTimer=0;WAVE=null;waveSeq=0;pendingFetches=[];requestEpoch++;}
  function openWave(reason){if(waveTimer)clearTimeout(waveTimer);waveSeq+=1;WAVE={id:waveSeq,reason:reason,t:Date.now(),adopted:false,requested:{out:null,in:null},sides:{out:null,in:null}};waveTimer=setTimeout(schedule,TIMEOUT_MS+10);}
  function latestFetch(signal,side){var hit=null;pendingFetches.forEach(function(p){if(p.signal===signal&&p.side===side)hit=p;});return hit;}
  function bindSide(latch){
    if(!latch)return;
    if(!latch.controller||!latch.controller.signal){if(!latch.tracked)latch.unobserved=true;return;}
    var hit=latch.request||latestFetch(latch.controller.signal,latch.side);
    if(!hit){if(!latch.tracked)latch.unobserved=true;return;}
    latch.tracked=true;latch.unobserved=false;latch.fetchPhase=hit.phase;latch.fetchOk=hit.phase==='ok';
    if(hit.mark)latch.payloadMark=hit.mark;
  }
  function makeLatch(live,side,request){var latch={side:side,request:request||null,start:live.start,controller:live.controller,sig:live.sig,fetchOk:false,tracked:false,unobserved:false,fetchPhase:'',frozenResp:null,timeRange:live.timeRange};bindSide(latch);return latch;}
  function noteFetch(sliceId,signal,phase,mark,request){
    var side=sliceId===342?'out':sliceId===324?'in':null;
    if(!side)return;
    if(request&&request.epoch!==requestEpoch)return request;
    if(phase==='start'){
      request={side:side,signal:signal,phase:phase,mark:null,id:++requestSeq,epoch:requestEpoch};
      pendingFetches.push(request);
      if(!WAVE||WAVE.adopted||WAVE.requested[side])openWave('request');
      WAVE.requested[side]=request;
      STATE='loading';SNAP=null;controller.state='loading';
      if(root)apply({state:'loading',wave:WAVE.id});
    }else{
      request=request||latestFetch(signal,side);
      if(!request)return;
      request.phase=phase;request.mark=mark||null;
    }
    if(pendingFetches.length>40)pendingFetches=pendingFetches.slice(-20);
    if(WAVE){bindSide(WAVE.sides.out);bindSide(WAVE.sides.in);}
    schedule();return request;
  }
  function attach(la,lb){
    [['out',la],['in',lb]].forEach(function(pair){var side=pair[0],live=pair[1],request=WAVE.requested[side];
      if(!WAVE.sides[side]&&request&&live.controller&&live.controller.signal===request.signal)WAVE.sides[side]=makeLatch(live,side,request);
    });
    bindSide(WAVE.sides.out);bindSide(WAVE.sides.in);
  }
  function sideReady(latch,live){
    if(!latch||!live.sig||live.sig!==latch.sig)return false;
    if(latch.controller&&live.controller&&latch.controller!==live.controller)return false;
    if(latch.start&&live.start&&latch.start!==live.start)return false;
    if(!terminalOk(live)||!dataOk(live))return false;
    bindSide(latch);
    if(!latch.tracked&&!WAVE.adopted)return false;
    if(latch.fetchPhase==='abort'||latch.fetchPhase==='error')return false;
    if(latch.tracked&&!latch.fetchOk)return false;
    if(latch.tracked&&(!latch.payloadMark||latch.payloadMark!==responseMark(live.resp)))return 'stale';
    if(latch.frozenResp&&live.resp!==latch.frozenResp)return 'stale';
    return true;
  }
  function pack(live){return {resp:live.resp,sig:live.sig,timeRange:live.timeRange,status:live.status};}
  function judge(la,lb){
    var currentA=WAVE&&(WAVE.adopted||(WAVE.sides.out&&la.controller===WAVE.sides.out.controller));
    var currentB=WAVE&&(WAVE.adopted||(WAVE.sides.in&&lb.controller===WAVE.sides.in.controller));
    if((failed(la)&&currentA)||(failed(lb)&&currentB))return {state:'error',msg:String((la.resp&&la.resp.error)||(lb.resp&&lb.resp.error)||'查询失败').slice(0,140),wave:WAVE&&WAVE.id};
    var inFlight=WAVE&&['out','in'].some(function(side){return WAVE.requested[side]&&WAVE.requested[side].phase==='start';});
    if(inFlight||la.status==='loading'||lb.status==='loading'||la.status==='stopped'||lb.status==='stopped'){
      if(WAVE&&!WAVE.adopted&&Date.now()-WAVE.t>TIMEOUT_MS)return {state:'error',msg:'查询超时，请再次点击“查询”',wave:WAVE.id};
      return {state:'loading',wave:WAVE&&WAVE.id};
    }
    var ra=sideReady(WAVE&&WAVE.sides.out,la),rb=sideReady(WAVE&&WAVE.sides.in,lb);
    if(ra==='stale'||rb==='stale')return {state:'mismatch',msg:'收到与本次查询不匹配的结果，未展示。请重新点击“查询”。',wave:WAVE.id};
    if(!la.sig||!lb.sig||la.sig!==lb.sig)return {state:'mismatch',msg:'两部分查询条件不一致或无法核对，未展示。',wave:WAVE&&WAVE.id};
    if(ra!==true||rb!==true)return {state:'mismatch',msg:'结果未能对应到本次查询，未展示。请重新点击“查询”。',wave:WAVE&&WAVE.id};
    if(WAVE.sides.out)WAVE.sides.out.frozenResp=la.resp;
    if(WAVE.sides.in)WAVE.sides.in.frozenResp=lb.resp;
    var ev={a:pack(la),b:pack(lb),wave:WAVE.id};
    if(!la.resp.data.length&&!lb.resp.data.length){ev.state='empty';return ev;}
    ev.state='success';return ev;
  }
  function observe(state){
    var la=readSide(state,'out'),lb=readSide(state,'in');
    if(!la.chart||!lb.chart)return {state:'unsupported'};
    if(!WAVE){
      if(terminalOk(la)&&terminalOk(lb)&&la.sig&&lb.sig&&la.sig===lb.sig&&dataOk(la)&&dataOk(lb)){
        openWave('adopt-cache');WAVE.adopted=true;
        WAVE.sides.out=makeLatch(la,'out');WAVE.sides.in=makeLatch(lb,'in');
        return judge(la,lb);
      }
      if(la.status==='loading'||lb.status==='loading'){openWave('query');attach(la,lb);return {state:'loading',wave:WAVE.id};}
      if(failed(la)||failed(lb))return {state:'error',msg:String((la.resp&&la.resp.error)||(lb.resp&&lb.resp.error)||'查询失败').slice(0,140)};
      if((terminalOk(la)||terminalOk(lb))&&(!la.sig||!lb.sig))return {state:'mismatch',msg:'查询条件无法核对，未展示结果。'};
      if(terminalOk(la)&&terminalOk(lb)&&(!dataOk(la)||!dataOk(lb)))return {state:'error',msg:'响应结构不合法'};
      return {state:'loading',fresh:true};
    }
    attach(la,lb);
    return judge(la,lb);
  }
  function sliceOf(body){
    try{var obj=typeof body==='string'?JSON.parse(body):null;if(!obj)return null;
      var fd=obj.form_data||obj.formData;if(typeof fd==='string')fd=JSON.parse(fd);
      var id=fd&&(fd.slice_id||fd.sliceId);return typeof id==='string'?+id:id;}catch(e){return null;}
  }
  function markOf(json){try{var result=json&&(json.result||json);var row=Array.isArray(result)?result[0]:result;if(!row||!Array.isArray(row.data))return null;return canon({data:row.data,columns:row.colnames||null,error:row.error||null});}catch(e){return null;}}
  function responseMark(resp){if(responseMarks&&responseMarks.has(resp))return responseMarks.get(resp);var mark=markOf(resp);if(responseMarks)responseMarks.set(resp,mark);return mark;}
  function installFetch(){
    if(!window.fetch||window.fetch.__hmMonthly)return;
    var orig=window.fetch;
    function wrapped(input,init){
      var url='';try{url=typeof input==='string'?input:(input&&input.url)||'';}catch(e){}
      var signal=init&&init.signal,slice=null;
      if(url.indexOf('/api/v1/chart/data')>=0&&init&&init.body&&active())slice=sliceOf(init.body);
      var request=null;if(slice===324||slice===342)request=noteFetch(slice,signal,'start',null);
      var p=orig.apply(this,arguments);
      if(slice!==324&&slice!==342)return p;
      return p.then(function(resp){
        var copy;try{copy=resp.clone();}catch(e){noteFetch(slice,signal,resp.ok?'ok':'error',null,request);return resp;}
        return copy.json().then(function(j){noteFetch(slice,signal,resp.ok?'ok':'error',markOf(j),request);return resp;},function(){noteFetch(slice,signal,resp.ok?'ok':'error',null,request);return resp;});
      },function(err){noteFetch(slice,signal,signal&&signal.aborted?'abort':'error',null,request);throw err;});
    }
    wrapped.__hmMonthly=true;window.fetch=wrapped;
  }
  function ready(){return STATE==='success';}
  function rowsOf(list){var q=search.trim().toLowerCase();return q?list.filter(function(r){return value(r,'KSDM').toLowerCase().indexOf(q)>=0;}):list;}
  function table(){
    if(!root||!SNAP||STATE!=='success')return;
    var list=[rowsOf(SNAP.data[0]),rowsOf(SNAP.data[1])],max=Math.max(list[0].length,list[1].length),pages=Math.max(1,Math.ceil(max/50));
    page=Math.min(Math.max(0,page),pages-1);
    var wrap=root.querySelector('.hm-scroll');while(wrap.firstChild)wrap.removeChild(wrap.firstChild);
    var t=el('table');t.setAttribute('aria-label','月工作报表（新）门诊与住院合并宽表');
    var cg=el('colgroup'),tw=0;mz.concat(zy).forEach(function(c){var w=c[0]==='KSDM'?180:c[0]==='JGS'?70:110,col=el('col');col.style.width=w+'px';tw+=w;cg.appendChild(col);});
    t.style.width=tw+'px';t.appendChild(cg);
    var head=el('thead'),tr=el('tr');
    [mz,zy].forEach(function(cols,i){var th=el('th','hm-group',i?'住院工作量':'门诊工作量');th.colSpan=cols.length;tr.appendChild(th);});head.appendChild(tr);
    tr=el('tr');mz.concat(zy).forEach(function(c,i){var th=el('th',(i===0||i===mz.length?'hm-dept ':'')+(i===mz.length?'hm-divider':''),c[1]);tr.appendChild(th);});head.appendChild(tr);t.appendChild(head);
    var body=el('tbody');
    for(var n=page*50;n<Math.min(max,(page+1)*50);n++){
      tr=el('tr');[mz,zy].forEach(function(cols,side){var row=list[side][n];cols.forEach(function(c,i){var v=value(row,c[0]),td=el('td',(i===0?'hm-dept ':'')+(side===1&&i===0?'hm-divider':''),v);td.title=v;td.setAttribute('data-field',c[0]);td.setAttribute('data-side',side?'inpatient':'outpatient');tr.appendChild(td);});});body.appendChild(tr);
    }
    t.appendChild(body);wrap.appendChild(t);
    root.querySelector('.hm-count').textContent='门诊 '+SNAP.data[0].length+' 行　住院 '+SNAP.data[1].length+' 行';
    root.querySelector('.hm-page').textContent='第 '+(page+1)+' / '+pages+' 页';
    root.querySelector('.hm-prev').disabled=page===0;root.querySelector('.hm-next').disabled=page>=pages-1;
    controller.rows={outpatient:SNAP.data[0].length,inpatient:SNAP.data[1].length};controller.visibleRows=body.children.length;
  }
  function csvLine(v){v=String(v==null?'':v);if(/^[=+@\-]/.test(v)&&!/^[-+]?\d+(\.\d+)?$/.test(v))v="'"+v;return'"'+v.replace(/"/g,'""')+'"';}
  function exportCSV(scope){
    if(!ready()||!SNAP)return;
    var list=(scope==='search')?[rowsOf(SNAP.data[0]),rowsOf(SNAP.data[1])]:SNAP.data;
    var count=Math.max(list[0].length,list[1].length),lines=[];
    lines.push(mz.map(function(c){return'门诊·'+c[1];}).concat(zy.map(function(c){return'住院·'+c[1];})).map(csvLine).join(','));
    for(var i=0;i<count;i++)lines.push(mz.map(function(c){return value(list[0][i],c[0]);}).concat(zy.map(function(c){return value(list[1][i],c[0]);})).map(csvLine).join(','));
    var per=SNAP.period.begin&&SNAP.period.end?SNAP.period.begin+'_'+SNAP.period.end:'期间待核实';
    var blob=new Blob(['\ufeff'+lines.join('\r\n')],{type:'text/csv;charset=utf-8;'}),url=URL.createObjectURL(blob),a=el('a');
    a.href=url;a.download='月工作报表（新）_'+per+'_'+(scope==='search'?'搜索结果':'整表')+'.csv';a.click();
    setTimeout(function(){URL.revokeObjectURL(url);},1000);
    controller.lastExport={scope:scope,rows:count,period:per};
  }
  function create(){
    root=el('section');root.id='hospital-monthly-report';
    var heading=el('div','hm-heading');heading.appendChild(el('h2','','新月工作报表'));heading.appendChild(el('div','hm-period',''));root.appendChild(heading);
    var toolbar=el('div','hm-toolbar'),input=el('input');input.type='search';input.placeholder='按科别搜索（左右独立过滤）';input.setAttribute('aria-label','按科别搜索');
    input.addEventListener('input',function(){if(!ready()){input.value=search;return;}search=input.value;page=0;table();});
    toolbar.appendChild(input);toolbar.appendChild(el('span','hm-count',''));
    var b1=el('button','hm-export','导出整张报表');b1.type='button';b1.title='导出本次成功快照的全部门诊/住院数据（不受搜索与分页影响）';
    b1.addEventListener('click',function(){exportCSV('all');});toolbar.appendChild(b1);
    var b2=el('button','hm-export2','导出当前搜索结果');b2.type='button';b2.title='导出当前搜索命中的两侧独立结果全部行（不仅当前页）';
    b2.addEventListener('click',function(){exportCSV('search');});toolbar.appendChild(b2);
    root.appendChild(toolbar);root.appendChild(el('div','hm-scroll'));
    var foot=el('div','hm-footer');foot.appendChild(el('span','','左右两栏独立排列（不按科室配对）；较短一侧补空位。横向滚动查看全部指标。'));
    var pager=el('div');
    [['hm-prev','上一页',-1],['hm-next','下一页',1]].forEach(function(a){var b=el('button',a[0],a[1]);b.type='button';
      b.addEventListener('click',function(){if(!ready())return;page+=a[2];table();});pager.appendChild(b);
      if(a[2]===-1)pager.appendChild(el('span','hm-page',''));});
    foot.appendChild(pager);root.appendChild(foot);
    document.querySelector('[data-test=grid-content]').appendChild(root);
    controller.exportAll=function(){exportCSV('all');};controller.exportSearch=function(){exportCSV('search');};
    return root;
  }
  var draftNow=null;
  function normRange(v){v=v&&String(v);return(!v||v==='No filter')?'':v;}
  function periodOf(timeRange,begin,end){
    if(begin&&end)return {begin:String(begin).slice(0,10),end:String(end).slice(0,10),source:'response'};
    var tr=String(timeRange||''),dateOnly=tr.match(/^(\d{4}-\d{2}-\d{2}) : (\d{4}-\d{2}-\d{2})$/);
    if(dateOnly){var pd=parseD(dateOnly[2]);return {begin:dateOnly[1],end:pd?fmtD(dayD(pd,-1)):'',source:'applied-date'};}
    var timed=tr.match(/^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) : (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})$/);
    if(timed)return {begin:timed[1],end:timed[2],source:'applied-datetime'};
    return {begin:'',end:'',source:'unknown'};
  }
  function periodText(){
    if(!SNAP)return'';
    var p=SNAP.period,t='统计期间：'+(p.begin&&p.end?p.begin+' 至 '+p.end:'待核实');
    if(normRange(SNAP.appliedDraft)!==normRange(draftNow))return t+'（条件已修改，尚未查询）';
    return t;
  }
  function clearChrome(){
    if(!root)return;
    var scroll=root.querySelector('.hm-scroll');if(scroll){while(scroll.firstChild)scroll.removeChild(scroll.firstChild);}
    var count=root.querySelector('.hm-count');if(count)count.textContent='';
    var pg=root.querySelector('.hm-page');if(pg)pg.textContent='';
    controller.rows=null;controller.visibleRows=0;controller.snapAt=null;
  }
  function setDisabled(ok){
    if(!root)return;
    ['.hm-export','.hm-export2','.hm-prev','.hm-next'].forEach(function(sel){var n=root.querySelector(sel);if(n)n.disabled=!ok;});
    var inp=root.querySelector('input');if(inp)inp.disabled=!ok;
  }
  function apply(ev){
    STATE=ev.state;controller.state=STATE;controller.wave=ev.wave||null;
    if(STATE==='unsupported'){if(root&&root.isConnected)root.remove();root=null;SNAP=null;document.documentElement.classList.remove('hm-unified');controller.rows=null;return;}
    if(!root)return;
    var period=root.querySelector('.hm-period');
    var scroll=root.querySelector('.hm-scroll');
    if(STATE!=='success'){search='';page=0;var inp0=root.querySelector('input');if(inp0)inp0.value='';}
    setDisabled(STATE==='success');
    if(STATE==='loading'){SNAP=null;clearChrome();period.textContent='正在查询…';scroll.textContent='正在查询…';return;}
    if(STATE==='error'){SNAP=null;clearChrome();period.textContent='查询失败'+(ev.msg?'：'+ev.msg:'')+'；请检查条件后重试。';scroll.textContent='查询失败，未展示旧结果。点击“查询”重试。';return;}
    if(STATE==='mismatch'){SNAP=null;clearChrome();period.textContent=ev.msg||'两部分查询条件不一致，未能合并展示；请重新点击“查询”。';scroll.textContent='未展示不能对应到本次查询的结果。';return;}
    var d0=ev.a.resp.data||[],d1=ev.b.resp.data||[];
    var row=d1[0]||d0[0]||{};
    var per=periodOf(ev.a.timeRange,row.STAT_BEGIN?dateValue(row,'STAT_BEGIN'):'',row.STAT_END?dateValue(row,'STAT_END'):'');
    function copyRows(rows){return rows.map(function(r){return Object.assign({},r);});}
    SNAP={data:[copyRows(d0),copyRows(d1)],sig:ev.a.sig,at:Date.now(),wave:ev.wave,period:{begin:per.begin,end:per.end,source:per.source},appliedDraft:normRange(ev.a.timeRange)};
    if(STATE==='empty'){
      setDisabled(false);
      period.textContent='当前条件没有数据'+(SNAP.period.begin?'；已查询期间：'+SNAP.period.begin+' 至 '+SNAP.period.end:'；实际统计期间待核实')+(normRange(SNAP.appliedDraft)!==normRange(draftNow)?'（条件已修改，尚未查询）':'');
      scroll.textContent='该条件下两侧均无数据。';
      root.querySelector('.hm-count').textContent='门诊 0 行　住院 0 行';
      controller.rows={outpatient:0,inpatient:0};controller.visibleRows=0;return;
    }
    table();period.textContent=periodText();controller.snapAt=SNAP.at;
  }
  function render(){
    timer=0;
    if(!active()){document.documentElement.classList.remove('hm-unified');if(unsubscribe){unsubscribe();unsubscribe=null;}if(root&&root.isConnected)root.remove();root=null;signature='';SNAP=null;STATE='idle';controller.state='idle';resetWave();return;}
    var found=findStore();if(!found){if(root&&root.isConnected)root.remove();root=null;SNAP=null;STATE='idle';signature='';controller.state='idle';if(unsubscribe){unsubscribe();unsubscribe=null;}store=null;document.documentElement.classList.remove('hm-unified');if(WAVE)resetWave();return;}
    if(found!==store||!unsubscribe){if(unsubscribe)unsubscribe();store=found;unsubscribe=store.subscribe(schedule);}
    var state=store.getState(),ev=observe(state);
    if(ev.state==='unsupported'){signature='';apply(ev);return;}
    draftNow=draftValue(state);
    var stamp=[ev.state,ev.wave,ev.msg,ev.a&&ev.a.sig,ev.b&&ev.b.sig,draftNow].join('|');
    if(root&&root.isConnected&&signature===stamp&&STATE===ev.state)return;
    if(!root||!root.isConnected)create();
    signature=stamp;
    [324,342].forEach(function(id){var c=document.querySelector('.dashboard-chart-id-'+id),row=c&&c.closest('[data-test=grid-row-background--transparent]');
      if(row){row.setAttribute('data-hm-source','true');row.parentElement.parentElement.setAttribute('data-hm-wrapper','true');}});
    document.documentElement.classList.add('hm-unified');
    apply(ev);
  }
  function schedule(){if(!timer)timer=setTimeout(render,120);}
  installFetch();
  new MutationObserver(schedule).observe(document.body,{childList:true,subtree:true});
  window.addEventListener('popstate',schedule);schedule();
  controller.observe=observe;controller.noteFetch=noteFetch;controller.resetWave=resetWave;
  controller.periodOf=periodOf;controller.sigOf=sigOf;controller.rowsOf=rowsOf;controller.dateValue=dateValue;
  controller.markOf=markOf;
})();
