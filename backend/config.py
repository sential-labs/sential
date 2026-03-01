from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SENTIAL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = Path("./data")
    redis_url: str = "redis://localhost:6379"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    database_url: str = ""

    def get_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        db_path = self.data_dir / "sential.db"
        return f"sqlite+aiosqlite:///{db_path}"


settings = Settings()