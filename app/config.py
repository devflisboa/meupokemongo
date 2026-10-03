import os
from datetime import datetime, timezone, timedelta

# Fuso horário de Brasília (UTC-3, sem DST para simplicidade em produção Docker)
TZ_BR = timezone(timedelta(hours=-3))


def now_br() -> datetime:
    """Retorna a hora atual no fuso de Brasília, sem tzinfo (compatível com MySQL)."""
    return datetime.now(TZ_BR).replace(tzinfo=None)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", "3306")
    DB_NAME = os.environ.get("DB_NAME", "meupokemongo")
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

    @property
    def SQLALCHEMY_DATABASE_URI(self):
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_ADMIN_CHAT_ID = os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "")

    # Limite global folgado: cada toggle/±/modal é uma requisição; catalogar gera centenas.
    # Rotas sensíveis (login/registro) têm limite próprio e rígido.
    RATELIMIT_DEFAULT = "3000 per hour;300 per minute"
    RATELIMIT_STORAGE_URL = "memory://"


class DevelopmentConfig(Config):
    DEBUG = True
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
