/* 登录页版式。左上角标志由主题 brandLogoUrl 提供，这里只排登录页。
   20261025g：新增全局明亮主题初始化——superset-theme-mode 为 system/未设置时首次置为 default（明亮）
   （hh-theme-init 标记首次初始化；用户此后明确选择 light/dark/system 均不再覆盖）。 */
(function () {
  /* 全局明亮主题初始化。
     前端主题构造在 head 同步阶段即读取 localStorage（此刻为空），挂载时会按其捕获值回写
     'system'；因此除立即写一次外，还需在挂载后（DOM 就绪 + 延时）修正被回写的值，
     并仅在被修正时自动刷新一次让渲染态与存储一致。hh-theme-init=1 表示初始化已完成，
     此后用户明确选择的 light/dark/system 均不再覆盖。 */
  function readMode(store) {
    try { return store.getItem("superset-theme-mode"); } catch (e) { return null; }
  }
  function initLightTheme() {
    try {
      var store = window.localStorage;
      var done = store.getItem("hh-theme-init") === "1";
      if (!done) {
        var mode = readMode(store);
        if (mode === null || mode === undefined || mode === "") store.setItem("superset-theme-mode", "default");
      }
    } catch (e) { /* 存储不可用时交由原生前端默认行为 */ }
  }
  function finalizeLightTheme(isFinal) {
    try {
      var store = window.localStorage;
      if (store.getItem("hh-theme-init") === "1") return;
      var mode = readMode(store);
      if (mode === "system" || mode === null || mode === undefined || mode === "") {
        /* 应用挂载已按构造期捕获值回写 system；此刻修正为 light 并刷新一次让渲染态一致 */
        store.setItem("superset-theme-mode", "default");
        store.setItem("hh-theme-init", "1");
        var ss = window.sessionStorage;
        if (!ss.getItem("hh-theme-reloaded")) {
          ss.setItem("hh-theme-reloaded", "1");
          window.location.reload();
        }
      } else if (isFinal) {
        /* 稳定的 light/dark（含用户既有明确选择）：仅标记完成，不改值 */
        store.setItem("hh-theme-init", "1");
      }
    } catch (e) { try { window.localStorage.setItem("hh-theme-init", "1"); } catch (e2) {} }
  }
  initLightTheme();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      setTimeout(function () { finalizeLightTheme(false); }, 350);
    });
  } else {
    setTimeout(function () { finalizeLightTheme(false); }, 350);
  }
  window.addEventListener("load", function () {
    setTimeout(function () { finalizeLightTheme(false); }, 900);
    setTimeout(function () { finalizeLightTheme(true); }, 1800);
  });

  var HOSPITAL = "山东省第二人民医院";
  var LOGO = "/custom/logo.png?v=20261005d";
  var LOCKUP = "/custom/logo-bar.png?v=20261005d";

  function setFavicon() {
    var link = document.querySelector('link[rel="icon"]');
    if (!link) {
      link = document.createElement("link");
      link.rel = "icon";
      document.head.appendChild(link);
    }
    link.type = "image/png";
    link.href = LOGO;
  }

  function isLoginPage() {
    return location.pathname.indexOf("/login") === 0;
  }

  function tagTopbar() {
    var imgs = document.querySelectorAll("img");
    for (var i = 0; i < imgs.length; i++) {
      var img = imgs[i];
      if (img.closest("#hospital-hero")) continue;
      var src = img.getAttribute("src") || "";
      if (src.indexOf("logo") === -1) continue;
      if (src.indexOf("superset-logo") !== -1) {
        img.src = LOCKUP;
      }
      img.style.height = "42px";
      img.style.width = "auto";
      img.style.maxWidth = "none";
      var node = img;
      for (var k = 0; k < 8 && node && node !== document.body; k++) {
        var rect = node.getBoundingClientRect();
        if (rect.top >= 0 && rect.top < 12 && rect.height >= 48 && rect.height <= 96 && rect.width > window.innerWidth * 0.5) {
          node.classList.add("hospital-topbar");
          return;
        }
        node = node.parentElement;
      }
    }
  }

  function inject() {
    if (document.getElementById("hospital-hero")) return;
    var form = document.querySelector('[data-test="login-form"]');
    if (!form) return;
    document.documentElement.classList.add("hospital-login");
    tagTopbar();
    var bar = document.querySelector(".hospital-topbar");
    var barBottom = bar ? Math.max(56, Math.round(bar.getBoundingClientRect().bottom)) : 64;
    document.documentElement.style.setProperty("--hh-bar", barBottom + "px");

    var title = form.querySelector(".ant-card-head-title");
    if (title) {
      title.textContent = "欢迎登录";
      if (!document.getElementById("hospital-system-name")) {
        var sys = document.createElement("div");
        sys.id = "hospital-system-name";
        sys.textContent = "统计报表系统";
        title.insertAdjacentElement("afterend", sys);
      }
    }

    var hint = form.querySelector(".ant-typography-secondary, .ant-typography");
    if (hint && hint.textContent && hint.textContent.indexOf("密码") !== -1) {
      hint.textContent = "请使用工号和密码登录";
    }

    var hero = document.createElement("aside");
    hero.id = "hospital-hero";
    hero.innerHTML =
      '<img src="' + LOGO + '" alt="" />' +
      "<h1>" + HOSPITAL + "</h1>" +
      '<p class="hh-system">统计报表系统</p>' +
      '<div class="hh-line"></div>' +
      '<p class="hh-slogan">数据服务临床 · 智慧驱动管理</p>';
    document.body.appendChild(hero);

    if (!document.getElementById("hospital-login-style")) {
      var st = document.createElement("style");
      st.id = "hospital-login-style";
      st.textContent = [
        "html.hospital-login,html.hospital-login body{background:#f4f7fb!important;margin:0}",
        ".hospital-topbar{background:#fff!important;border-bottom:3px solid #0e4c86!important;box-shadow:0 1px 0 rgba(14,76,134,.04)!important;z-index:30!important}",
        ".hospital-topbar img{height:42px!important;width:auto!important;max-width:none!important}",
        "#hospital-hero{position:fixed;left:0;top:var(--hh-bar,64px);bottom:0;width:42%;z-index:2;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:36px 40px 48px;box-sizing:border-box;color:#fff;pointer-events:none;",
        "background:radial-gradient(circle at 20% 18%,rgba(255,255,255,.12),transparent 28%),radial-gradient(circle at 82% 88%,rgba(212,168,75,.20),transparent 26%),linear-gradient(165deg,#08284a 0%,#0e4c86 55%,#0a3a68 100%)}",
        "#hospital-hero img{width:120px;height:120px;border-radius:50%;background:#fff;padding:8px;box-shadow:0 14px 36px rgba(0,0,0,.22)}",
        "#hospital-hero h1{margin:28px 0 0;font-size:32px;font-weight:700;letter-spacing:2px;line-height:1.4;text-align:center}",
        "#hospital-hero .hh-system{margin:12px 0 0;font-size:16px;letter-spacing:8px;color:rgba(255,255,255,.9)}",
        "#hospital-hero .hh-line{width:64px;height:3px;margin:22px 0 14px;border-radius:2px;background:#d4a84b}",
        "#hospital-hero .hh-slogan{margin:0;font-size:14px;letter-spacing:2px;color:rgba(255,255,255,.78)}",
        'html.hospital-login [data-test="login-form"]{margin:0!important;width:100%!important;height:calc(100vh - var(--hh-bar,64px))!important;min-height:520px!important;background:transparent!important;justify-content:flex-end!important;padding:24px 7% 32px 46%!important;box-sizing:border-box!important}',
        'html.hospital-login [data-test="login-form"] .ant-card{width:100%;max-width:440px;border:none;border-radius:20px;box-shadow:0 22px 60px rgba(12,48,90,.14);overflow:hidden}',
        'html.hospital-login [data-test="login-form"] .ant-card-head{border-bottom:none;min-height:72px;padding:18px 24px 0}',
        'html.hospital-login [data-test="login-form"] .ant-card-head-title{text-align:center;font-size:24px;font-weight:700;color:#0e3f6e;letter-spacing:3px}',
        "#hospital-system-name{text-align:center;margin-top:6px;font-size:15px;letter-spacing:4px;color:#0e4c86;font-weight:600}",
        'html.hospital-login [data-test="login-form"] .ant-card-body{padding:8px 32px 28px}',
        "html.hospital-login .ant-form-item-label>label{color:#35516c!important;font-weight:600;font-size:14px}",
        "html.hospital-login .ant-input-affix-wrapper{border-radius:10px;padding-top:10px;padding-bottom:10px;border-color:#d7e3ef;background:#fbfcfe}",
        "html.hospital-login .ant-input-affix-wrapper:hover,html.hospital-login .ant-input-affix-wrapper-focused{border-color:#0e4c86!important;box-shadow:0 0 0 2px rgba(14,76,134,.12)}",
        'html.hospital-login [data-test="login-button"]{height:46px;border-radius:10px;font-size:16px;letter-spacing:6px;background:#0e4c86;border-color:#0e4c86;margin-top:8px}',
        'html.hospital-login [data-test="login-button"]:hover{background:#0b3e70!important;border-color:#0b3e70!important}',
        "@media (max-width:960px){#hospital-hero{position:relative;top:auto;width:100%;min-height:240px;padding:28px 16px}",
        "#hospital-hero h1{font-size:24px}",
        'html.hospital-login [data-test="login-form"]{height:auto!important;min-height:0!important;padding:16px!important;justify-content:center!important}}'
      ].join("");
      document.head.appendChild(st);
    }
  }

  function injectShell() {
    if (document.getElementById("hospital-shell-style")) return;
    var st = document.createElement("style");
    st.id = "hospital-shell-style";
    st.textContent = [
      "#hospital-home-hint{margin:16px 24px 0;padding:14px 18px;border-radius:12px;background:#fff;border:1px solid #d7e3ef;border-left:4px solid #0e4c86;color:#35516c;font-size:14px;line-height:1.7;box-shadow:0 8px 24px rgba(12,48,90,.05)}",
      "#hospital-home-hint strong{display:block;color:#0e3f6e;font-size:16px;letter-spacing:1px;margin-bottom:2px}"
    ].join("");
    document.head.appendChild(st);
  }

  function placeHint() {
    var existing = document.getElementById("hospital-home-hint");
    var home = !isLoginPage() && (location.pathname === "/" || location.pathname.indexOf("/superset/welcome") === 0);
    if (!home) {
      if (existing) existing.remove();
      return;
    }
    if (existing) return;
    injectShell();
    var hint = document.createElement("div");
    hint.id = "hospital-home-hint";
    hint.innerHTML = "<strong>统计报表系统</strong><span>分配给您的报表在左侧「看板」。看板是空的，表示这个账号还没有开通报表，请联系信息科。</span>";
    var header = document.querySelector(".hospital-topbar");
    if (header && header.parentElement) header.insertAdjacentElement("afterend", hint);
  }

  setFavicon();
  if (document.title.indexOf(HOSPITAL) === -1) document.title = HOSPITAL;
  var pushState = history.pushState;
  history.pushState = function () {
    pushState.apply(history, arguments);
    setTimeout(function () { tagTopbar(); placeHint(); }, 300);
  };
  window.addEventListener("popstate", function () {
    setTimeout(function () { tagTopbar(); placeHint(); }, 300);
  });
  if (!isLoginPage()) {
    var n = 0;
    var watch = setInterval(function () {
      n += 1;
      tagTopbar();
      placeHint();
      if ((document.querySelector(".hospital-topbar") && document.getElementById("hospital-home-hint")) || n > 30) clearInterval(watch);
    }, 200);
    return;
  }

  var tries = 0;
  var timer = setInterval(function () {
    tries += 1;
    if (document.querySelector('[data-test="login-form"]')) {
      clearInterval(timer);
      inject();
      var n2 = 0;
      var again = setInterval(function () {
        n2 += 1;
        tagTopbar();
        if (n2 > 20) clearInterval(again);
      }, 300);
    } else if (tries > 60) {
      clearInterval(timer);
    }
  }, 200);
})();
