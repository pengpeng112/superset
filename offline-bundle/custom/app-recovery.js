/* 20261022b：修复旧登录链接中丢端口的同站回跳；失效分块最多重载一次。 */
(function(){
  'use strict';
  if(window.hospitalAppRecovery)return;
  var api=window.hospitalAppRecovery={version:'20261022b',recoveries:0};
  var storageKey='hospital-app-recovery:'+api.version,attempted=false;
  function normalizedLoginUrl(href){
    try{var url=new URL(href);if(!/^\/login\/?$/.test(url.pathname))return null;
      var raw=url.searchParams.get('next');if(!raw)return null;var target=new URL(raw,url.href);
      if(target.hostname!==url.hostname||target.protocol!==url.protocol||target.port||!url.port||target.username||target.password)return null;
      if(!/^\/(?:superset|dashboard|chart|explore)(?:\/|$)/.test(target.pathname))return null;
      url.searchParams.set('next',target.pathname+target.search+target.hash);return url.href;
    }catch(e){return null;}
  }
  api.normalizedLoginUrl=normalizedLoginUrl;
  var fixed=normalizedLoginUrl(location.href);if(fixed){api.loginTargetFixed=true;location.replace(fixed);return;}
  function canRetry(){
    if(attempted)return false;
    try{if(sessionStorage.getItem(storageKey))return false;sessionStorage.setItem(storageKey,'1');}catch(e){}
    attempted=true;return true;
  }
  function failedChunk(message){return /ChunkLoadError|Loading (?:CSS )?chunk [\w-]+ failed|Failed to fetch dynamically imported module/i.test(String(message||''));}
  function recover(message){
    if(!failedChunk(message)||!canRetry())return;
    api.recoveries++;
    /* 不删除 cookies/localStorage、缓存查询结果或 native_filters_key，不改变权限及统计条件。 */
    setTimeout(function(){location.reload();},0);
  }
  window.addEventListener('error',function(e){recover((e.error&&e.error.name)+' '+(e.error&&e.error.message)+' '+(e.message||''));});
  window.addEventListener('unhandledrejection',function(e){var reason=e.reason;recover(reason&&(reason.message||String(reason)));});
  api.isChunkFailure=failedChunk;
})();
