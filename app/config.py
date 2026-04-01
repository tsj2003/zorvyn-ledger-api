from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://finance_user:finance_pass@db:5432/finance_db"
    JWT_SECRET: str = "change-me-to-a-long-random-string"
    JWT_EXPIRY_MINUTES: int = 60

    @property
    def async_database_url(self) -> str:
        """Normalize DATABASE_URL to use asyncpg driver.
        Render provides postgres://, Docker/Render may provide postgresql://.
        SQLAlchemy requires postgresql+asyncpg:// for async support.
        """
        url = self.DATABASE_URL
        # Handle Render's postgres:// prefix first
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def sync_database_url(self) -> str:
        return self.async_database_url.replace("+asyncpg", "+psycopg2")

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()

