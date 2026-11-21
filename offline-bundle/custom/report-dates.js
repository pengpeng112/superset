/* 离线日历直接选择。20261119d19（BI-ENHANCE 批）：
   CONTRACT/isReportKey/BI_APPLY_PAGES 三处同步补入第 4 个 BI 驾驶舱 75 与别名 bi-nursing-bed
   （契约 gran:'range',quick:'month' 与 72/74 一致），防通过别名访问时查询按钮死锁，日历/快选/查询
   按钮行为与既有驾驶舱完全一致。
   20261111d18（FINAL-CLOSEOUT 收尾）：
   CONTRACT/isReportKey 补 BI 驾驶舱 3 个 slug 别名（bi-overview→72、bi-outpatient-flow→73、
   bi-surgery-quality→74，契约与数字 ID 完全一致），render() 编辑态判断改按 AGENTS.md 约定读
   dashboardState.editMode（经 home-ui isEditing，不能只看 ?edit=true 查询串），BI_APPLY_PAGES
   同步补别名，防通过别名访问驾驶舱时查询按钮死锁。
   20261104d13：
   契约与 isReportKey 接入抗菌办查询页 61–70，并补 mr-discharge-death-detail 别名（指向看板 2 同一契约）。
   20261022d12：
   病案明细从服务器时钟计算当前月末，不再锁死九月；与获准扩展的 SQL 窗口一致。
   病案明细及后续原生日期筛选统一日历范围外观，别名按真实看板 ID 取契约。
   整月同时核年份；元数据旧请求不能清掉新请求；桥接退化不反复创建控件。
   去掉统一 365 天上限，不再从筛选说明猜上下界；未知跨度不加限制。
   元数据按页单飞、发起时计入、含首次最多 5 次，离页作废。
   桥接与日历都成功才隐藏原生；失败或编辑/离页销毁自定义层并恢复原生。
   datetime 两端仍是 single，秒值原样透传；纯日期只在提交时把结束日换成次日零点。 */
