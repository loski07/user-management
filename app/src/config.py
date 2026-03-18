from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """
    Application settings are loaded from environment variables.
    Pydantic raises a ValidationError if required settings (those without a default)
    are not found as environment variables.
    """

    s3_bucket_name: str
    dynamodb_table_name: str
    aws_region: str = "us-east-1"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> AppSettings:
    """
    Returns the application settings as a singleton by validating from the environment.
    The settings are cached using lru_cache to avoid re-reading them on every request.
    """
    return AppSettings.model_validate({})
