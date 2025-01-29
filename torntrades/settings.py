"""
Django settings for torntrades project.

Generated by 'django-admin startproject' using Django 3.0.6.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(override=True)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = [
    'tornexchange.com',
    'www.tornexchange.com',
    'www.torn.com',
    'localhost',
    '127.0.0.1',
    '84.46.245.25',
    '0.0.0.0:8000'
]

# CORS_ORIGIN_WHITELIST = ['http://www.torn.com',
#                          'https://www.torn.com', 'http://*', 'chrome-extension://*']

CORS_ORIGIN_ALLOW_ALL = True

CORS_ALLOW_HEADER = ['access-control-allow-origin']

CORS_ALLOW_METHODS = [
    'GET',
    'POST',
    'OPTIONS',
    'HEAD',
]

# Application definition

INSTALLED_APPS = [
    'crispy_forms',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'main.apps.MainConfig',
    'users.apps.UsersConfig',
    'django.contrib.humanize',
    'vote',
    'django_filters',
    'django_crontab',
    'hitcount',
    'corsheaders',
    'debug_toolbar',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'torntrades.urls'

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

WSGI_APPLICATION = 'torntrades.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv('POSTGRES_DB'),
        'USER': os.getenv('POSTGRES_USER'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        # the name of the depends_on value from docker-compose.yml
        'HOST': os.getenv('POSTGRES_HOST'),
        'PORT': os.getenv('POSTGRES_PORT'),
        'CONN_MAX_AGE': 60
    }
}


#
# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

MEDIA_URL = '/media/'

CRISPY_TEMPLATE_PACK = 'bootstrap4'

LOGIN_REDIRECT_URL = 'home'

LOGIN_URL = 'login'

DATA_UPLOAD_MAX_NUMBER_FIELDS = 10240

CRONJOBS = [
    ('* * * * *', 'django.core.management.update_items'),
]

MINIMUM_CIRCULATION_REQUIRED_FOR_ITEM = 50

INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

CSRF_FAILURE_VIEW = "main.views.custom_csrf_failure_view"

########################
#### SENTRY LOGGING ####
########################

if(DEBUG == "true"):
    SENTRY_DSN=None
else:
    SENTRY_DSN=os.getenv('SENTRY_DSN_URL')

sentry_sdk.init(
    dsn=SENTRY_DSN,
    
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    integrations=[DjangoIntegration()],
    send_default_pii=True  # Capture user data if applicable
)


########################
#### CACHING ###########
########################

CACHE_DIR_FOLDER = os.getenv("CACHE_DIR")

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-name',  # Optional, used to identify the cache instance.
        'TIMEOUT': 300,  # Cache timeout in seconds (default: 300 seconds or 5 minutes).
        'OPTIONS': {
            'MAX_ENTRIES': 1000,  # Maximum number of entries before older items are evicted.
            'CULL_FREQUENCY': 3,  # Fraction of entries to evict when the max is reached.
        },
    },
    'file': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': CACHE_DIR_FOLDER,  # Replace with your desired directory
        'TIMEOUT': 300,  # Cache timeout in seconds (default is 300 seconds)
        'OPTIONS': {
            'MAX_ENTRIES': 1000,  # Maximum number of entries in the cache
            'CULL_FREQUENCY': 3,  # Fraction of entries to cull when max reached
            'VERSION': 1,
        },
    }
}


########################
#### LOGGING ###########
########################

ERROR_LOG = os.getenv("500_ERRORS_FILE")

if ERROR_LOG != "":
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
            },
            'file': {
                'level': 'WARNING',
                'class': 'logging.FileHandler',
                'filename': ERROR_LOG,
            },
        },
        'loggers': {
            'django': {
                'handlers': ['file'],
                'level': 'WARNING',
                'propagate': True,
            },
            'django.db.backends': {
                'handlers': ['file'],
                'level': 'WARNING',
                'propagate': False,  # Avoid duplicating logs to the root logger
            },
        },
    }
