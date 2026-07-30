"""Application configuration loaded from environment variables."""
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    hf_api_token: str = os.getenv("HF_API_TOKEN", "")
    hf_model: str = os.getenv("HF_MODEL", "cardiffnlp/twitter-roberta-base-sentiment-latest")
    hf_api_url: str = f"https://router.huggingface.co/hf-inference/models/{hf_model}"

    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))

    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
    cache_max_size: int = int(os.getenv("CACHE_MAX_SIZE", "1000"))
    cache_backend: str = os.getenv("CACHE_BACKEND", "memory")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    rate_limit: str = os.getenv("RATE_LIMIT", "10/minute")
    batch_rate_limit: str = os.getenv("BATCH_RATE_LIMIT", "5/minute")
    batch_max_size: int = int(os.getenv("BATCH_MAX_SIZE", "50"))

    neutral_confidence_threshold: float = float(os.getenv("NEUTRAL_CONFIDENCE_THRESHOLD", "0.7"))

    circuit_breaker_threshold: int = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5"))
    circuit_breaker_reset_seconds: float = float(os.getenv("CIRCUIT_BREAKER_RESET_SECONDS", "30"))

    max_request_body_bytes: int = int(os.getenv("MAX_REQUEST_BODY_BYTES", str(256 * 1024)))


settings = Settings()
