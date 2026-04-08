from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "wechat-travel-agents"
    app_env: str = "development"
    database_url: str = "sqlite:///./wechat_agents.db"
    jwt_secret: str = "replace-me"
    app_encryption_key: str = ""
    wechat_component_app_id: str = ""
    wechat_component_app_secret: str = ""
    wechat_component_token: str = ""
    wechat_component_aes_key: str = ""
    wechat_callback_base_url: str = "http://localhost:8000"
    default_search_provider: str = "cn-search"
    image_source_provider: str = "mock-xiaohongshu"
    media_root: str = "./media"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def media_path(self) -> Path:
        return Path(self.media_root).resolve()


settings = Settings()
