from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "DevOps Platform"
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me-to-a-random-32-char-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DATABASE_URL: str = "mysql+aiomysql://root:password@localhost:3306/devops_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    DINGTALK_WEBHOOK: str = ""

    # Jenkins
    JENKINS_URL: str = ""
    JENKINS_USER: str = ""
    JENKINS_TOKEN: str = ""


settings = Settings()
