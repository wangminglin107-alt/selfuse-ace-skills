"""Narrow Zotero 10 local API boundary used by the bridge service."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import uuid4

from research_skills_os.integrations.zotero_obsidian.models import SyncSource
from research_skills_os.integrations.zotero_obsidian.planner import source_identity


class ZoteroError(RuntimeError):
    """Base class for recoverable Zotero bridge errors."""


class ZoteroUnavailable(ZoteroError):
    """Raised when the configured Zotero instance cannot be reached."""


class ZoteroVersionUnsupported(ZoteroError):
    """Raised when the running Zotero cannot authorize local writes."""


class ZoteroAuthorizationDenied(ZoteroError):
    """Raised when the user denies Zotero's local write prompt."""


class ZoteroProtocolError(ZoteroError):
    """Raised when Zotero returns an unexpected or unsuccessful response."""


class ZoteroIdentityCollision(ZoteroError):
    """Raised when more than one Zotero item has the same stable identity."""


@dataclass(frozen=True)
class HttpResult:
    status: int
    headers: dict[str, str]
    body: bytes


class HttpTransport(Protocol):
    def request(
        self, method: str, path: str, headers: dict[str, str], body: bytes | None
    ) -> HttpResult: ...


class UrllibTransport:
    def __init__(self, base_url: str = "http://127.0.0.1:23119") -> None:
        self._base_url = base_url.rstrip("/")

    def request(
        self, method: str, path: str, headers: dict[str, str], body: bytes | None
    ) -> HttpResult:
        request = Request(
            f"{self._base_url}{path}", data=body, headers=headers, method=method
        )
        try:
            with urlopen(request, timeout=10) as response:
                return HttpResult(
                    status=response.status,
                    headers=dict(response.headers.items()),
                    body=response.read(),
                )
        except HTTPError as error:
            return HttpResult(
                status=error.code,
                headers=dict(error.headers.items()),
                body=error.read(),
            )
        except URLError as error:
            raise ZoteroUnavailable(f"cannot reach local Zotero: {error.reason}") from error


class ZoteroClient(Protocol):
    def ensure_collection(self, name: str) -> str: ...

    def find_item(self, identity: str) -> str | None: ...

    def create_item(self, source: SyncSource, collection_key: str) -> str: ...

    def add_to_collection(self, item_key: str, collection_key: str) -> None: ...


def _header(headers: dict[str, str], name: str) -> str | None:
    expected = name.casefold()
    return next((value for key, value in headers.items() if key.casefold() == expected), None)


def _json(result: HttpResult) -> object:
    try:
        return json.loads(result.body)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ZoteroProtocolError("Zotero returned invalid JSON") from error


def _created_key(result: HttpResult) -> str:
    raw = _json(result)
    if not isinstance(raw, dict):
        raise ZoteroProtocolError("Zotero create response is not an object")
    outcomes = raw.get("success") or raw.get("successful")
    if not isinstance(outcomes, dict) or "0" not in outcomes:
        raise ZoteroProtocolError("Zotero did not create the requested object")
    created = outcomes["0"]
    if isinstance(created, str):
        return created
    if isinstance(created, dict):
        key = created.get("key")
        if isinstance(key, str) and key:
            return key
    raise ZoteroProtocolError("Zotero create response has no object key")


def _normalize_doi(value: str) -> str:
    normalized = value.strip().casefold()
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", normalized).strip()


