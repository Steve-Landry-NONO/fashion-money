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

    # Vision is provider-swappable. Tests/dev default to the deterministic mock.
    decomposition_provider: str = "mock"
    openai_api_key: str | None = None
    groq_api_key: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    # Validated Groq baseline from the local 4-image smoke benchmark.
    vision_model: str = "qwen/qwen3.8-27b"

    # Product Search is provider-swappable. Shopify is experimental until the
    # France benchmark passes; mock remains the safe default for CI/dev.
    product_search_provider: str = "mock"
    shopify_ucp_profile_url: str | None = None
    product_search_timeout_seconds: float = 10.0

    # Decision Engine config (externalised — parameters to learn, not to debate)
    tight_threshold_abs: float = 15.0
    tight_threshold_pct: float = 0.15
    rollover_cap_multiplier: float = 1.0


settings = Settings()
