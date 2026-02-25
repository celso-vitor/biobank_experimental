import os
import environ
from pathlib import Path

# =========================
# BASE & ENV
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent

# Inicializa o environ
env = environ.Env(
    DEBUG=(bool, True)
)
# Tenta ler o arquivo .env se ele existir na raiz do projeto
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# =========================
# SEGURANÇA / DEBUG
# =========================
# Agora busca do .env, se não achar usa a dev-secret-key
SECRET_KEY = env('SECRET_KEY', default="dev-secret-key") 
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

# =========================
# APLICAÇÕES
# =========================
INSTALLED_APPS = [
    # 1. Django Core Apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # 2. App Principal
    "core.apps.CoreConfig",

    # 4. Utilitários Externos
    "import_export",  # <--- AQUI ESTÁ A CORREÇÃO!
    "django_extensions",
    "rest_framework",
    "django_filters",
]

# =========================
# MIDDLEWARE
# =========================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# =========================
# URLS / WSGI
# =========================
ROOT_URLCONF = "biobank.urls"
WSGI_APPLICATION = "biobank.wsgi.application"

# =========================
# TEMPLATES
# =========================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "core" / "interfaces",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# =========================
# DATABASE (DINÂMICO: POSTGRES OU SQLITE)
# =========================
DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
}

# =========================
# STATIC FILES (CSS, JS, IMAGES)
# =========================
STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "core" / "interfaces",
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

# =========================
# MEDIA (UPLOADS DE AMOSTRAS)
# =========================
MEDIA_URL = "/data/"
MEDIA_ROOT = BASE_DIR / "data"

# =========================
# INTERNACIONALIZAÇÃO
# =========================
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# =========================
# AUTENTICAÇÃO
# =========================
LOGIN_URL = "/login/"
LOGOUT_URL = "/logout/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

# =========================
# DEFAULTS
# =========================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