class LocalZoteroClient:
    """Small no-delete client for the authorized Zotero 10 local API."""

    def __init__(self, *, transport: HttpTransport | None = None) -> None:
        self._transport = transport or UrllibTransport()
        self._server_id: str | None = None
        self._remembered_key: str | None = None

    def _ensure_ready(self) -> None:
        if self._server_id is not None:
            return
        result = self._transport.request(
            "GET", "/api/", {"Zotero-API-Version": "3"}, None
        )
        if result.status == 403:
            raise ZoteroUnavailable("local Zotero API is disabled")
        if result.status != 200:
            raise ZoteroUnavailable(f"local Zotero probe failed with HTTP {result.status}")
        version = _header(result.headers, "X-Zotero-Version")
        server_id = _header(result.headers, "Zotero-Server-ID")
        if not version or not server_id:
            raise ZoteroProtocolError("Zotero probe omitted version or server ID")
        try:
            major = int(version.split(".", maxsplit=1)[0])
        except ValueError as error:
            raise ZoteroProtocolError(f"invalid Zotero version: {version}") from error
        if major < 10:
            raise ZoteroVersionUnsupported("local writes require Zotero 10 or later")
        self._server_id = server_id

    def _read(self, path: str) -> HttpResult:
        self._ensure_ready()
        headers = {
            "Zotero-API-Version": "3",
            "Zotero-Server-ID": self._required_server_id(),
        }
        result = self._transport.request("GET", path, headers, None)
        if result.status != 200:
            raise ZoteroProtocolError(f"Zotero read failed with HTTP {result.status}")
        return result

    def _required_server_id(self) -> str:
        if self._server_id is None:
            raise ZoteroProtocolError("Zotero server ID is unavailable")
        return self._server_id

    def _authorize(self) -> str:
        self._ensure_ready()
        if self._remembered_key is not None:
            return self._remembered_key
        body = json.dumps({"appName": "Research Skills OS"}).encode()
        result = self._transport.request(
            "POST",
            "/api/local/authorize",
            {
                "Content-Type": "application/json",
                "Zotero-API-Version": "3",
                "Zotero-Server-ID": self._required_server_id(),
            },
            body,
        )
        if result.status == 403:
            raise ZoteroAuthorizationDenied("Zotero local write authorization was denied")
        if result.status != 200:
            raise ZoteroProtocolError(
                f"Zotero authorization failed with HTTP {result.status}"
            )
        raw = _json(result)
        if not isinstance(raw, dict) or not isinstance(raw.get("key"), str):
            raise ZoteroProtocolError("Zotero authorization response has no key")
        key = str(raw["key"])
        if raw.get("remember") is True:
            self._remembered_key = key
        return key

    def _write(self, method: str, path: str, payload: object) -> HttpResult:
        key = self._authorize()
        headers = {
            "Content-Type": "application/json",
            "Zotero-API-Version": "3",
            "Zotero-Server-ID": self._required_server_id(),
            "Zotero-API-Key": key,
        }
        if method == "POST":
            headers["Zotero-Write-Token"] = uuid4().hex
        result = self._transport.request(method, path, headers, json.dumps(payload).encode())
        if result.status not in {200, 204}:
            raise ZoteroProtocolError(f"Zotero write failed with HTTP {result.status}")
        return result

    def ensure_collection(self, name: str) -> str:
        raw = _json(self._read("/api/users/0/collections"))
        if not isinstance(raw, list):
            raise ZoteroProtocolError("Zotero collections response is not a list")
        matches = [
            item.get("key")
            for item in raw
            if isinstance(item, dict)
            and isinstance(item.get("data"), dict)
            and item["data"].get("name") == name
        ]
        keys = [key for key in matches if isinstance(key, str)]
        if len(keys) > 1:
            raise ZoteroIdentityCollision(f"{len(keys)} Zotero collections share the name")
        if keys:
            return keys[0]
        return _created_key(
            self._write(
                "POST",
                "/api/users/0/collections",
                [{"name": name, "parentCollection": False}],
            )
        )

    def find_item(self, identity: str) -> str | None:
        identity_type, _, value = identity.partition(":")
        path = f"/api/users/0/items/top?q={quote(value, safe='')}"
        raw = _json(self._read(path))
        if not isinstance(raw, list):
            raise ZoteroProtocolError("Zotero items response is not a list")
        keys: list[str] = []
        for item in raw:
            if not isinstance(item, dict) or not isinstance(item.get("data"), dict):
                continue
            data = item["data"]
            if identity_type == "doi":
                matches = _normalize_doi(str(data.get("DOI", ""))) == value
            elif identity_type == "url":
                candidate = SyncSource(
                    source_id="candidate",
                    title=str(data.get("title", "untitled")),
                    year=1000,
                    item_type=str(data.get("itemType", "document")),
                    url=str(data.get("url", "")),
                    content_sha256="0" * 64,
                    note_source="candidate.md",
                    inspected_content=False,
                )
                matches = source_identity(candidate) == identity
            else:
                title, _, year = value.rpartition("|")
                normalized_title = (
                    re.sub(r"\s+", " ", str(data.get("title", ""))).strip().casefold()
                )
                matches = normalized_title == title and str(data.get("date", "")).startswith(year)
            key = item.get("key")
            if matches and isinstance(key, str):
                keys.append(key)
        if len(keys) > 1:
            raise ZoteroIdentityCollision(f"{len(keys)} Zotero items share identity {identity}")
        return keys[0] if keys else None

    def create_item(self, source: SyncSource, collection_key: str) -> str:
        payload: dict[str, object] = {
            "itemType": source.item_type,
            "title": source.title,
            "creators": [
                {"creatorType": "author", "name": author} for author in source.authors
            ],
            "date": str(source.year),
            "collections": [collection_key],
            "tags": [{"tag": "research-skills-os"}],
        }
        if source.doi:
            payload["DOI"] = _normalize_doi(source.doi)
        if source.url:
            payload["url"] = source.url
        return _created_key(self._write("POST", "/api/users/0/items", [payload]))

    def add_to_collection(self, item_key: str, collection_key: str) -> None:
        raw = _json(self._read(f"/api/users/0/items/{item_key}"))
        if not isinstance(raw, dict) or not isinstance(raw.get("data"), dict):
            raise ZoteroProtocolError("Zotero item response has no editable data")
        data = raw["data"]
        version = data.get("version")
        collections = data.get("collections")
        if not isinstance(version, int) or not isinstance(collections, list):
            raise ZoteroProtocolError("Zotero item data omits version or collections")
        if collection_key in collections:
            return
        self._write(
            "PATCH",
            f"/api/users/0/items/{item_key}",
            {"version": version, "collections": [*collections, collection_key]},
        )
