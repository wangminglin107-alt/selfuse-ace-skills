from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs

from research_skills_os.integrations.zotero_obsidian.attachments import PreparedAttachment
from research_skills_os.integrations.zotero_obsidian.zotero import (
    HttpResult,
    LocalZoteroClient,
)


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


def json_result(payload: object) -> HttpResult:
    return HttpResult(status=200, headers={}, body=json.dumps(payload).encode())


def ready_result() -> HttpResult:
    return HttpResult(
        status=200,
        headers={"X-Zotero-Version": "10.0.1", "Zotero-Server-ID": "SERVER123"},
        body=b"",
    )


def prepared_pdf(tmp_path: Path) -> PreparedAttachment:
    content = b"%PDF-1.7\n%%EOF\n"
    path = tmp_path / "paper.pdf"
    path.write_bytes(content)
    stat = path.stat()
    return PreparedAttachment(
        path=path,
        filename="paper.pdf",
        sha256=hashlib.sha256(content).hexdigest(),
        md5=hashlib.md5(content, usedforsecurity=False).hexdigest(),
        size=len(content),
        mtime_ms=int(stat.st_mtime * 1000),
        media_type="application/pdf",
        source_url="https://example.org/paper.pdf",
    )


def test_find_attachment_uses_stable_sha256_tag(tmp_path: Path) -> None:
    prepared = prepared_pdf(tmp_path)
    payload = [
        {
            "key": "ATTACH01",
            "data": {
                "itemType": "attachment",
                "tags": [{"tag": f"research-skills-os-sha256:{prepared.sha256}"}],
            },
        }
    ]
    transport = ScriptedTransport(
        [
            ExpectedRequest("GET", "/api/", ready_result()),
            ExpectedRequest("GET", "/api/users/0/items/PARENT01/children", json_result(payload)),
        ]
    )

    assert LocalZoteroClient(transport=transport).find_attachment(
        "PARENT01", prepared.sha256
    ) == "ATTACH01"


def test_create_attachment_performs_full_local_upload(tmp_path: Path) -> None:
    prepared = prepared_pdf(tmp_path)
    authorize = json_result({"key": "K" * 32, "remember": True})
    upload = {
        "url": "/api/local/file-upload/UPLOAD01",
        "contentType": "application/octet-stream",
        "prefix": "PREFIX",
        "suffix": "SUFFIX",
        "uploadKey": "UPLOAD01",
    }
    transport = ScriptedTransport(
        [
            ExpectedRequest("GET", "/api/", ready_result()),
            ExpectedRequest("POST", "/api/local/authorize", authorize),
            ExpectedRequest(
                "POST",
                "/api/users/0/items",
                json_result({"success": {"0": "ATTACH01"}}),
            ),
            ExpectedRequest(
                "POST",
                "/api/users/0/items/ATTACH01/file",
                json_result(upload),
            ),
            ExpectedRequest(
                "POST",
                "/api/local/file-upload/UPLOAD01",
                HttpResult(status=201, headers={}, body=b""),
            ),
            ExpectedRequest(
                "POST",
                "/api/users/0/items/ATTACH01/file",
                HttpResult(status=204, headers={}, body=b""),
            ),
        ]
    )

    key = LocalZoteroClient(transport=transport).create_attachment("PARENT01", prepared)

    assert key == "ATTACH01"
    item_payload = json.loads(transport.received[2][3] or b"")[0]
    assert item_payload["parentItem"] == "PARENT01"
    assert item_payload["linkMode"] == "imported_file"
    assert item_payload["tags"] == [
        {"tag": f"research-skills-os-sha256:{prepared.sha256}"}
    ]
    authorization = parse_qs((transport.received[3][3] or b"").decode())
    assert authorization["md5"] == [prepared.md5]
    assert transport.received[4][3] == b"PREFIX" + prepared.path.read_bytes() + b"SUFFIX"
    assert parse_qs((transport.received[5][3] or b"").decode()) == {"upload": ["UPLOAD01"]}
