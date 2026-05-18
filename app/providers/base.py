import hashlib
import json
import time
from pathlib import Path
from typing import Any

import httpx

from app.config import get_settings


class ProviderError(RuntimeError):
    def __init__(self, provider: str, message: str) -> None:
        super().__init__(message)
        self.provider = provider
        self.message = message


class CachedHTTPClient:
    def __init__(self, provider: str) -> None:
        self.provider = provider
        self.settings = get_settings()

    async def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        ttl_seconds: int | None = None,
    ) -> Any:
        ttl = ttl_seconds if ttl_seconds is not None else self.settings.cache_ttl_seconds
        cache_path = self._cache_path(url, params)
        if cache_path.exists() and time.time() - cache_path.stat().st_mtime < ttl:
            return json.loads(cache_path.read_text(encoding="utf-8"))

        async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
            response = await client.get(url, params=params)
            if response.status_code >= 400:
                raise ProviderError(self.provider, f"HTTP {response.status_code}: {response.text[:200]}")
            payload = response.json()
            cache_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
            return payload

    def _cache_path(self, url: str, params: dict[str, Any] | None) -> Path:
        key = json.dumps({"url": url, "params": params or {}}, sort_keys=True)
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.settings.cache_dir / f"{self.provider}_{digest}.json"
