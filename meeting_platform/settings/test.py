# Test settings file - contains mock/test credentials only, not real secrets
# bandit: disable=B105
import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Ensure apps/ directory is on PYTHONPATH like prod settings
sys.path.insert(0, os.path.join(BASE_DIR, "apps"))
SECRET_KEY = 'test-secret-key'  # nosec B105
DEBUG = True
ALLOWED_HOSTS = []
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'meeting.apps.MeetingConfig',  # Added: meeting app
    'rest_framework',  # Added: DRF
]

# Custom user model
AUTH_USER_MODEL = "meeting.User"

ROOT_URLCONF = 'meeting_platform.urls'
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

# Database - using in-memory SQLite for faster tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # Changed: use in-memory database for faster test execution
    }
}

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'EXCEPTION_HANDLER': 'meeting_platform.utils.customized.my_exception.my_exception_handler',
}

# Templates configuration
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

USE_TZ = False
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Shanghai'
STATIC_URL = '/static/'
STATIC_ROOT = '/tmp/static'  # Required for urls.py static() call in DEBUG mode
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Stub external platform configs required by meeting app to prevent AttributeError during tests
MEETING_PLATFORM = {}
PERMISSION_PLATFORM = {}
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Test platform configurations
COMMUNITY_HOST = {
    'openEuler': {
        'zoom': [
            {'HOST': 'host1@test.com', 'ACCOUNT': 'account1', 'TOKEN': 'token1'},  # nosec
            {'HOST': 'host2@test.com', 'ACCOUNT': 'account2', 'TOKEN': 'token2'},  # nosec
            {'HOST': 'host3@test.com', 'ACCOUNT': 'account3', 'TOKEN': 'token3'}  # nosec
        ],
        'ZOOM': [
            {'HOST': 'host1@test.com', 'ACCOUNT': 'account1', 'TOKEN': 'token1'},  # nosec
            {'HOST': 'host2@test.com', 'ACCOUNT': 'account2', 'TOKEN': 'token2'},  # nosec
            {'HOST': 'host3@test.com', 'ACCOUNT': 'account3', 'TOKEN': 'token3'}  # nosec
        ],
        'welink': [
            {'HOST': 'host4@test.com', 'ACCOUNT': 'account4', 'PWD': 'pwd4'},  # nosec
            {'HOST': 'host5@test.com', 'ACCOUNT': 'account5', 'PWD': 'pwd5'},  # nosec
            {'HOST': 'host6@test.com', 'ACCOUNT': 'account6', 'PWD': 'pwd6'}  # nosec
        ],
        'WELINK': [
            {'HOST': 'host4@test.com', 'ACCOUNT': 'account4', 'PWD': 'pwd4'},  # nosec
            {'HOST': 'host5@test.com', 'ACCOUNT': 'account5', 'PWD': 'pwd5'},  # nosec
            {'HOST': 'host6@test.com', 'ACCOUNT': 'account6', 'PWD': 'pwd6'}  # nosec
        ],
        'tencent': [
            {'HOST': 'host7@test.com', 'SECRET_ID': 'id7', 'SECRET_KEY': 'key7'},  # nosec
            {'HOST': 'host8@test.com', 'SECRET_ID': 'id8', 'SECRET_KEY': 'key8'},  # nosec
            {'HOST': 'host9@test.com', 'SECRET_ID': 'id9', 'SECRET_KEY': 'key9'}  # nosec
        ],
        'TENCENT': [
            {'HOST': 'host7@test.com', 'SECRET_ID': 'id7', 'SECRET_KEY': 'key7'},  # nosec
            {'HOST': 'host8@test.com', 'SECRET_ID': 'id8', 'SECRET_KEY': 'key8'},  # nosec
            {'HOST': 'host9@test.com', 'SECRET_ID': 'id9', 'SECRET_KEY': 'key9'}  # nosec
        ]
    }
}

# Test SMTP configuration (will be mocked in tests)
COMMUNITY_SMTP = {
    'openEuler': {
        'SMTP_SERVER_HOST': 'smtp.test.com',
        'SMTP_SERVER_PORT': 587,
        'SMTP_SERVER_USER': 'test@test.com',
        'SMTP_SERVER_PASS': 'test_password',  # nosec
        'SMTP_MESSAGE_FROM': 'noreply@test.com'
    }
}

# Test Kafka configuration (will be mocked in tests)
COMMUNITY_KAFKA = {
    'openEuler': {
        'bootstrap_servers': ['localhost:9092'],
        'topic': 'test-meeting-notifications'
    }
}

# Email templates for notification system
TEMPLATE = {
    'TEMPLATE_NOT_SUMMARY_NOT_RECORDING': 'meeting_platform/test/meeting/templates/not_summary_not_recording.txt',
    'TEMPLATE_SUMMARY_NOT_RECORDING': 'meeting_platform/test/meeting/templates/summary_not_recording.txt',
    'TEMPLATE_NOT_SUMMARY_RECORDING': 'meeting_platform/test/meeting/templates/not_summary_recording.txt',
    'TEMPLATE_SUMMARY_RECORDING': 'meeting_platform/test/meeting/templates/summary_recording.txt',
    'TEMPLATE_CANCEL_EMAIL': 'meeting_platform/test/meeting/templates/cancel_email.txt',
}

# Test community configuration
COMMUNITY_SUPPORT = ['openEuler']
COMMUNITY_PORTAL = {
    'openEuler': {
        'PORTAL_ZH': 'https://test.openeuler.org',
        'PORTAL_EN': 'https://test.openeuler.org/en'
    }
}
COMMUNITY_PRIVATE_MEETING_EMAIL_SUFFIX = {
    'openEuler': '@openEuler.com'
}

# Test feature flags
IS_UPLOAD_BILI = False  # Disable Bilibili upload in tests
IS_UPLOAD_OBS = False   # Disable OBS upload in tests
API_PREFIX = {
    'WELINK_API_PREFIX': 'https://api.test.welink.com',
    'ZOOM_API_PREFIX': 'https://api.test.zoom.us',
    'TENCENT_API_PREFIX': 'https://api.test.tencent.com',
}

# Test meeting limits
MEETING_CREATE_COUNT = 10
MEETING_MODIFY_COUNT = 5
QUERY_MEETING_DATE = 7
FORCE_MEETING_END_TIME = 15
FORCE_MEETING_END_POINT = 24
BILI_VIDEO_MIN_SIZE = 1024 * 1024 * 50
BILI_UPLOAD_DATE = 7
REQUEST_TIMEOUT = (5, 5)  # Shorter timeout for tests
HANDLE_MEETING_SCHEDULE_PLAN = "windows"

# Test recording configurations (stubs)
COMMUNITY_OBS = {}
COMMUNITY_BILI = {}
# Audit client disabled for tests (URL/TOKEN = None will bypass audit checks)
COMMUNITY_AUDIT = {
    'URL': None,
    'TOKEN': None  # nosec
}
COMMUNITY_TRANSLATE = {
    'URL': 'http://test-translate.com',
    'TOKEN': 'test-token'  # nosec
}
COMMUNITY_ZOOM_OBS = {}

# Test warning advance time (minutes)
OVER_TIME_WARNING_ADVANCE_TIME = 30

# Test operator emails configuration (for warning emails)
OPERATOR_EMAILS = {
    'openEuler': ['operator@test.com']
}