(function(){
  'use strict';
  if(window.hospitalDateUI||!window.flatpickr)return;
  var api=window.hospitalDateUI={version:'20261119d19'};
  var states=[],metadata={},metaTries={},metaFlight={},metaEpoch=0,pending=0,lastKey=null;
  /* 只登记已核对的粒度。maxSpanDays / bounds 不写在这里：契约跨度仍是 unknown，不能猜。 */
  var CONTRACT={
    2:{gran:'range',quick:'month',filterId:'NATIVE_FILTER-DISCHARGE-TIME',minDate:'2026-01-01',serverMonthEnd:true,source:'dataset4 current month SQL window'},
    'mr-discharge-death-detail':{gran:'range',quick:'month',filterId:'NATIVE_FILTER-DISCHARGE-TIME',minDate:'2026-01-01',serverMonthEnd:true,source:'dataset4 current month SQL window'},
    32:{gran:'range',quick:'month'},'month-work-report-new':{gran:'range',quick:'month'},
    35:{gran:'range',quick:'month'},36:{gran:'range',quick:'day'},37:{gran:'range',quick:'week'},
    39:{gran:'range',quick:'week'},40:{gran:'datetime'},
    41:{gran:'range',quick:'month'},42:{gran:'range',quick:'day'},43:{gran:'range',quick:'day'},
    44:{gran:'range',quick:'month'},45:{gran:'range',quick:'month'},46:{gran:'range',quick:'month'},
    47:{gran:'range',quick:'week'},48:{gran:'range',quick:'week'},49:{gran:'range',quick:'week'},
    50:{gran:'fullmonth',quick:'month'},51:{gran:'fullmonth',quick:'month'},52:{gran:'fullmonth',quick:'month'},
    53:{gran:'sameday',quick:'day'},54:{gran:'sameday',quick:'day'},55:{gran:'sameday',quick:'day'},
    56:{gran:'sameday',quick:'day'},57:{gran:'sameday',quick:'day'},
    58:{gran:'range',quick:'week'},59:{gran:'range',quick:'week'},60:{gran:'range',quick:'month'},
    /* 抗菌办查询页（20261104d13）：61 门急诊处方、62 住院检验、63 季度消耗、64 住院患者、
       65 住院医嘱、66 微生物、67 检查、68 诊断、69 手术记录、70 生命体征 */
    61:{gran:'range',quick:'month'},72:{gran:'range',quick:'month'},73:{gran:'sameday',quick:'day'},74:{gran:'range',quick:'month'},62:{gran:'range',quick:'day'},63:{gran:'range',quick:'month'},
    /* BI 驾驶舱 slug 别名（20261111d18，20261119d19 补第 4 个）：契约与对应数字 ID 完全一致 */
    'bi-overview':{gran:'range',quick:'month'},'bi-outpatient-flow':{gran:'sameday',quick:'day'},'bi-surgery-quality':{gran:'range',quick:'month'},
    75:{gran:'range',quick:'month'},'bi-nursing-bed':{gran:'range',quick:'month'},
    64:{gran:'range',quick:'month'},65:{gran:'range',quick:'day'},66:{gran:'range',quick:'month'},
    67:{gran:'range',quick:'month'},68:{gran:'range',quick:'month'},69:{gran:'range',quick:'month'},
    70:{gran:'range',quick:'day'}
  };
  var style=document.createElement('style');style.id='hospital-calendar-style';
  style.textContent=[
    '.hdt-picker{display:flex;align-items:center;gap:6px;position:relative;min-height:36px;font-size:14px;max-width:100%}',
    '.hdt-picker input{box-sizing:border-box;border:1px solid #bbcddd;border-radius:7px;background:#fff;color:#183e60;height:36px;padding:7px 28px 7px 10px;cursor:pointer;font:inherit;min-width:0;width:100%}',
    '.hdt-input-wrap{position:relative;flex:1;min-width:0}.hdt-input-wrap:after{content:"▦";position:absolute;right:9px;top:7px;pointer-events:none;color:#6688a5;font-size:18px}',
    '.hdt-picker button{border:1px solid #dce6ef;border-radius:6px;color:#235a89;background:#f7faff;padding:6px 9px;height:32px;white-space:nowrap;cursor:pointer;font-size:13px}',
    '.hdt-picker button:hover{background:#eaf3fc;border-color:#87afd1}.hdt-picker button:disabled{opacity:.4;cursor:default;background:#f2f5f8}',
    '.hdt-picker .hdt-reset{border:0;background:transparent;padding:4px;color:#7a8997}',
    '.hdt-error{position:absolute;left:0;top:38px;color:#b64236;font-size:12px;background:#fff;z-index:5;white-space:nowrap}',
    '.hdt-error.hdt-info{color:#57708a}',
    '.hdt-fallback{display:block;color:#8a4b32;font-size:12px;line-height:1.4;margin-top:4px}',
    '.hdt-meta-retry{margin-left:8px}',
    '.hdt-picker[data-mode=datetime]{width:530px}.hdt-picker[data-mode=range]{width:410px}',
    '.hdt-filter-item .ant-form-item-control-input-content{overflow:visible!important}.hdt-filter-item{max-width:100%}',
    '.flatpickr-calendar{z-index:11000!important;border-radius:10px!important;box-shadow:0 10px 36px rgba(18,62,99,.18)!important;font-family:"Microsoft YaHei",sans-serif!important}',
    '.flatpickr-day.selected,.flatpickr-day.startRange,.flatpickr-day.endRange{background:#215e91!important;border-color:#215e91!important}',
    '.flatpickr-day.inRange{background:#eaf3fc!important;border-color:#eaf3fc!important;box-shadow:-5px 0 0 #eaf3fc,5px 0 0 #eaf3fc!important}',
    '.flatpickr-current-month{font-size:16px!important}',
    '@media(max-width:900px){.hdt-picker[data-mode=datetime]{width:440px}.hdt-picker[data-mode=range]{width:360px}}'
  ].join('\n');document.head.appendChild(style);
  function bridge(el){if(!el)return null;var k=Object.keys(el).find(function(k){return k.indexOf('__reactFiber')===0;});if(!k)return null;var f=el[k],r;while(f){var p=f.memoizedProps||{};if(p.name===el.getAttribute('name')&&typeof p.onChange==='function'&&'value'in p)r=p;f=f.return;}return r||null;}
  function fmt(d,time){function z(n){return('0'+n).slice(-2);}return d.getFullYear()+'-'+z(d.getMonth()+1)+'-'+z(d.getDate())+(time?' '+z(d.getHours())+':'+z(d.getMinutes())+':'+z(d.getSeconds()):'');}
  function day(d,n){return new Date(d.getFullYear(),d.getMonth(),d.getDate()+n);}
  function parse(s){var m=String(s).match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?/);return m?new Date(+m[1],+m[2]-1,+m[3],+(m[4]||0),+(m[5]||0),+(m[6]||0)):null;}
  function key(){var m=location.pathname.match(/\/dashboard\/([^/]+)/);return m?m[1]:'';}
  function contract(f){var md=metadata[key()],c=CONTRACT[key()]||CONTRACT[md&&md.__dashboardId];if(c&&c.filterId&&f&&c.filterId!==f.id)c=null;return c||(f&&f.filterType==='filter_time'?{gran:'range',quick:'month',generic:true}:null);}
  function isReportKey(k){if(k==='month-work-report-new'||k==='mr-discharge-death-detail'||k==='bi-overview'||k==='bi-outpatient-flow'||k==='bi-surgery-quality'||k==='bi-nursing-bed')return true;var n=+k;return n===2||n===32||(n>=35&&n<=70)||(n>=72&&n<=75);}
  function info(t){var md=metadata[key()];return md&&!md.__failed&&(md.native_filter_configuration||[]).find(function(f){return f.id===t.getAttribute('name')&&f.filterType==='filter_time';});}
  function clearFlight(id,doAbort,expected){var f=metaFlight[id];if(!f||(expected&&f!==expected))return;if(f.timer)clearTimeout(f.timer);if(doAbort&&f.ac){try{f.ac.abort();}catch(e){}}if(metaFlight[id]===f)delete metaFlight[id];}
  function abortFlights(){Object.keys(metaFlight).forEach(function(id){clearFlight(id,true);});}
  /* 发起时计入。已有在途或退避定时器时不再加一次。含首次最多 5 次。 */
  function claim(id){
    if(metaFlight[id])return false;
    var used=metaTries[id]||0;
    if(used>=5){metadata[id]={'__failed':true};return false;}
    metaTries[id]=used+1;return true;
  }
  function load(){var id=key();if(!id)return;
    if(metadata[id]&&!metadata[id].__failed)return;
    if(!claim(id))return;
    var epoch=metaEpoch,ac=typeof AbortController==='function'?new AbortController():null,serverDate=null;
    var flight={epoch:epoch,ac:ac,timer:null,kind:'fetch'};
    var deadline=new Promise(function(resolve,reject){flight.timer=setTimeout(function(){if(ac)ac.abort();reject(Error('Metadata timeout'));},8000);});
    metaFlight[id]=flight;
    var opts={credentials:'same-origin'};if(ac)opts.signal=ac.signal;
    Promise.race([fetch('/api/v1/dashboard/'+encodeURIComponent(id),opts),deadline])
      .then(function(r){if(!r.ok)throw Error('Metadata');serverDate=r.headers&&r.headers.get('Date');return r.json();})
      .then(function(j){
        if(epoch!==metaEpoch||key()!==id||metaFlight[id]!==flight){clearFlight(id,false,flight);return;}
        var md=j&&j.result&&j.result.json_metadata;
        md=typeof md==='string'?JSON.parse(md):(md||{});
        if(md.native_filter_configuration===undefined)md.native_filter_configuration=[];
        if(!Array.isArray(md.native_filter_configuration))throw Error('Metadata shape');
        md.__dashboardId=j.result.id;var serverMillis=Date.parse(serverDate);if(isFinite(serverMillis))md.__serverOffset=serverMillis-Date.now();metadata[id]=md;
        clearFlight(id,false,flight);schedule();
      })
      .catch(function(){
        if(metaFlight[id]!==flight)return;
        clearFlight(id,false,flight);
        if(epoch!==metaEpoch||key()!==id)return;
        if((metaTries[id]||0)>=5){metadata[id]={'__failed':true};schedule();return;}
        var wait=(metaTries[id]||1)*1500;
        var rt=setTimeout(function(){if(metaFlight[id]&&metaFlight[id].kind==='wait')delete metaFlight[id];if(epoch===metaEpoch&&key()===id)load();},wait);
        metaFlight[id]={epoch:epoch,timer:rt,kind:'wait'};
      });
  }
  function retryMeta(){var id=key();if(!id)return;metaEpoch++;clearFlight(id,true);metaTries[id]=0;delete metadata[id];load();schedule();}
  function error(s,v){if(s.error.textContent!==v)s.error.textContent=v;if(v)s.error.classList.remove('hdt-info');}
  function note(s,v){if(s.error.textContent!==v)s.error.textContent=v;s.error.classList.add('hdt-info');}
  function boundsOf(s){
    var c=s.contract,md=metadata[key()];
    if(c&&c.serverMonthEnd){
      if(!md||typeof md.__serverOffset!=='number')return null;
      /* 医院时区 Asia/Shanghai；HTTP Date 的 UTC 时刻转为该时区的自然月。 */
      var now=new Date(Date.now()+md.__serverOffset+8*3600000),last=new Date(Date.UTC(now.getUTCFullYear(),now.getUTCMonth()+1,0));
      var upper=last.getUTCFullYear()+'-'+('0'+(last.getUTCMonth()+1)).slice(-2)+'-'+('0'+last.getUTCDate()).slice(-2);
      return [c.minDate,upper];
    }
    return s.bounds||null;
  }
  function refreshBounds(s){var bounds=boundsOf(s);if(!bounds||String(bounds)===String(s.bounds))return;s.bounds=bounds;s.pickers.forEach(function(p){p.set('minDate',bounds[0]);p.set('maxDate',bounds[1]);});}
  function violate(s,a,b){
    var c=s.contract;
    if(!a||!b||!isFinite(a.getTime())||!isFinite(b.getTime()))return'请选择有效的开始和结束日期';
    if(s.mode==='datetime'){if(b.getTime()<=a.getTime())return'结束时间必须晚于开始时间';}
    else if(b<a)return'结束日期不能早于开始日期';
    if(c&&c.gran==='fullmonth'){
      if(a.getDate()!==1)return'本报表须选同一个完整自然月：开始应为当月1日';
      if(a.getFullYear()!==b.getFullYear()||a.getMonth()!==b.getMonth()||day(b,1).getDate()!==1)return'本报表须选同一个完整自然月（当月1日至月末）';
    }
    if(c&&c.gran==='sameday'&&a.getTime()!==b.getTime())return'本报表仅支持同一天：两端日期应相同';
    if(typeof (c&&c.maxSpanDays)==='number'&&s.mode!=='datetime'&&((b-a)/86400000>c.maxSpanDays))return'所选范围超过本页已核实上限';
    if(c&&c.minDate&&a<parse(c.minDate))return'开始日期不能早于'+c.minDate;
    var bounds=boundsOf(s);if(bounds&&(a<parse(bounds[0])||b>parse(bounds[1])))return'请选择可查询期间内的日期（'+bounds[0]+' 至 '+bounds[1]+'）';
    return null;
  }
  function nativeValue(mode,a,b){if(!a||!b)return'No filter';return mode==='datetime'?fmt(a,true)+' : '+fmt(b,true):fmt(a,false)+' : '+fmt(day(b,1),false);}
  function parseRange(v){var parts=String(v||'').split(/\s+:\s+/);if(parts.length!==2)return null;var a=parse(parts[0]),b=parse(parts[1]);return a&&b?{a:a,b:b}:null;}
  function restoreNative(s){if(!s.native)return;s.native.style.display=s.oldStyle?s.oldStyle.display:'';if(s.native.parentElement){s.native.parentElement.style.width=s.oldStyle?s.oldStyle.width:'';s.native.parentElement.style.height=s.oldStyle?s.oldStyle.height:'';}}
  function destroyPickers(s){s.pickers.forEach(function(p){try{p.destroy();}catch(e){}});s.pickers=[];}
  function showFallback(s,msg){
    var host=s.native&&s.native.parentElement;if(!host)return;
    var fallbackId='hdt-fallback-'+s.trigger.getAttribute('name');
    s.fallback=document.getElementById(fallbackId)||s.fallback;
    if(!s.fallback||!s.fallback.isConnected){s.fallback=document.createElement('div');s.fallback.id=fallbackId;s.fallback.className='hdt-fallback';s.fallback.setAttribute('data-date-fallback','true');s.fallback.setAttribute('role','status');host.appendChild(s.fallback);}
    if(s.fallback.textContent!==msg)s.fallback.textContent=msg;
  }
  function degrade(s,msg){destroyPickers(s);if(s.panel&&s.panel.parentNode)s.panel.remove();restoreNative(s);showFallback(s,msg||'日期控件未就绪，已恢复系统原生日期入口');states=states.filter(function(x){return x!==s;});}
  function emit(s,a,b){
    var p=bridge(s.trigger);
    if(!p){degrade(s,'日期控件未就绪，已恢复系统原生日期入口');return;}
    if(a&&b){var why=violate(s,a,b);if(why){s.valid=false;error(s,why);return;}}
    var v=nativeValue(s.mode,a,b);
    s.valid=true;s.lastValue=v;s.complete=a&&b?[new Date(a),new Date(b)]:[];error(s,'');
    if(a&&b)note(s,'已选 '+fmt(a,s.mode==='datetime')+' 至 '+fmt(b,s.mode==='datetime')+(s.mode==='datetime'?'':'（含结束日）')+'，点击“查询”查看');
    p.onChange(v);schedule();
  }
  function display(s,a,b){refreshBounds(s);if(s.mode==='datetime'){s.pickers[0].setDate(a,false);s.pickers[1].setDate(b,false);}else s.pickers[0].setDate(s.mode==='range'?[a,b]:a,false);}
  function choose(s,a,b){display(s,a,b);emit(s,a,b);}
  function sync(s,v){if(s.lastValue===v||s.pickers.some(function(p){return p.isOpen;}))return;s.lastValue=v;
    var pair=parseRange(v);s.valid=true;error(s,'');s.hint='';
    if(pair){var bIncl=s.mode==='datetime'?pair.b:day(pair.b,-1);s.complete=[pair.a,bIncl];display(s,pair.a,bIncl);}
    else{s.complete=[];s.pickers.forEach(function(p){p.clear(false);});s.input.title=v&&v!=='No filter'?'当前条件：'+v:s.input.placeholder;}}
  function make(t,f){
    var native=t.parentElement,panel=document.createElement('div'),c=contract(f);
    if(!c)return null;
    if(!bridge(t)){showFallback({native:native,trigger:t},'日期控件未就绪，已保留系统原生日期入口');return null;}
    var oldFallback=document.getElementById('hdt-fallback-'+t.getAttribute('name'));if(oldFallback)oldFallback.remove();
    var current=bridge(t),timedGeneric=c.generic&&current&&/\d{2}:\d{2}:\d{2}/.test(String(current.value||''));
    var m=c.gran==='datetime'||timedGeneric?'datetime':'range',fid=t.getAttribute('name')||'date';
    panel.className='hdt-picker';panel.setAttribute('data-mode',m);panel.setAttribute('data-filter-id',fid);
    function input(label,placeholder){var w=document.createElement('span');w.className='hdt-input-wrap';var e=document.createElement('input');e.type='text';e.setAttribute('aria-label',label);e.placeholder=placeholder;w.appendChild(e);panel.appendChild(w);return e;}
    var first=input(f.name||'开始',m==='datetime'?'开始时间':'开始日期 至 结束日期');
    var status=document.createElement('span');status.className='hdt-error';status.id='hdt-msg-'+fid;status.setAttribute('role','status');panel.appendChild(status);
    first.setAttribute('aria-describedby',status.id);
    var s={trigger:t,native:native,panel:panel,input:first,error:status,mode:m,pickers:[],valid:true,lastValue:null,complete:[],contract:c,bounds:c.bounds||null,hint:'',fallback:null,
      oldStyle:{display:native.style.display,width:native.parentElement.style.width,height:native.parentElement.style.height}};
    s.bounds=boundsOf(s);
    try{native.parentElement.insertBefore(panel,native);}catch(e){return null;}
    function config(){var o={locale:flatpickr.l10ns.zh,disableMobile:true,allowInput:false,defaultHour:0,defaultMinute:0,dateFormat:m==='datetime'?'Y-m-d H:i:S':'Y-m-d',ariaDateFormat:'Y年m月d日',position:'below left',showMonths:1,onOpen:function(){refreshBounds(s);}};if(c.minDate)o.minDate=c.minDate;if(s.bounds){o.minDate=s.bounds[0];o.maxDate=s.bounds[1];}return o;}
    try{
      var opt=config();
      if(m==='range'){opt.mode='range';opt.showMonths=innerWidth<1100?1:2;opt.onChange=function(ds){s.valid=ds.length!==1;error(s,ds.length===1?'再点击结束日期':'');if(ds.length===2)emit(s,day(ds[0],0),day(ds[1],0));};}
      else{opt.mode='single';opt.enableTime=true;opt.enableSeconds=true;opt.time_24hr=true;opt.minuteIncrement=1;opt.onChange=function(){var a=s.pickers[0].selectedDates[0],b=s.pickers[1]&&s.pickers[1].selectedDates[0];s.valid=!!a&&!!b;if(a&&b)emit(s,a,b);};}
      opt.onClose=function(ds){if(s.mode==='range'&&ds.length===1){s.pickers[0].setDate(s.complete.length?[s.complete[0],s.complete[1]]:[],false);s.valid=true;error(s,'');}};
      s.pickers.push(flatpickr(first,opt));
      if(m==='datetime'){var sep=document.createElement('span');sep.textContent='至';panel.appendChild(sep);var second=input('结束时间','结束时间');second.setAttribute('aria-describedby',status.id);var c2=config();c2.enableTime=true;c2.enableSeconds=true;c2.time_24hr=true;c2.minuteIncrement=1;c2.mode='single';c2.onChange=opt.onChange;s.pickers.push(flatpickr(second,c2));}
    }catch(e){destroyPickers(s);if(panel.parentNode)panel.remove();showFallback(s,'日期控件未就绪，已恢复系统原生日期入口');return null;}
    function button(text,fn,cls){var b=document.createElement('button');b.type='button';b.textContent=text;if(cls)b.className=cls;b.addEventListener('click',fn);panel.appendChild(b);return b;}
    function inBounds(a,b2){return !violate(s,a,b2);}
    var q=m==='datetime'?null:c.quick;
    function quickBtn(text,getRange){var now=getRange(),ok=inBounds(now[0],now[1]);var btn=button(text,function(){if(btn.disabled)return;var pair=getRange();if(!inBounds(pair[0],pair[1]))return;choose(s,pair[0],pair[1]);},null);
      if(!ok){btn.disabled=true;btn.title='超出已核实可查询期间';}return btn;}
    if(q==='month'){
      quickBtn('上月',function(){var n=new Date();return [new Date(n.getFullYear(),n.getMonth()-1,1),new Date(n.getFullYear(),n.getMonth(),0)];});
      quickBtn('本月',function(){var n=new Date();return [new Date(n.getFullYear(),n.getMonth(),1),new Date(n.getFullYear(),n.getMonth()+1,0)];});
    }else if(q==='day'){
      quickBtn('昨天',function(){var n=new Date();return [day(n,-1),day(n,-1)];});
      quickBtn('今天',function(){var n=new Date();return [day(n,0),day(n,0)];});
    }else if(q==='week'){
      quickBtn('近7天',function(){var n=new Date();return [day(n,-6),day(n,0)];});
      quickBtn('本月',function(){var n=new Date();return [new Date(n.getFullYear(),n.getMonth(),1),day(n,0)];});
    }
    function clearedNote(){var k=key();return k==='58'||k==='59'?'已清除：未选日期时，原 SQL 只查询当天减 7 天的那一天':'已清除：下次查询使用报表默认期间';}
    var reset=button('×',function(){s.pickers.forEach(function(p){p.clear(false);});s.hint='';emit(s,null,null);note(s,clearedNote());},'hdt-reset');
    reset.title='恢复报表默认日期';reset.setAttribute('aria-label','恢复默认日期');
    if(!bridge(t)){destroyPickers(s);panel.remove();showFallback(s,'日期控件未就绪，已恢复系统原生日期入口');return null;}
    native.style.display='none';native.parentElement.style.width='auto';native.parentElement.style.height='auto';
    var item=panel.closest('.ant-form-item');if(item)item.classList.add('hdt-filter-item');
    states.push(s);var p=bridge(t);if(p)sync(s,p.value);return s;
  }
  function teardown(){
    states.slice().forEach(function(s){destroyPickers(s);if(s.panel&&s.panel.parentNode)s.panel.remove();restoreNative(s);if(s.fallback&&s.fallback.parentNode)s.fallback.remove();});
    states=[];
    Array.prototype.forEach.call(document.querySelectorAll('.hdt-fallback[data-date-fallback]'),function(n){n.remove();});
    var noteEl=document.getElementById('hdt-uncontracted');if(noteEl)noteEl.remove();
  }
  function metaRetryButton(){
    var bar=document.querySelector('[data-test="filter-bar"]');if(!bar)return;
    var old=document.getElementById('hdt-meta-retry');
    var id=key(),failed=id&&metadata[id]&&metadata[id].__failed;
    if(!failed){if(old)old.remove();return;}
    if(old)return;
    var b=document.createElement('button');b.type='button';b.id='hdt-meta-retry';b.className='hdt-meta-retry';b.textContent='重新加载日期配置';
    b.addEventListener('click',function(){retryMeta();});bar.appendChild(b);
  }
  function uncontractedNote(){
    if(!isReportKey(key())||contract())return;
    var bar=document.querySelector('[data-test="filter-bar"]');if(!bar||document.getElementById('hdt-uncontracted'))return;
    var n=document.createElement('div');n.id='hdt-uncontracted';n.className='hdt-fallback';n.setAttribute('role','status');
    n.textContent='本页未配置日期契约，仍使用系统日期入口。';bar.appendChild(n);
  }
  function render(){pending=0;
    var id=key(),onDash=/\/superset\/dashboard\//.test(location.pathname),editing=/(?:\?|&)edit=true/.test(location.search)||!!(window.hospitalHomeUI&&window.hospitalHomeUI.isEditing&&window.hospitalHomeUI.isEditing()),lifecycle=id+'|'+editing;
    if(lifecycle!==lastKey){lastKey=lifecycle;metaEpoch++;abortFlights();teardown();}
    if(!onDash||editing){teardown();return;}
    load();metaRetryButton();
    states=states.filter(function(s){if(!s.trigger.isConnected){destroyPickers(s);if(s.panel&&s.panel.isConnected)s.panel.remove();restoreNative(s);return false;}return true;});
    Array.prototype.forEach.call(document.querySelectorAll('[data-test="time-range-trigger"][name]'),function(t){
      var f=info(t);if(!f)return;
      var s=states.find(function(x){return x.trigger===t;});
      if(s&&!bridge(t)){degrade(s,'日期控件未就绪，已恢复系统原生日期入口');return;}
      if(!s)s=make(t,f);
      if(!s)return;
      var p=bridge(t);if(p)sync(s,p.value);
    });
  }
  /* BI 驾驶舱（72-74，20261107d16）：本构建多图看板首载 applied dataMask 为空，
     原生「查询」按钮恒 disabled（前端缺陷死锁）。此处仅解锁按钮外观与点击，
     点击仍走原生 onClick(onApply) 真实应用；非法选择仍被 blockSubmit 拦截。
     注意：不得挂在 render()（MutationObserver 驱动）里——会在挂载期放大成
     变更风暴饿死图表网格（d15 教训）；改用独立低频轮询。 */
  var BI_APPLY_PAGES={72:1,73:1,74:1,75:1,'bi-overview':1,'bi-outpatient-flow':1,'bi-surgery-quality':1,'bi-nursing-bed':1};
  function biBarOnApply(){
    var b=document.querySelector('[data-test="filter-bar__apply-button"]');if(!b)return null;
    var k=Object.keys(b).find(function(k){return k.indexOf('__reactFiber')===0;});if(!k)return null;
    var f=b[k];
    while(f){var p=f.memoizedProps||{};
      if(p.hasOwnProperty('isApplyDisabled')&&typeof p.onApply==='function')return p.onApply;
      f=f.return;}
    return null;
  }
  function biApplyUnlock(){
    if(!BI_APPLY_PAGES[key()])return;
    var b=document.querySelector('[data-test="filter-bar__apply-button"]');
    if(!b)return;
    if(!b.getAttribute('data-hh-apply-wired')){
      b.setAttribute('data-hh-apply-wired','1');
      b.addEventListener('click',function(){
        /* antd 对 disabled 期按钮不挂 onClick；此处直调 FilterBar 的 onApply 原函数 */
        try{var fn=biBarOnApply();if(fn)fn();}catch(e){}
      });
    }
    if(b.disabled){try{b.disabled=false;b.classList.remove('ant-btn-disabled');}catch(e){}}
  }
  setInterval(function(){try{biApplyUnlock();}catch(e){}},800);
  function schedule(){if(!pending)pending=setTimeout(render,100);}
  function blockSubmit(e){if(states.some(function(s){return s.trigger.isConnected&&!s.valid;})){e.preventDefault();e.stopImmediatePropagation();}}
  new MutationObserver(schedule).observe(document.body,{childList:true,subtree:true});
  window.addEventListener('popstate',schedule);
  document.addEventListener('click',function(e){if(e.target.closest&&e.target.closest('[data-test="filter-bar__apply-button"]'))blockSubmit(e);},true);
  document.addEventListener('keydown',function(e){if(e.key!=='Enter'||!e.target.closest||!e.target.closest('[data-test="filter-bar"]'))return;blockSubmit(e);},true);
  api.violate=function(spec){return violate({mode:spec.mode||'range',contract:spec.contract||null,bounds:spec.bounds||null},spec.a,spec.b);};
  api.nativeValue=nativeValue;api.parseRange=parseRange;api.loadMeta=load;api.retryMeta=retryMeta;api.renderNow=render;
  api.debug=function(){return{tries:Object.assign({},metaTries),flights:Object.keys(metaFlight),epoch:metaEpoch,failed:!!(metadata[key()]&&metadata[key()].__failed)};};
  api.contractFor=function(k){return CONTRACT[k]||null;};
  api.draftFor=function(fid){var s=states.find(function(x){return x.trigger.isConnected&&x.trigger.getAttribute('name')===fid;});return s?s.lastValue:undefined;};
  schedule();
})();
