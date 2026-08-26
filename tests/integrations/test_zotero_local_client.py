from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import ClassVar

import pytest

import research_skills_os.integrations.zotero_obsidian.zotero as zotero_module
from research_skills_os.integrations.zotero_obsidian import SyncSource
from research_skills_os.integrations.zotero_obsidian.zotero import (
    HttpResult,
    LocalZoteroClient,
    UrllibTransport,
    ZoteroIdentityCollision,
    ZoteroVersionUnsupported,
)


class FakeUrlResponse:
    status = 200
    headers: ClassVar[dict[str, str]] = {}

    def __enter__(self) -> FakeUrlResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return b"{}"


@dataclass(frozen=True)
class ExpectedRequest:
    method: str
    path: str
    result: HttpResult


@dataclass
class ScriptedTransport:
    expected: list[ExpectedRequest]
    received: list[tuple[str, str, dict[str, str], bytes | None]] = field(default_factory=list)

    def request(
        self, method: str, path: str, headers: dict[str, str], body: bytes | None
    ) -> HttpResult:
        expectation = self.expected.pop(0)
        assert (method, path) == (expectation.method, expectation.path)
        self.received.append((method, path, headers, body))
        return expectation.result


def json_result(payload: object, **headers: str) -> HttpResult:
    return HttpResult(status=200, headers=headers, body=json.dumps(payload).encode())


def ready_result(version: str = "10.0.1") -> HttpResult:
    return HttpResult(
        status=200,
        headers={"X-Zotero-Version": version, "Zotero-Server-ID": "SERVER123"},
        body=b"Nothing to see here.",
    )


def source_record() -> SyncSource:
    return SyncSource(
        source_id="brady-2017",
        title="Emotion shapes the diffusion of moralized content",
        year=2017,
        item_type="journalArticle",
        authors=("William J. Brady",),
        doi="HTTPS://DOI.ORG/10.1073/PNAS.1618923114",
        url="https://www.pnas.org/doi/10.1073/pnas.1618923114",
        content_sha256="a" * 64,
        note_source="notes/brady.md",
        inspected_content=True,
    )


def test_default_transport_allows_time_for_human_authorization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, float] = {}

    def fake_urlopen(request: object, *, timeout: float) -> FakeUrlResponse:
        observed["timeout"] = timeout
        return FakeUrlResponse()

    monkeypatch.setattr(zotero_module, "urlopen", fake_urlopen)

    UrllibTransport().request("GET", "/api/", {}, None)

    assert observed["timeout"] == 60


def test_zotero_9_is_rejected_before_any_write() -> None:
    transport = ScriptedTransport([ExpectedRequest("GET", "/api/", ready_result("9.0.5"))])
    client = LocalZoteroClient(transport=transport)

    with pytest.raises(ZoteroVersionUnsupported, match="10 or later"):
        client.ensure_collection("Pilot")

    assert [method for method, _, _, _ in transport.received] == ["GET"]


def test_existing_collection_does_not_request_write_authorization() -> None:
    transport = ScriptedTransport(
        [
            ExpectedRequest("GET", "/api/", ready_result()),
            ExpectedRequest(
                "GET",
                "/api/users/0/collections",
                json_result([{"key": "COLL1234", "data": {"name": "Pilot"}}]),
            ),
        ]
    )

    assert LocalZoteroClient(transport=transport).ensure_collection("Pilot") == "COLL1234"
    assert [method for method, _, _, _ in transport.received] == ["GET", "GET"]


