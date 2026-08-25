import httpx
import logging
from datetime import datetime, timezone

from app.collectors.base import BaseCollector
from app.config import settings
from app.models.quota_snapshot import QuotaSnapshot, QuotaLimit

logger = logging.getLogger(__name__)

class OfficialCollector(BaseCollector):
    def __init__(self):
        super().__init__("official")
        self.client = httpx.AsyncClient(
            base_url=settings.zai_base_url,
            headers={"Authorization": f"Bearer {settings.zai_api_key.get_secret_value()}"},
            timeout=10.0
        )
        self.last_success = None
        self.last_error = None
        self.consecutive_failures = 0

    async def start(self) -> None:
        self.is_running = True
        # Actual polling is handled by APScheduler in this architecture,
        # but the collector provides the logic to fetch.
        pass

    async def stop(self) -> None:
        self.is_running = False
        await self.client.aclose()

    async def fetch_quota(self) -> QuotaSnapshot:
        """Fetch the current quota from Z.ai API."""
        try:
            response = await self.client.get(settings.zai_monitor_endpoint)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != 200:
                raise ValueError(f"API returned error code: {data.get('code')}")

            quota_data = data.get("data", {})
            level = quota_data.get("level", "unknown")
            limits_data = quota_data.get("limits", [])

            snapshot = QuotaSnapshot(
                level=level,
                raw_response=data
            )

            for limit_data in limits_data:
                # nextResetTime is epoch ms
                reset_ms = limit_data.get("nextResetTime")
                reset_time = datetime.fromtimestamp(reset_ms / 1000.0, tz=timezone.utc) if reset_ms else None

                limit = QuotaLimit(
                    limit_type=limit_data.get("type"),
                    unit=limit_data.get("unit"),
                    percentage=limit_data.get("percentage"),
                    current_value=limit_data.get("currentValue"),
                    limit_value=limit_data.get("usage"),
                    remaining=limit_data.get("remaining"),
                    next_reset_time=reset_time
                )
                snapshot.limits.append(limit)

            self.last_success = datetime.now(timezone.utc)
            self.consecutive_failures = 0
            self.last_error = None
            return snapshot

        except Exception as e:
            self.consecutive_failures += 1
            self.last_error = str(e)
            self.last_failure = datetime.now(timezone.utc)
            logger.error(f"Error fetching official quota: {e}")
            raise

    async def get_health(self) -> dict:
        return {
            "name": self.name,
            "is_running": self.is_running,
            "is_healthy": self.consecutive_failures == 0,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures
        }
