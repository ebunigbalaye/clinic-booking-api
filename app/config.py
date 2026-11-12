"""
This file lets us centralise database credentials coniguration in one place. We can then import the settings object into other files to access the database URL.
BaseSettings allows Pydantic to load configuration from environment variables.
DATABASE_URL tells our application where PostgreSQL is located.
env_file=".env" tells Pydantic to look for a local .env file.
settings = Settings() creates an instance containing our configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    API_KEY: str
    TEST_DATABASE_URL: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
