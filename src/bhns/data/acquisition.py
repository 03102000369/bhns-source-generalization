"""Bounded, immutable evidence acquisition; never invent or replace payloads."""

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from urllib.request import Request, urlopen


def retrieve_evidence(url, directory, request_id, *, expected_sha256=None, max_bytes=25_000_000, timeout=30):
    if not url.startswith("https://"):
        raise ValueError("Evidence retrieval requires HTTPS")
    if not request_id.replace("_", "").replace("-", "").isalnum():
        raise ValueError("request_id must be a simple stable identifier")
    record = {"request_id": request_id, "url": url, "accessed_at": datetime.now(timezone.utc).isoformat()}
    try:
        with urlopen(Request(url, headers={"User-Agent": "BHNS-provenance-audit/0.1"}), timeout=timeout) as response:
            payload = response.read(max_bytes + 1)
            record.update(status_code=response.status, final_url=response.url,
                          content_type=response.headers.get("Content-Type"))
        if len(payload) > max_bytes:
            raise ValueError("Evidence payload exceeds configured size limit")
        checksum = hashlib.sha256(payload).hexdigest()
        if expected_sha256 is not None and checksum != expected_sha256:
            raise ValueError("Downloaded bytes differ from the expected checksum")
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{request_id}-{checksum[:12]}.bin"
        if path.exists():
            if path.read_bytes() != payload:
                raise ValueError("An immutable destination has conflicting bytes")
        else:
            with path.open("xb") as handle:
                handle.write(payload)
        record.update(status="retrieved", path=str(path), sha256=checksum, bytes=len(payload))
    except (OSError, ValueError) as exc:
        record.update(status="unavailable", error=str(exc))
    return record
