# 本地开发配置（P1）：与生产附录 B 同构，差异处已标注
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
AUTH_USER_REGISTRATION = False

FEATURE_FLAGS = {
    "EMBEDDED_SUPERSET": False,            # 本地不开（生产开）
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
WEBDRIVER_BASEURL_USER_FRIENDLY = "http://127.0.0.1:8088"

ROW_LIMIT = 50000
SQL_MAX_ROW = 100000
TABLE_VIZ_MAX_ROW_SERVER = 500000
DISPLAY_MAX_ROW = 10000
DEFAULT_SQLLAB_LIMIT = 1000
SQLLAB_TIMEOUT = 120

TALISMAN_ENABLED = False                 # 本地关（生产开）
SESSION_COOKIE_SECURE = False
WTF_CSRF_ENABLED = True

GUEST_TOKEN_JWT_SECRET = os.environ.get("GUEST_TOKEN_JWT_SECRET", "dev-only-not-secret")

SUPERSET_LOG_LEVEL = "INFO"
