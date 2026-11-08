import os
from pathlib import Path
from urllib.parse import urlparse, unquote
BASE_DIR = Path(__file__).resolve().parent.parent

# Load simple KEY=VALUE settings from a local .env file. Existing environment
# variables take priority, which keeps hosting-platform configuration working.
ENV_FILE = BASE_DIR / '.env'
if ENV_FILE.exists():
    existing_environment_keys = set(os.environ)
    for raw_line in ENV_FILE.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        if key not in existing_environment_keys:
            # If a key appears more than once in .env, the last entry wins.
            os.environ[key] = value.strip().strip('"').strip("'")

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'local-development-only-change-before-deploying')
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'
if not DEBUG and SECRET_KEY == 'local-development-only-change-before-deploying':
    raise RuntimeError('Set DJANGO_SECRET_KEY for production')
_env_hosts = os.environ.get('DJANGO_ALLOWED_HOSTS', '')
_render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '')
ALLOWED_HOSTS = list(dict.fromkeys(
    [h.strip() for h in f"localhost,127.0.0.1,testserver,before-bed.onrender.com,{_render_host},{_env_hosts}".split(',') if h.strip()] + ['.onrender.com']
))
INSTALLED_APPS = ['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','planner']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    database_url = urlparse(DATABASE_URL)
    if database_url.scheme not in ('postgres', 'postgresql'):
        raise RuntimeError('DATABASE_URL must use the postgres:// or postgresql:// scheme')
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': unquote(database_url.path.lstrip('/')),
        'USER': unquote(database_url.username or ''),
        'PASSWORD': unquote(database_url.password or ''),
        'HOST': database_url.hostname or '',
        'PORT': database_url.port or 5432,
        'CONN_MAX_AGE': 600,
        'OPTIONS': {'sslmode': 'require'},
    }}
else:
    DATABASES = {'default': {'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'db.sqlite3'}}
AUTH_PASSWORD_VALIDATORS = [{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator'},{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE='en-us'
TIME_ZONE=os.environ.get('APP_TIME_ZONE','Asia/Singapore')
USE_I18N=True
USE_TZ=True
STATIC_URL='static/'
STATICFILES_DIRS=[BASE_DIR/'static']
STATIC_ROOT=BASE_DIR/'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}
MEDIA_URL='media/'
MEDIA_ROOT=BASE_DIR/'media'
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
LOGIN_URL='login'
LOGIN_REDIRECT_URL='dashboard'
LOGOUT_REDIRECT_URL='login'
if not DEBUG:
    CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(
        [f"https://{h}" for h in ALLOWED_HOSTS if not h.startswith('.')] +
        ['https://*.onrender.com', 'https://before-bed.onrender.com']
    ))
    SESSION_COOKIE_SECURE=True
    CSRF_COOKIE_SECURE=True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
