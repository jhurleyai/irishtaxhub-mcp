from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List, Optional, Tuple

import httpx
import yaml
from jinja2 import Template
from jsonschema import Draft7Validator


class OpenAPILoader:
    def __init__(self, base_url: str, openapi_source: Optional[str] = None, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.source = openapi_source
        self.timeout = timeout
        self._spec: Optional[Dict[str, Any]] = None

    async def load(self) -> Dict[str, Any]:
        if self._spec is not None:
            return self._spec

        # 1) Explicit source via env: file path or URL
        if self.source:
            if self.source.startswith("http://") or self.source.startswith("https://"):
                self._spec = await self._fetch_url(self.source)
            else:
                self._spec = self._load_file(self.source)
        else:
            # 2) Try common endpoints exposed by Flasgger/OpenAPI
            for path in ["/apispec_1.json", "/openapi.json", "/apidocs/spec.json"]:
                try:
                    self._spec = await self._fetch_url(self.base_url + path)
                    break
                except Exception:
                    continue

        if not self._spec:
            raise RuntimeError("Unable to load OpenAPI spec from provided source or base_url.")

        return self._spec

    async def _fetch_url(self, url: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(url)
            r.raise_for_status()
            ct = r.headers.get("content-type", "").lower()
            if "json" in ct or url.endswith(".json"):
                return r.json()
            text = r.text
            # Support Jinja templates if present (unlikely for served JSON)
            if "{%" in text:
                template = Template(text)
                rendered = template.render(development_mode=True)
                return yaml.safe_load(rendered)
            # YAML fallback
            return yaml.safe_load(text)

    def _load_file(self, path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        if "{%" in raw:
            template = Template(raw)
            # Allow override via env; default True for local dev
            dev_mode = os.getenv("IRISHTAXHUB_DEVELOPMENT_MODE", "true").lower() in {"1", "true", "yes"}
            rendered = template.render(development_mode=dev_mode)
            return yaml.safe_load(rendered)
        # Try JSON then YAML
        try:
            return json.loads(raw)
        except Exception:
            return yaml.safe_load(raw)


def list_endpoints(spec: Dict[str, Any], tag: Optional[str] = None) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    paths = spec.get("paths", {})
    base_path = spec.get("basePath", "")
    for path, ops in paths.items():
        for method, op in ops.items():
            if method.lower() not in {"get", "post", "put", "delete", "patch"}:
                continue
            tags = op.get("tags", [])
            if tag and tag not in tags:
                continue
            effective_path = normalize_path(spec, path)
            results.append(
                {
                    "path": path,
                    "effectivePath": effective_path,
                    "method": method.upper(),
                    "summary": op.get("summary"),
                    "operationId": op.get("operationId"),
                    "tags": tags,
                }
            )
    return results


def _resolve_ref(spec: Dict[str, Any], ref: str) -> Dict[str, Any]:
    # Supports Swagger 2.0 style: #/definitions/Name and JSON Schema refs
    if not ref.startswith("#/"):
        raise ValueError(f"Unsupported ref format: {ref}")
    parts = ref.lstrip("#/").split("/")
    node: Any = spec
    for p in parts:
        node = node[p]
    if not isinstance(node, dict):
        raise ValueError(f"Resolved ref is not an object: {ref}")
    return node


def get_request_body_schema(spec: Dict[str, Any], path: str, method: str) -> Optional[Dict[str, Any]]:
    method = method.lower()
    # Try the exact path first
    op = spec.get("paths", {}).get(path, {}).get(method)
    if not op:
        # Try de-normalizing/normalizing relative to basePath
        base = spec.get("basePath", "")
        if base and path.startswith(base):
            op = spec.get("paths", {}).get(path[len(base) :] or "/", {}).get(method)
        elif base:
            op = spec.get("paths", {}).get(base.rstrip("/") + path, {}).get(method)
    if not op:
        return None

    # Swagger 2.0: parameters -> in: body -> schema
    for param in op.get("parameters", []) or []:
        if param.get("in") == "body" and "schema" in param:
            schema = param["schema"]
            if "$ref" in schema:
                return _resolve_ref(spec, schema["$ref"])  # type: ignore
            return schema
    # OpenAPI 3: requestBody -> content -> application/json -> schema
    req = op.get("requestBody")
    if req:
        content = req.get("content", {}).get("application/json", {})
        schema = content.get("schema")
        if schema:
            if "$ref" in schema:
                return _resolve_ref(spec, schema["$ref"])  # type: ignore
            return schema
    return None


def normalize_path(spec: Dict[str, Any], path: str) -> str:
    base = spec.get("basePath", "")
    if not base:
        return path
    if path.startswith(base):
        return path
    # Ensure single slash
    return base.rstrip("/") + path


def validate_body(spec: Dict[str, Any], path: str, method: str, body: Optional[Dict[str, Any]]) -> None:
    schema = get_request_body_schema(spec, path, method)
    if not schema or body is None:
        return
    # Create validator with the full spec as the reference resolver context
    # This allows $ref resolution to work correctly
    from jsonschema import RefResolver
    resolver = RefResolver.from_schema(spec)
    validator = Draft7Validator(schema, resolver=resolver)
    validator.validate(body)
