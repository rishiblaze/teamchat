from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    google_cloud_project: str = ""
    vertex_ai_location: str = "us-central1"
    ai_context_message_limit: int = 50

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = ""  # use GOOGLE_CLOUD_PROJECT etc.


@lru_cache
def get_settings() -> Settings:
    return Settings()
