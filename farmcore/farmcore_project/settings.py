"""FarmCore Django project settings."""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent
SCHEMAS_DIR = REPO_ROOT / "shared" / "schemas"

env = environ.Env(
    DJANGO_DEBUG=(bool, True),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-only-change-in-production")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_rq",
    "pgvector",
    "accounts",
    "farms",
    "documents",
    "assistant",
    "scheduling",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "farmcore_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "farmcore_project.wsgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-au"
TIME_ZONE = "Australia/Sydney"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "UNAUTHENTICATED_USER": None,
}

RQ_QUEUES = {
    "default": {
        "URL": env("REDIS_URL", default="redis://127.0.0.1:6379/0"),
        "DEFAULT_TIMEOUT": 600,
    }
}

MINIO_ENDPOINT = env("MINIO_ENDPOINT", default="localhost:9000")
MINIO_ACCESS_KEY = env("MINIO_ACCESS_KEY", default="minio")
MINIO_SECRET_KEY = env("MINIO_SECRET_KEY", default="minio12345")
MINIO_BUCKET = env("MINIO_BUCKET", default="farmcore-documents")
MINIO_USE_SSL = env.bool("MINIO_USE_SSL", default=False)

# Phase 0 stub version tuple defaults (pinned in Admit).
CAI_STUB_VERSIONS = {
    "corpus_snapshot_id": "gov-a-stub-none",
    "chunker_version": "chunk-stub-v0",
    "embedding_model_id": "none:0",
    "retrieval_config_version": "retr-stub-v0",
    "reranker_model_id": "none",
    "prompt_template_id": "refusal-stub-v0",
    "tool_registry_version": "tools-v0",
    "generation_model_id": "none:stub:0",
    "verifier_model_id": "none",
    "schema_version": "chunks-v1",
}

CHUNKS_SCHEMA_PATH = SCHEMAS_DIR / "chunks-v1.schema.json"
