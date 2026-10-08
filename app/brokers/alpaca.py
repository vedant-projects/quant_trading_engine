"""Read-only Alpaca paper-account monitor.

Automated order submission is intentionally not exposed.
"""

import httpx

from app.config import Settings
from app.utils.exceptions import BrokerError


class AlpacaPaperMonitor:
    """Read selected fields from the fixed Alpaca paper endpoint."""

    def __init__(self, settings: Settings) -> None:
        """Require paper credentials and create a bounded HTTP client."""
        key = settings.alpaca_api_key.get_secret_value()
        secret = settings.alpaca_secret_key.get_secret_value()

        if not key or not secret:
            raise BrokerError("Alpaca paper credentials are not configured.")

        self._client = httpx.AsyncClient(
            base_url="https://paper-api.alpaca.markets",
            headers={
                "APCA-API-KEY-ID": key,
                "APCA-API-SECRET-KEY": secret,
            },
            timeout=10,
            follow_redirects=False,
        )

    async def get_account(self) -> dict[str, str]:
        """Return selected account fields without returning raw broker data."""
        try:
            response = await self._client.get("/v2/account")
            response.raise_for_status()
            payload = response.json()

            fields = (
                "id",
                "status",
                "currency",
                "cash",
                "equity",
                "buying_power",
            )

            return {name: str(payload[name]) for name in fields}
        except (
            httpx.HTTPError,
            ValueError,
            KeyError,
            TypeError,
        ) as exc:
            raise BrokerError("Alpaca paper-account query failed.") from exc

    async def close(self) -> None:
        """Release HTTP resources."""
        await self._client.aclose()
