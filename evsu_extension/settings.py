from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'development-only-change-before-deployment'
DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1','localhost']
INSTALLED_APPS = [
'django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','dashboard']
MIDDLEWARE = [
'django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF='evsu_extension.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages','dashboard.context_processors.global_context']}}]
WSGI_APPLICATION='evsu_extension.wsgi.application'
DATABASES={'default':{'ENGINE':'django.db.backends.mysql','NAME':'evsu_extension','USER':'root','PASSWORD':'','HOST':'127.0.0.1','PORT':'3306','OPTIONS':{'charset':'utf8mb4'}}}
AUTH_PASSWORD_VALIDATORS=[]
LANGUAGE_CODE='en-us'
TIME_ZONE='Asia/Manila'
USE_I18N=True
USE_TZ=True
STATIC_URL='/static/'
MEDIA_URL='/media/'
MEDIA_ROOT=BASE_DIR/'media'
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
LOGIN_URL='/login/'
LOGIN_REDIRECT_URL='/'
LOGOUT_REDIRECT_URL='/login/'

# TAEP Director forms legitimately contain more than Django's default 1,000 fields.
DATA_UPLOAD_MAX_NUMBER_FIELDS=5000
