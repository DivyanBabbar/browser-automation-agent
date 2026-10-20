from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    browser_timeout_ms: int = 12_000
    max_plan_steps: int = 8
    data_dir: str = "data"
    log_level: str = "INFO"


settings = Settings()
