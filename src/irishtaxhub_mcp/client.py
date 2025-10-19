from __future__ import annotations

from typing import Any, Dict, Optional
import httpx


class IrishTaxHubClient:
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers=self._headers(),
        )

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def close(self) -> None:
        await self._client.aclose()

    async def post_calculator(self, calculator: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST /v1/tax/calculators/{calculator}
        """
        url = f"/v1/tax/calculators/{calculator}"
        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()

    async def request(
        self,
        method: str,
        path: str,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not path.startswith("/"):
            raise ValueError("path must start with '/'")
        resp = await self._client.request(method.upper(), path, json=json_body, params=params)
        resp.raise_for_status()
        return resp.json()
