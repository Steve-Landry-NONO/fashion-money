from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://fashion:fashion@localhost:5432/fashion"
    analytics_sink: str = "stdout"  # stdout (dev) | saas (prod)
    # Decision Engine config (externalised — parameters to learn, not to debate)
    tight_threshold_abs: float = 15.0
    tight_threshold_pct: float = 0.15
    rollover_cap_multiplier: float = 1.0


settings = Settings()
