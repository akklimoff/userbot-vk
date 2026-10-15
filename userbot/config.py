from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    # ACCESS_TOKEN — имя из config.py первых версий, старые настройки продолжают работать
    vk_token: str = Field(validation_alias=AliasChoices("VK_TOKEN", "ACCESS_TOKEN"))
    state_dir: str = "state"
    log_messages: bool = False
    workers: int = 8
