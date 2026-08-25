from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import settings
from app.collectors.official import OfficialCollector
from app.collectors.zai_admin import ZaiAdminCollector
from app.collectors.openai import OpenAICollector
from app.collectors.anthropic import AnthropicCollector
from app.collectors.anthropic_proxy import AnthropicProxyCollector
from app.collectors.webhook import WebhookCollector
from app.collectors.proxy import ProxyCollector
from app.collectors.log_parser import LogCollector
from app.collectors.manager import CollectorManager

engine = create_async_engine(settings.database_url, echo=False)
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

# Shared singletons - imported by main.py lifespan and FastAPI dependencies.
official_collector = OfficialCollector()
zai_admin_collector = ZaiAdminCollector()
openai_collector = OpenAICollector()
anthropic_collector = AnthropicCollector()
anthropic_proxy_collector = AnthropicProxyCollector()

collector_manager = CollectorManager()
collector_manager.register(official_collector)
collector_manager.register(zai_admin_collector)
collector_manager.register(openai_collector)
collector_manager.register(anthropic_collector)
collector_manager.register(anthropic_proxy_collector)
collector_manager.register(WebhookCollector())
collector_manager.register(ProxyCollector())
collector_manager.register(LogCollector())


def get_official_collector() -> OfficialCollector:
    return official_collector


def get_collector_manager() -> CollectorManager:
    return collector_manager
