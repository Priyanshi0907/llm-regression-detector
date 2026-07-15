"""
Central configuration for the eval pipeline.
All values are loaded from environment variables (see .env.example)
so the same code runs identically in local dev, CI, and Docker.
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _get_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _get_float(key: str, default: float) -> float:
    val = os.getenv(key)
    return float(val) if val else default


def _get_int(key: str, default: int) -> int:
    val = os.getenv(key)
    return int(val) if val else default


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")

    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai")

    judge_model: str = os.getenv("JUDGE_MODEL", "gpt-4o-mini")
    judge_provider: str = os.getenv("JUDGE_PROVIDER", "openai")

    # Semantic similarity (embeddings) is an optional second score alongside
    # LLM-as-judge. Off by default since it adds an extra API call per case.
    semantic_similarity_enabled: bool = _get_bool("SEMANTIC_SIMILARITY_ENABLED", False)
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    slack_webhook_url: str = os.getenv("SLACK_WEBHOOK_URL", "")

    warning_threshold_pct: float = _get_float("WARNING_THRESHOLD_PCT", 3.0)
    critical_threshold_pct: float = _get_float("CRITICAL_THRESHOLD_PCT", 8.0)
    drift_window: int = _get_int("DRIFT_WINDOW", 7)
    drift_threshold_pct: float = _get_float("DRIFT_THRESHOLD_PCT", 5.0)

    mock_mode: bool = _get_bool("MOCK_MODE", True)
    report_base_url: str = os.getenv("REPORT_BASE_URL", "https://your-domain.com/reports")

    # Rough blended $/1K tokens used only to show an illustrative cost-per-run
    # figure in reports. Not a billing-accurate calculation — swap in your
    # provider's real input/output pricing if you need exact costs.
    cost_per_1k_tokens: float = _get_float("COST_PER_1K_TOKENS", 0.015)

    db_path: str = os.getenv("DB_PATH", "data/eval_results.db")
    reports_dir: str = os.getenv("REPORTS_DIR", "data/reports")
    prompts_dir: str = os.getenv("PROMPTS_DIR", "prompts")
    dataset_path: str = os.getenv("DATASET_PATH", "golden_dataset/dataset_v1.json")
    rubric_path: str = os.getenv("RUBRIC_PATH", "golden_dataset/judge_rubric.yaml")

    # Alerting — Slack was the original channel; Discord and email are
    # optional additions, all independently configurable.
    discord_webhook_url: str = os.getenv("DISCORD_WEBHOOK_URL", "")
    email_smtp_host: str = os.getenv("EMAIL_SMTP_HOST", "")
    email_smtp_port: int = _get_int("EMAIL_SMTP_PORT", 587)
    email_smtp_user: str = os.getenv("EMAIL_SMTP_USER", "")
    email_smtp_password: str = os.getenv("EMAIL_SMTP_PASSWORD", "")
    email_from: str = os.getenv("EMAIL_FROM", "")
    email_to: str = os.getenv("EMAIL_TO", "")  # comma-separated

    max_concurrency: int = _get_int("MAX_CONCURRENCY", 8)


settings = Settings()
