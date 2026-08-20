from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://fashion:fashion@localhost:5432/fashion"
    analytics_sink: str = "stdout"  # stdout (dev) | saas (prod)

    # Real image ingestion / object storage.
    image_bucket: str = "fashion-money-captures"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "fashion"
    s3_secret_key: str = "fashionfashion"
    s3_region: str = "us-east-1"
    max_image_bytes: int = 10 * 1024 * 1024

    # Vision is provider-swappable. Tests/dev default to the deterministic mock;
    # set DECOMPOSITION_PROVIDER=openai + OPENAI_API_KEY for real analysis.
    decomposition_provider: str = "mock"
    openai_api_key: str | None = None
    vision_model: str = "gpt-5.6-luna"

    # Decision Engine config (externalised — parameters to learn, not to debate)
    tight_threshold_abs: float = 15.0
    tight_threshold_pct: float = 0.15
    rollover_cap_multiplier: float = 1.0


settings = Settings()
