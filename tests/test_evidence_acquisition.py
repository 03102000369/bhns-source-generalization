"""Synthetic HTTP bytes exercise immutable retrieval, never astronomical intake."""

import io

import pytest

from bhns.data import acquisition


class SyntheticResponse(io.BytesIO):
    status = 200
    url = "https://example.invalid/SYNTHETIC"
    headers = {"Content-Type": "application/octet-stream"}


def test_download_bytes_and_checksum_are_bound_and_immutable(tmp_path, monkeypatch):
    monkeypatch.setattr(acquisition, "urlopen", lambda *a, **k: SyntheticResponse(b"SYNTHETIC"))
    first = acquisition.retrieve_evidence(SyntheticResponse.url, tmp_path, "test")
    second = acquisition.retrieve_evidence(SyntheticResponse.url, tmp_path, "test", expected_sha256=first["sha256"])
    assert first["status"] == second["status"] == "retrieved"
    assert first["path"] == second["path"] and len(list(tmp_path.iterdir())) == 1
    monkeypatch.setattr(acquisition, "urlopen", lambda *a, **k: SyntheticResponse(b"CHANGED SYNTHETIC"))
    bad = acquisition.retrieve_evidence(SyntheticResponse.url, tmp_path, "test", expected_sha256=first["sha256"])
    assert bad["status"] == "unavailable" and len(list(tmp_path.iterdir())) == 1


def test_download_size_limit_prevents_write(tmp_path, monkeypatch):
    monkeypatch.setattr(acquisition, "urlopen", lambda *a, **k: SyntheticResponse(b"SYNTHETIC"))
    record = acquisition.retrieve_evidence(SyntheticResponse.url, tmp_path, "test", max_bytes=3)
    assert record["status"] == "unavailable" and not list(tmp_path.iterdir())


@pytest.mark.parametrize("url,tag", [("http://example.invalid", "test"), ("https://example.invalid", "../test")])
def test_unsafe_acquisition_arguments_rejected(tmp_path, url, tag):
    with pytest.raises(ValueError):
        acquisition.retrieve_evidence(url, tmp_path, tag)
