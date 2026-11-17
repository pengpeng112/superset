# Superset 6.1.x 生产配置（P3-S4，真实值；机密经 .env 环境变量注入）
import sys

import oracledb

# D7+Thick：数据中心 Oracle 为 11.2.0.4（实测 2026-10-04），低于 Thin 的 12.1 门槛，
# 必须 Thick 模式（Instant Client 19.25 已装入镜像 /opt/oracle/instantclient）；
# SA1.4 下还需 module mapping（oracle:// 连接串）
if oracledb.is_thin_mode():
    try:
        oracledb.init_oracle_client(lib_dir="/opt/oracle/instantclient")
    except Exception as _e:  # 已初始化时忽略（幂等）
        pass
oracledb.version = "8.3.0"
sys.modules["cx_Oracle"] = oracledb

import os
from datetime import timedelta

from celery.schedules import crontab

SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]
DATA_DIR = "/app/superset_home"
SQLALCHEMY_DATABASE_URI = (
    "postgresql+psycopg2://superset:"
    + os.environ["POSTGRES_PASSWORD"]
    + "@postgres:5432/superset"
)

from flask_appbuilder.security.manager import AUTH_DB

AUTH_TYPE = AUTH_DB
AUTH_USER_REGISTRATION = False  # 仅 ODS 同步过的工号存在；SSO 接入后也只认证不注册

FEATURE_FLAGS = {
    "EMBEDDED_SUPERSET": True,
    "EMBEDDED_SUPERSET_ONLY": False,
    "ALERT_REPORTS": True,
    "ENABLE_TEMPLATE_PROCESSING": True,
    "DASHBOARD_RBAC": True,
    "PLAYWRIGHT_REPORTS_AND_THUMBNAILS": True,
}

CACHE_CONFIG = {"CACHE_TYPE": "RedisCache", "CACHE_REDIS_URL": "redis://redis:6379/0", "CACHE_DEFAULT_TIMEOUT": 86400}
DATA_CACHE_CONFIG = {"CACHE_TYPE": "RedisCache", "CACHE_REDIS_URL": "redis://redis:6379/1"}
FILTER_STATE_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_URL": "redis://redis:6379/2",
    "CACHE_DEFAULT_TIMEOUT": int(timedelta(days=1).total_seconds()),  # SETEX 需整数；浮点致 Redis ResponseError（2026-10-12 修复）
}
EXPLORE_FORM_DATA_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_URL": "redis://redis:6379/2",
    "CACHE_DEFAULT_TIMEOUT": int(timedelta(days=1).total_seconds()),  # SETEX 需整数；浮点致 Redis ResponseError（2026-10-12 修复）
}

CELERY_CONFIG = {
    "broker_url": "redis://redis:6379/3",
    "result_backend": "redis://redis:6379/4",
    "imports": ("superset.sql_lab", "superset.tasks.scheduler"),
    "beat_schedule": {
        "reports.scheduler": {
            "task": "reports.scheduler",
            "schedule": crontab(minute="*", hour="*"),
        }
    },
}

WEBDRIVER_BASEURL = "http://superset-web:8088/"
WEBDRIVER_BASEURL_USER_FRIENDLY = "http://10.10.8.73:8180/"

ROW_LIMIT = 50000
SQL_MAX_ROW = 100000
TABLE_VIZ_MAX_ROW_SERVER = 500000
DISPLAY_MAX_ROW = 10000
DEFAULT_SQLLAB_LIMIT = 1000
SQLLAB_TIMEOUT = 120

ENABLE_PROXY_FIX = True
PROXY_FIX_X_FOR = 1
PROXY_FIX_X_PROTO = 1
PROXY_FIX_X_HOST = 1

TALISMAN_ENABLED = True
# frame-ancestors：嵌入集成启动前不追加门户来源（H2 暂不启动）
SESSION_COOKIE_SECURE = False  # 试点期 HTTP；HTTPS 里程碑后改 True
WTF_CSRF_ENABLED = True

GUEST_TOKEN_JWT_SECRET = os.environ["GUEST_TOKEN_JWT_SECRET"]
GUEST_TOKEN_JWT_ALGO = "HS256"

# SMTP：信息科提供后取消注释并重启 beat 与 worker
# SMTP_HOST = "<内网邮件服务器>"
# SMTP_PORT = 25
# SMTP_STARTTLS = False
# SMTP_DEFAULT_FROM = "superset@hospital.local"

SUPERSET_LOG_LEVEL = "INFO"

# 界面默认语言：简体中文（用户可在 Settings->Language 个人切换）
BABEL_DEFAULT_LOCALE = "zh"

# 启用界面语言选择（含简体中文；翻译覆盖度见 v2 论断 14）
LANGUAGES = {
    "en": {"flag": "us", "name": "英文"},
    "zh": {"flag": "cn", "name": "中文"},
}

# 系统显示名称（浏览器标题/登录页）
APP_NAME = "山东省第二人民医院"
LOGO_URI = "/custom/logo.png?v=20261005d"

# --- hospital brand ---
# 左上角标志走主题 brandLogoUrl（APP_ICON），不是 LOGO_URI。
APP_ICON = "/custom/logo-bar.png?v=20261005d"
LOGO_TARGET_PATH = "/"

_HOSPITAL_TOKEN = {
    "brandAppName": APP_NAME,
    "brandLogoAlt": "山东省第二人民医院",
    "brandLogoUrl": "/custom/logo-bar.png?v=20261005d",
    "brandLogoMargin": "6px 0",
    "brandLogoHref": "/",
    "brandLogoHeight": "42px",
    "brandSpinnerUrl": None,
    "brandSpinnerSvg": None,
    "colorPrimary": "#0e4c86",
    "colorLink": "#0e4c86",
    "colorError": "#e04355",
    "colorWarning": "#fcc700",
    "colorSuccess": "#5ac189",
    "colorInfo": "#66bcfe",
    "fontUrls": [],
    "fontFamily": "'Microsoft YaHei', 'PingFang SC', 'Noto Sans SC', Inter, Helvetica, Arial, sans-serif",
    "fontFamilyCode": "'IBM Plex Mono', 'Courier New', monospace",
    "transitionTiming": 0.3,
    "brandIconMaxWidth": 360,
    "fontSizeXS": "8",
    "fontSizeXXL": "28",
    "fontWeightNormal": "400",
    "fontWeightLight": "300",
    "fontWeightStrong": "500",
    "fontWeightBold": "700",
    "colorEditorSelection": "#fff5cf",
}
THEME_DEFAULT = {"token": dict(_HOSPITAL_TOKEN), "algorithm": "default"}
_DARK_TOKEN = dict(_HOSPITAL_TOKEN)
_DARK_TOKEN["brandLogoUrl"] = "/custom/logo-bar-light.png?v=20261005d"
_DARK_TOKEN["colorEditorSelection"] = "#5c4d1a"
THEME_DARK = {"token": _DARK_TOKEN, "algorithm": "dark"}