def test_collection_creation_uses_local_authorization_and_server_id() -> None:
    transport = ScriptedTransport(
        [
            ExpectedRequest("GET", "/api/", ready_result()),
            ExpectedRequest("GET", "/api/users/0/collections", json_result([])),
            ExpectedRequest(
                "POST",
                "/api/local/authorize",
                json_result({"key": "K" * 32, "remember": False}),
            ),
            ExpectedRequest(
                "POST",
                "/api/users/0/collections",
                json_result({"successful": {"0": {"key": "NEWC1234"}}}),
            ),
        ]
    )

    key = LocalZoteroClient(transport=transport).ensure_collection("Pilot")

    assert key == "NEWC1234"
    _, _, authorize_headers, authorize_body = transport.received[2]
    assert authorize_headers["Zotero-Server-ID"] == "SERVER123"
    assert json.loads(authorize_body or b"") == {"appName": "Research Skills OS"}
    _, _, write_headers, write_body = transport.received[3]
    assert write_headers["Zotero-API-Key"] == "K" * 32
    assert write_headers["Zotero-Server-ID"] == "SERVER123"
    assert json.loads(write_body or b"") == [{"name": "Pilot", "parentCollection": False}]


def test_find_item_returns_only_exact_normalized_doi_match() -> None:
    payload = [
        {"key": "RIGHT123", "data": {"DOI": "10.1073/PNAS.1618923114"}},
        {"key": "WRONG123", "data": {"DOI": "10.1073/pnas.other"}},
    ]
    transport = ScriptedTransport(
        [
            ExpectedRequest("GET", "/api/", ready_result()),
            ExpectedRequest(
                "GET",
                "/api/users/0/items/top?q=10.1073%2Fpnas.1618923114",
                json_result(payload),
            ),
        ]
    )

    assert (
        LocalZoteroClient(transport=transport).find_item("doi:10.1073/pnas.1618923114")
        == "RIGHT123"
    )


def test_duplicate_exact_identity_is_reported_instead_of_guessed() -> None:
    payload = [
        {"key": "FIRST123", "data": {"DOI": "10.1000/test"}},
        {"key": "SECOND12", "data": {"DOI": "10.1000/test"}},
    ]
    transport = ScriptedTransport(
        [
            ExpectedRequest("GET", "/api/", ready_result()),
            ExpectedRequest(
                "GET", "/api/users/0/items/top?q=10.1000%2Ftest", json_result(payload)
            ),
        ]
    )

    with pytest.raises(ZoteroIdentityCollision, match="2 Zotero items"):
        LocalZoteroClient(transport=transport).find_item("doi:10.1000/test")


def test_created_item_contains_normalized_identity_and_collection() -> None:
    transport = ScriptedTransport(
        [
            ExpectedRequest("GET", "/api/", ready_result()),
            ExpectedRequest(
                "POST",
                "/api/local/authorize",
                json_result({"key": "K" * 32, "remember": False}),
            ),
            ExpectedRequest(
                "POST",
                "/api/users/0/items",
                json_result({"success": {"0": "ITEM1234"}}),
            ),
        ]
    )

    key = LocalZoteroClient(transport=transport).create_item(source_record(), "COLL1234")

    assert key == "ITEM1234"
    payload = json.loads(transport.received[2][3] or b"")[0]
    assert payload["DOI"] == "10.1073/pnas.1618923114"
    assert payload["collections"] == ["COLL1234"]
    assert payload["creators"] == [{"creatorType": "author", "name": "William J. Brady"}]


def test_existing_item_is_patched_with_complete_collection_list() -> None:
    transport = ScriptedTransport(
        [
            ExpectedRequest("GET", "/api/", ready_result()),
            ExpectedRequest(
                "GET",
                "/api/users/0/items/ITEM1234",
                json_result(
                    {
                        "data": {
                            "key": "ITEM1234",
                            "version": 4,
                            "collections": ["OLD12345"],
                        }
                    }
                ),
            ),
            ExpectedRequest(
                "POST",
                "/api/local/authorize",
                json_result({"key": "K" * 32, "remember": False}),
            ),
            ExpectedRequest(
                "PATCH",
                "/api/users/0/items/ITEM1234",
                HttpResult(status=204, headers={}, body=b""),
            ),
        ]
    )

    LocalZoteroClient(transport=transport).add_to_collection("ITEM1234", "NEW12345")

    payload = json.loads(transport.received[3][3] or b"")
    assert payload == {"version": 4, "collections": ["OLD12345", "NEW12345"]}
