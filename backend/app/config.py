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
