/* 医院内网旧浏览器样式兼容。必须在 Superset 资源之前同步加载。 */
(function () {
  'use strict';
  if (window.hospitalBrowserCompat || (window.CSS && CSS.supports('selector(:where(*))') && CSS.supports('inset-inline-start', '0px'))) return;
  window.hospitalBrowserCompat = { active: true };
  var supportsWhere = window.CSS && CSS.supports('selector(:where(*))');
  var physical = {
    'inset-inline-start':'left','inset-inline-end':'right','inset-block-start':'top','inset-block-end':'bottom',
    'margin-inline-start':'margin-left','margin-inline-end':'margin-right','margin-block-start':'margin-top','margin-block-end':'margin-bottom',
    'padding-inline-start':'padding-left','padding-inline-end':'padding-right','padding-block-start':'padding-top','padding-block-end':'padding-bottom',
    'border-inline-start':'border-left','border-inline-end':'border-right','border-block-start':'border-top','border-block-end':'border-bottom',
    'inline-size':'width','block-size':'height','min-inline-size':'min-width','max-inline-size':'max-width','min-block-size':'min-height','max-block-size':'max-height'
  };
  function parts(value) {
    return value.match(/(?:\([^)]*\)|[^\s()])+\s*/g).map(function(x){return x.trim();});
  }
  function convert(css) {
    // Ant Design 的哈希选择器只包含一个类名；等效于官方 high hashPriority 回退。
    if(!supportsWhere) {
      css = css.replace(/:where\((\.[\w-]+)\)/g, '$1');
      // 哈希选择器回退会提高 Ant Design 的优先级；同步补偿应用样式，
      // 防止组件默认的 flex、宽度等覆盖 Superset 导航与筛选框布局。
      css = css.replace(/([^{}]+)(?=\{)/g,function(selector){
        return selector.replace(/(\.superset-[\w-]+)(?:\1)*/g,'$1$1');
      });
    }
    css = css.replace(/(^|[;{])\s*([\w-]+)\s*:\s*([^;{}]+)(?=[;}])/g, function(all, prefix, key, value) {
      var important=/\s*!important\s*$/.test(value)?' !important':'';
      value=value.replace(/\s*!important\s*$/,'').trim();
      if(physical[key]) return prefix+physical[key]+':'+value+important;
      var border=key.match(/^border-(inline|block)-(start|end)-(width|style|color)$/);
      if(border) return prefix+'border-'+(border[1]==='inline'?(border[2]==='start'?'left':'right'):(border[2]==='start'?'top':'bottom'))+'-'+border[3]+':'+value+important;
      var shorthand=key.match(/^(inset|margin|padding|border)-(inline|block)$/);
      if(key==='inset'||shorthand) {
        var tokens=parts(value),props;
        if(key==='inset') {props=['top','right','bottom','left'];tokens=[tokens[0],tokens[1]||tokens[0],tokens[2]||tokens[0],tokens[3]||tokens[1]||tokens[0]];}
        else {var stem=shorthand[1]==='inset'?'':shorthand[1]+'-';props=shorthand[2]==='inline'?[stem+'left',stem+'right']:[stem+'top',stem+'bottom'];if(shorthand[1]==='border')tokens=[value,value];else tokens=[tokens[0],tokens[1]||tokens[0]];}
        return prefix+props.map(function(p,i){return p+':'+tokens[i]+important;}).join(';');
      }
      if((key==='text-align' || key==='float') && /^(start|end)$/.test(value))return prefix+key+':'+(value==='start'?'left':'right')+important;
      return all;
    });
    return css;
  }
  // Emotion 等动态样式使用 insertRule；转换在浏览器解析之前完成。
  var insert = CSSStyleSheet.prototype.insertRule;
  CSSStyleSheet.prototype.insertRule = function(rule,index){return insert.call(this,convert(String(rule)),index===undefined?0:index);};
  function fixStyle(el) {
    if(el.tagName!=='STYLE' || !el.textContent)return;
    var original=el.textContent,converted=convert(original);
    if(original!==converted)el.textContent=converted;
  }
  new MutationObserver(function(records){records.forEach(function(record){
    if(record.target.nodeType===3)fixStyle(record.target.parentElement);
    else if(record.target.tagName==='STYLE')fixStyle(record.target);
    Array.prototype.forEach.call(record.addedNodes,function(el){if(el.nodeType===1){fixStyle(el);Array.prototype.forEach.call(el.querySelectorAll('style'),fixStyle);}});
  });}).observe(document,{childList:true,subtree:true,characterData:true});
  window.hospitalBrowserCompat.convertCss=convert;
})();
