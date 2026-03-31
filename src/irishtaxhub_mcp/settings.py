from __future__ import annotations

import os

from dotenv import load_dotenv
from pydantic import BaseModel


class Settings(BaseModel):
    base_url: str = "http://localhost:5000"
    api_key: str | None = None
    timeout: float = 30.0
    openapi: str | None = None  # file path or URL

    @classmethod
    def load(cls) -> "Settings":
        # Load from .env if present
        load_dotenv()
        base_url = os.getenv("IRISHTAXHUB_BASE_URL", cls.model_fields["base_url"].default)
        openapi = os.getenv("IRISHTAXHUB_OPENAPI")
        if not openapi:
            # Default to the explicit stable endpoint exposed by the API
            openapi = f"{base_url.rstrip('/')}/openapi.json"
        return cls(
            base_url=base_url,
            api_key=os.getenv("IRISHTAXHUB_API_KEY"),
            timeout=float(os.getenv("IRISHTAXHUB_TIMEOUT", cls.model_fields["timeout"].default)),
            openapi=openapi,
        )
