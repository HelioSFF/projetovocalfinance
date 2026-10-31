from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://vocal:vocal@db:5432/vocal_finance"
    test_database_url: str = "postgresql+asyncpg://vocal:vocal@db:5432/vocal_finance_test"
    cors_origins: str = "http://localhost:8081"
    decision_threshold: float = 0.6
    max_audio_mb: int = 10
    ai_timeout_seconds: int = 15
    openai_service_tier: str = ""
    extraction_model: str = "gpt-6-luna"
    openai_api_key: str = ""
    deepseek_api_key: str = ""
    app_env: str = "production"

    model_config = {"env_file": ".env", "extra": "ignore"}

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def dev_tools_enabled(self) -> bool:
        return self.app_env.strip().lower() == "development"


settings = Settings()
