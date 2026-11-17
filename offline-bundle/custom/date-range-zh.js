/* 出院日期筛选：调用原控件回调，保持看板“应用”流程与统计口径。 */
(function(){
  'use strict';
  if(window.hospitalDateUI)return;
  function clearChildren(el){while(el.firstChild)el.removeChild(el.firstChild);}
  var FILTER='NATIVE_FILTER-DISCHARGE-TIME',editor=null;
  function propsOf(el){
    var key=Object.keys(el).find(function(k){return k.startsWith('__reactFiber');}),f=el[key],result;
    while(f){var p=f.memoizedProps||{};if(p.name===FILTER && typeof p.onChange==='function' && 'value' in p)result=p;f=f.return;}
    return result;
  }
  function date(value){
    if(!/^\d{4}-\d{2}-\d{2}$/.test(value))return null;
    var parts=value.split('-').map(Number),d=new Date(parts[0],parts[1]-1,parts[2]);
    return d.getFullYear()===parts[0] && d.getMonth()===parts[1]-1 && d.getDate()===parts[2] ? d : null;
  }
  function format(d){return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');}
  function shift(value,days){var d=date(value);d.setDate(d.getDate()+days);return format(d);}
  function update(state){
    var start=state.start.value,end=state.end.value;
    if(!start||!end){state.status.textContent='请选择开始、结束日期，再点击看板“应用”。';return;}
    if(!date(start)||!date(end)||start>end){state.status.textContent='结束日期不能早于开始日期。';return;}
    if(state.min && (start<state.min || end>state.max)){state.status.textContent='请选择可查询期间内的日期。';return;}
    var bridge=propsOf(state.trigger);if(!bridge){state.status.textContent='日期控件未就绪，请刷新页面重试。';return;}
    var range=start+' : '+shift(end,1);state.lastValue=range;
    bridge.onChange(range);
    state.status.textContent='已选 '+start+' 至 '+end+'（含结束当天），点击看板“应用”。';
  }
  function sync(state,value){
    if(state.lastValue===value)return;state.lastValue=value;
    var match=String(value||'').match(/^(\d{4}-\d{2}-\d{2})(?:T00:00:00)?\s*:\s*(\d{4}-\d{2}-\d{2})(?:T00:00:00)?$/);
    if(match && date(match[1]) && date(match[2])){state.start.value=match[1];state.end.value=shift(match[2],-1);state.status.textContent='当前日期：'+state.start.value+' 至 '+state.end.value+'（含结束当天）。';}
    else {state.start.value='';state.end.value='';state.status.textContent=value && value!=='No filter' ? '当前筛选：'+value+'。可改选开始、结束日期。' : '请选择开始、结束日期，再点击看板“应用”。';}
  }
  function buttons(state){
    var box=state.panel.querySelector('.hd-shortcuts');clearChildren(box);
    var anchor=state.max || format(new Date()),d=date(anchor);
    var first=new Date(d.getFullYear(),d.getMonth(),1),previousStart=new Date(d.getFullYear(),d.getMonth()-1,1),previousEnd=new Date(d.getFullYear(),d.getMonth(),0);
    var periods=[['近7天',shift(anchor,-6),anchor],['近30天',shift(anchor,-29),anchor],
      [state.max?'最新月':'本月',format(first),anchor],['上一月',format(previousStart),format(previousEnd)]];
    if(state.min)periods.push(['全部期间',state.min,state.max]);
    periods.forEach(function(period){
      if(state.min && period[2]<state.min)return;
      var button=document.createElement('button');button.type='button';button.textContent=period[0];
      button.addEventListener('click',function(){state.start.value=state.min && period[1]<state.min ? state.min : period[1];state.end.value=period[2];update(state);});box.appendChild(button);
    });
  }
  function render(){
    var trigger=document.querySelector('[data-test="time-range-trigger"][name="'+FILTER+'"]');
    if(!trigger){if(editor && !editor.trigger.isConnected){editor.panel.remove();editor=null;}return;}
    if(editor && editor.trigger===trigger){var current=propsOf(trigger);if(current)sync(editor,current.value);return;}
    var bridge=propsOf(trigger);if(!bridge)return;
    var native=trigger.parentElement,panel=document.createElement('section');panel.className='hospital-date-range';panel.setAttribute('aria-label','出院日期范围');
    panel.innerHTML='<label>开始日期<input type="date" lang="zh-CN" aria-label="出院开始日期"></label><label>结束日期<input type="date" lang="zh-CN" aria-label="出院结束日期"></label><div class="hd-shortcuts"></div><p class="hd-period"></p><p class="hd-status" role="status"></p>';
    native.parentElement.insertBefore(panel,native);native.style.display='none';
    native.parentElement.style.height='auto';native.parentElement.style.width='100%';
    var bar=panel.parentElement;while(bar && !bar.querySelector('[data-test=filter-bar__apply-button]'))bar=bar.parentElement;
    if(bar && bar!==document.body && bar!==document.documentElement && getComputedStyle(bar).display==='flex' && getComputedStyle(bar).flexDirection==='row'){
      panel.classList.add('hospital-date-horizontal');bar.classList.add('hospital-horizontal-filters');
      var item=panel.closest('.ant-form-item');if(item)item.classList.add('hospital-date-filter-item');
      var select=bar.querySelector('.ant-select'),fields=panel.parentElement;
      while(select && fields && fields!==bar && !fields.contains(select))fields=fields.parentElement;
      if(select && fields && getComputedStyle(fields).display==='flex' && getComputedStyle(fields).flexDirection==='row'){
        fields.classList.add('hospital-filter-fields');
        var control=select;while(control.parentElement && control.parentElement!==fields)control=control.parentElement;
        if(control.parentElement===fields)control.classList.add('hospital-filter-compact-control');
      }
      var apply=bar.querySelector('[data-test=filter-bar__apply-button]');
      if(apply)apply.parentElement.classList.add('hospital-filter-actions');
    }
    var state={trigger:trigger,panel:panel,start:panel.querySelector('[aria-label="出院开始日期"]'),end:panel.querySelector('[aria-label="出院结束日期"]'),status:panel.querySelector('.hd-status'),lastValue:null,min:null,max:null};
    editor=state;sync(state,bridge.value);buttons(state);
    state.start.addEventListener('change',function(){update(state);});state.end.addEventListener('change',function(){update(state);});
    // 从当前看板已有说明读取已接入期间；不扩大数据查询范围或修改看板配置。
    var match=location.pathname.match(/\/dashboard\/([^/]+)/);
    if(match)fetch('/api/v1/dashboard/'+encodeURIComponent(match[1])).then(function(r){if(!r.ok)throw Error('Metadata');return r.json();}).then(function(body){
      if(!panel.isConnected)return;var meta=body.result.json_metadata;meta=typeof meta==='string'?JSON.parse(meta):meta;
      var filter=(meta.native_filter_configuration||[]).find(function(f){return f.id===FILTER;});
      var bounds=filter && String(filter.description||'').match(/(\d{4}-\d{2}-\d{2})\s*至\s*(\d{4}-\d{2}-\d{2})/);
      if(bounds && date(bounds[1]) && date(bounds[2])){
        state.min=bounds[1];state.max=bounds[2];state.start.min=state.end.min=state.min;state.start.max=state.end.max=state.max;
        panel.querySelector('.hd-period').textContent='可查询期间：'+state.min+' 至 '+state.max+'；快捷范围截至 '+state.max+'。';buttons(state);
      }
    }).catch(function(){/* 元数据不可用时仍可手动选择日期。 */});
  }
  var style=document.createElement('style');
  style.textContent='.hospital-date-range{padding:8px 0;min-width:180px}.hospital-date-range>label{display:flex;flex-direction:column;margin-bottom:10px;color:#35516c;font-size:13px}.hospital-date-range input{width:100%;box-sizing:border-box;border:1px solid #a8bdcf;border-radius:6px;padding:7px 8px;background:#fff;color:#193a58}.hd-shortcuts{display:flex;flex-wrap:wrap}.hospital-date-range>label input{margin-top:5px}.hd-shortcuts button{margin:0 6px 6px 0;padding:5px 8px;border:1px solid #d7e3ef;border-radius:5px;background:#f2f6fa;color:#0e4c86;cursor:pointer;font-size:12px}.hd-period,.hd-status{margin:8px 0 0;color:#637b91;font-size:12px;line-height:1.6;white-space:normal}';
  style.textContent+='.hospital-date-horizontal{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);column-gap:12px;width:420px;max-width:100%;padding:0}.hospital-date-horizontal>label{margin-bottom:8px}.hospital-date-horizontal .hd-shortcuts,.hospital-date-horizontal .hd-period,.hospital-date-horizontal .hd-status{grid-column:1 / -1}.hospital-date-horizontal .hd-period,.hospital-date-horizontal .hd-status{margin:0;line-height:1.5}.hospital-date-horizontal .hd-shortcuts{margin-top:0}.hospital-horizontal-filters,.hospital-filter-fields{align-items:flex-start!important;flex-wrap:wrap!important}.hospital-horizontal-filters .hospital-date-filter-item{flex-shrink:0}.hospital-date-filter-item .ant-form-item-row{align-items:flex-start!important}.hospital-date-filter-item .ant-form-item-label{padding-top:24px!important}.hospital-filter-compact-control,.hospital-filter-actions{padding-top:24px}.hospital-horizontal-filters>.ant-form{align-items:flex-start!important;flex-wrap:wrap!important}@media(max-width:700px){.hospital-date-horizontal{width:100%;min-width:240px}}';
  function start(){document.head.appendChild(style);render();new MutationObserver(function(){requestAnimationFrame(render);}).observe(document,{childList:true,subtree:true});}
  if(document.head)start();else document.addEventListener('DOMContentLoaded',start);
  document.addEventListener('click',function(event){
    if(!editor || !editor.panel.isConnected || !event.target.closest('[data-test="filter-bar__apply-button"]'))return;
    var startValue=editor.start.value,endValue=editor.end.value;
    if((startValue||endValue) && (!date(startValue)||!date(endValue)||startValue>endValue || editor.min && (startValue<editor.min || endValue>editor.max))){
      event.preventDefault();event.stopImmediatePropagation();editor.status.textContent='请先选择有效的开始、结束日期。';
    }
  },true);
})();
