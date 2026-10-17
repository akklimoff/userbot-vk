from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    # ACCESS_TOKEN — имя из config.py первых версий, старые настройки продолжают работать
    vk_token: str = Field("", validation_alias=AliasChoices("VK_TOKEN", "ACCESS_TOKEN"))
    vk_tokens: str = ""
    trusted_ids: str = ""
    state_dir: str = "state"
    log_messages: bool = False
    workers: int = 8

    @property
    def tokens(self) -> list[str]:
        candidates = [self.vk_token, *self.vk_tokens.split(",")]
        return list(dict.fromkeys(token.strip() for token in candidates if token.strip()))

    @property
    def trusted(self) -> list[int]:
        return [int(part) for part in self.trusted_ids.split(",") if part.strip()]

    @model_validator(mode="after")
    def _trusted_are_ids(self) -> "Settings":
        if not all(part.strip().isdecimal() for part in self.trusted_ids.split(",") if part.strip()):
            raise ValueError("TRUSTED_IDS — числовые ID через запятую")
        return self

    @model_validator(mode="after")
    def _has_token(self) -> "Settings":
        if not self.tokens:
            raise ValueError("нужен VK_TOKEN или VK_TOKENS")
        return self
