from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    # Z.ai Configuration
    zai_api_key: SecretStr = SecretStr("dummy_key_for_dev")
    zai_base_url: str = "https://api.z.ai"
    zai_monitor_endpoint: str = "/api/monitor/usage/quota/limit"
    zai_coding_plan_base_url: str | None = None

    # Identity - used by the "my usage" analytics views to attribute
    # usage to the operator of this monitor instance.
    user_identity: str | None = None
    user_application: str | None = None
    
    # Polling
    poll_interval_seconds: int = 60
    adaptive_polling_enabled: bool = True
    min_poll_interval: int = 30
    max_poll_interval: int = 300
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/glm_monitor.db"
    
    # Proxy Collector
    proxy_enabled: bool = False
    proxy_port: int = 8080
    proxy_target_url: str = "https://api.z.ai"
    
    # Log Collector
    log_collector_enabled: bool = False
    log_watch_paths: list[str] = []
    
    # Webhook Collector
    webhook_enabled: bool = True
    webhook_secret: SecretStr | None = None

    # Default provider tag for Z.ai (GLM) request-level collectors.
    default_provider: str = "zai"

    # OpenAI Admin usage poller (ChatGPT / GPT models).
    # Requires an Admin API key (sk-admin-...). Disabled unless a key is set.
    openai_enabled: bool = False
    openai_api_key: SecretStr = SecretStr("")
    openai_base_url: str = "https://api.openai.com"
    openai_poll_interval_seconds: int = 300

    # Anthropic Admin usage poller (Claude / Claude Code models).
    # Requires an Admin API key (sk-ant-admin01-...). Disabled unless a key is set.
    anthropic_enabled: bool = False
    anthropic_api_key: SecretStr = SecretStr("")
    anthropic_base_url: str = "https://api.anthropic.com"
    anthropic_poll_interval_seconds: int = 300

    # Anthropic forward-proxy collector. Captures per-request token usage by
    # intercepting Claude Code's OWN traffic to api.anthropic.com. Works with
    # subscription (OAuth) OR pay-as-you-go keys — usage is read from the
    # streamed Messages response. Point Claude Code at it via ANTHROPIC_BASE_URL.
    anthropic_proxy_enabled: bool = False
    anthropic_proxy_port: int = 8090
    anthropic_proxy_target_url: str = "https://api.anthropic.com"
    anthropic_proxy_application: str = "claude-code"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Data Retention
    retention_days: int = 90
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json | console
    
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_prefix="GLM_MONITOR_",
        case_sensitive=False,
        extra="ignore"
    )

settings = Settings()
