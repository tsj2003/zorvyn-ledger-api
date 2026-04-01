from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://finance_user:finance_pass@db:5432/finance_db"
    JWT_SECRET: str = "change-me-to-a-long-random-string"
    JWT_EXPIRY_MINUTES: int = 60

    # sync URL for alembic migrations
    @property
    def sync_database_url(self) -> str:
        return self.DATABASE_URL.replace("+asyncpg", "+psycopg2")

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
