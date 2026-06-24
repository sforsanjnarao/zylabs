"""Application configuration.

Loads settings from environment variables (and the .env file) so that
secrets and tunables are never hardcoded in the source.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API keys (read from .env)
    openai_api_key: str = ""
    tavily_api_key: str = ""

    # Tunable defaults
    openai_model: str = "gpt-4o-mini"
    database_url: str = "sqlite:///./project01.db"
    log_level: str = "INFO"

    # Comma-separated list of allowed frontend origins for CORS.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse cors_origins into a clean list of origins."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


# A single shared settings instance the whole app imports.
settings = Settings()
