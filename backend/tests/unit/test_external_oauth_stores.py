"""Unit tests for external OAuth token store fallback (~/.gptimage, ~/.codex).

IMPORTANT: every test here monkeypatches GPTIMAGE_STORE/CODEX_STORE to a
tmp_path location. Never let a test touch the real ~/.gptimage/auth.json or
~/.codex/auth.json — those are real, shared ChatGPT logins on this machine.
"""
import base64
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from utils import external_oauth_stores as stores


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_jwt(payload: dict) -> str:
    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header = _b64url(b'{"alg":"none","typ":"JWT"}')
    body = _b64url(json.dumps(payload).encode())
    return f"{header}.{body}.sig"


@pytest.fixture(autouse=True)
def _isolate_stores(tmp_path, monkeypatch):
    """Redirect both stores into tmp_path for every test in this file."""
    monkeypatch.setattr(stores, "GPTIMAGE_STORE", tmp_path / ".gptimage" / "auth.json")
    monkeypatch.setattr(stores, "CODEX_STORE", tmp_path / ".codex" / "auth.json")
    return tmp_path


def _write_gptimage(path, **overrides):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "type": "oauth",
        "access": "gptimage-access-token",
        "refresh": "gptimage-refresh-token",
        "account_id": "acct_gptimage",
        "expires": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp() * 1000),
        "last_refresh": "2026-01-01T00:00:00Z",
    }
    data.update(overrides)
    path.write_text(json.dumps(data))
    return data


def _write_codex(path, **overrides):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "auth_mode": "chatgpt",
        "OPENAI_API_KEY": None,
        "tokens": {
            "access_token": "codex-access-token",
            "refresh_token": "codex-refresh-token",
            "account_id": "acct_codex",
        },
        "last_refresh": "2026-01-01T00:00:00Z",
    }
    data.update(overrides)
    path.write_text(json.dumps(data))
    return data


# ---------------------------------------------------------------------------
# load_external_oauth — priority & normalization
# ---------------------------------------------------------------------------

class TestLoadExternalOAuth:

    def test_returns_none_when_no_store_exists(self):
        assert stores.load_external_oauth() is None

    def test_reads_gptimage_store(self):
        _write_gptimage(stores.GPTIMAGE_STORE)
        record = stores.load_external_oauth()
        assert record.access == "gptimage-access-token"
        assert record.account_id == "acct_gptimage"
        assert record.format == "gptimage"

    def test_reads_codex_store_when_gptimage_absent(self):
        _write_codex(stores.CODEX_STORE)
        record = stores.load_external_oauth()
        assert record.access == "codex-access-token"
        assert record.account_id == "acct_codex"
        assert record.format == "codex"

    def test_gptimage_takes_priority_over_codex(self):
        _write_gptimage(stores.GPTIMAGE_STORE)
        _write_codex(stores.CODEX_STORE)
        record = stores.load_external_oauth()
        assert record.format == "gptimage"
        assert record.access == "gptimage-access-token"

    def test_falls_back_to_codex_when_gptimage_store_malformed(self):
        stores.GPTIMAGE_STORE.parent.mkdir(parents=True, exist_ok=True)
        stores.GPTIMAGE_STORE.write_text("not json")
        _write_codex(stores.CODEX_STORE)
        record = stores.load_external_oauth()
        assert record.format == "codex"

    def test_account_id_derived_from_jwt_when_missing_in_gptimage_file(self):
        token = _make_jwt({"https://api.openai.com/auth": {"chatgpt_account_id": "acct_from_jwt"}})
        _write_gptimage(stores.GPTIMAGE_STORE, access=token, account_id=None)
        record = stores.load_external_oauth()
        assert record.account_id == "acct_from_jwt"

    def test_expiry_derived_from_jwt_exp_claim_when_missing(self):
        future_exp = int((datetime.now(timezone.utc) + timedelta(hours=2)).timestamp())
        token = _make_jwt({"exp": future_exp})
        _write_gptimage(stores.GPTIMAGE_STORE, access=token, expires=None)
        record = stores.load_external_oauth()
        assert record.expires is not None
        assert record.expires > datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=59)


# ---------------------------------------------------------------------------
# is_expiring
# ---------------------------------------------------------------------------

class TestIsExpiring:

    def _record(self, expires):
        return stores.ExternalOAuthRecord(
            access="a", refresh="r", account_id="acct",
            expires=expires, store=stores.GPTIMAGE_STORE, format="gptimage",
        )

    def test_none_expiry_is_not_expiring(self):
        assert stores.is_expiring(self._record(None)) is False

    def test_far_future_is_not_expiring(self):
        expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
        assert stores.is_expiring(self._record(expires)) is False

    def test_within_60s_margin_is_expiring(self):
        expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=30)
        assert stores.is_expiring(self._record(expires)) is True

    def test_already_past_is_expiring(self):
        expires = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=5)
        assert stores.is_expiring(self._record(expires)) is True


# ---------------------------------------------------------------------------
# refresh_external_token — write-back preserves source file format
# ---------------------------------------------------------------------------

class TestRefreshExternalToken:

    def test_refresh_writes_back_gptimage_format(self):
        _write_gptimage(stores.GPTIMAGE_STORE)
        record = stores.load_external_oauth()

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "access_token": "new-gptimage-access",
            "refresh_token": "new-gptimage-refresh",
            "expires_in": 3600,
        }
        with patch("requests.post", return_value=mock_resp) as mock_post:
            updated = stores.refresh_external_token(record)

        assert updated.access == "new-gptimage-access"
        mock_post.assert_called_once()
        on_disk = json.loads(stores.GPTIMAGE_STORE.read_text())
        assert on_disk["type"] == "oauth"
        assert on_disk["access"] == "new-gptimage-access"
        assert on_disk["refresh"] == "new-gptimage-refresh"
        assert on_disk["account_id"] == "acct_gptimage"
        assert "last_refresh" in on_disk

    def test_refresh_writes_back_codex_format_preserving_other_fields(self):
        _write_codex(stores.CODEX_STORE)
        record = stores.load_external_oauth()

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "access_token": "new-codex-access",
            "refresh_token": "new-codex-refresh",
            "expires_in": 3600,
        }
        with patch("requests.post", return_value=mock_resp):
            updated = stores.refresh_external_token(record)

        assert updated.access == "new-codex-access"
        on_disk = json.loads(stores.CODEX_STORE.read_text())
        # Fields unrelated to the token rotation must survive untouched.
        assert on_disk["auth_mode"] == "chatgpt"
        assert on_disk["OPENAI_API_KEY"] is None
        assert on_disk["tokens"]["access_token"] == "new-codex-access"
        assert on_disk["tokens"]["refresh_token"] == "new-codex-refresh"
        assert on_disk["tokens"]["account_id"] == "acct_codex"

    def test_refresh_without_refresh_token_returns_none(self):
        _write_gptimage(stores.GPTIMAGE_STORE, refresh=None)
        record = stores.load_external_oauth()
        with patch("requests.post") as mock_post:
            result = stores.refresh_external_token(record)
        assert result is None
        mock_post.assert_not_called()

    def test_refresh_http_failure_returns_none_and_does_not_write(self):
        _write_gptimage(stores.GPTIMAGE_STORE)
        record = stores.load_external_oauth()
        original_bytes = stores.GPTIMAGE_STORE.read_bytes()

        with patch("requests.post", side_effect=ConnectionError("network down")):
            result = stores.refresh_external_token(record)

        assert result is None
        assert stores.GPTIMAGE_STORE.read_bytes() == original_bytes
