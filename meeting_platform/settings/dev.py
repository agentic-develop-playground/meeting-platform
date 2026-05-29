import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "apps"))

SECRET_KEY = 'dev-secret-key-do-not-use-in-production'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'meeting.apps.MeetingConfig',
    'rest_framework',
    'corsheaders',
    'django_filters',
    'drf_yasg',
]

AUTH_USER_MODEL = "meeting.User"

CORS_ALLOW_METHODS = (
    'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'
)
CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_ALLOW_ALL = True

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'meeting_platform.urls'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'EXCEPTION_HANDLER': 'meeting_platform.utils.customized.my_exception.my_exception_handler',
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'meeting_platform.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'meeting_platform'),
        'USER': os.getenv('DB_USER', 'root'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'meeting_dev'),
        'HOST': os.getenv('DB_HOST', 'mysql'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        }
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Shanghai'
USE_TZ = False
STATIC_URL = '/static/'
STATIC_ROOT = '/tmp/static'
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] [%(filename)s:%(lineno)d] [%(levelname)s]- %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'log': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}

MEETING_PLATFORM = {}
PERMISSION_PLATFORM = {}
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

COMMUNITY_HOST = {
    'openEuler': {
        'zoom': [],
        'ZOOM': [],
        'welink': [],
        'WELINK': [],
        'tencent': [],
        'TENCENT': [],
    }
}

COMMUNITY_SMTP = {}
COMMUNITY_KAFKA = {}
COMMUNITY_OBS = {}
COMMUNITY_BILI = {}
COMMUNITY_AUDIT = {'URL': None, 'TOKEN': None}
COMMUNITY_TRANSLATE = {'URL': 'http://localhost', 'TOKEN': 'dev-token'}
COMMUNITY_ZOOM_OBS = {}

TEMPLATE = {}
API_PREFIX = {}
COMMUNITY_SUPPORT = ['openEuler']
COMMUNITY_PORTAL = {
    'openEuler': {
        'PORTAL_ZH': 'https://test.openeuler.org',
        'PORTAL_EN': 'https://test.openeuler.org/en'
    }
}
COMMUNITY_PRIVATE_MEETING_EMAIL_SUFFIX = {'openEuler': '@openEuler.com'}
IS_UPLOAD_BILI = False
IS_UPLOAD_OBS = False

MEETING_CREATE_COUNT = 10
MEETING_MODIFY_COUNT = 5
QUERY_MEETING_DATE = 7
FORCE_MEETING_END_TIME = 30
FORCE_MEETING_END_POINT = 24
BILI_VIDEO_MIN_SIZE = 1024 * 1024 * 50
BILI_UPLOAD_DATE = 7
REQUEST_TIMEOUT = (5, 5)
HANDLE_MEETING_SCHEDULE_PLAN = "windows"

OPERATOR_EMAILS = {'openEuler': []}
OVER_TIME_WARNING_ADVANCE_TIME = 30