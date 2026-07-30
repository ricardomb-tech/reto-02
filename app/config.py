"""Application configuration loaded from environment variables."""
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    hf_api_token: str = os.getenv("HF_API_TOKEN", "")
    hf_model: str = os.getenv("HF_MODEL", "distilbert/distilbert-base-uncased-finetuned-sst-2-english")
    hf_api_url: str = f"https://router.huggingface.co/hf-inference/models/{hf_model}"

    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))

    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
    cache_max_size: int = int(os.getenv("CACHE_MAX_SIZE", "1000"))

    rate_limit: str = os.getenv("RATE_LIMIT", "10/minute")


settings = Settings()
