"""External OAuth token stores shared with the Codex CLI and the gptimage tool.

Both tools authenticate against ChatGPT via the same OAuth+PKCE flow
(auth.openai.com, client_id app_EMoamEEZ73f0CkXaXp7hrann) and persist the
resulting tokens to well-known files on disk:

    ~/.gptimage/auth.json   {"type":"oauth","access":...,"refresh":...,
                              "account_id":...,"expires":<epoch_ms>,...}
    ~/.codex/auth.json      {"auth_mode":"chatgpt","tokens":{"access_token":...,
                              "refresh_token":...,"account_id":...},...}

When banana-slides has no OAuth token of its own in the database, it can
reuse whichever of these is already logged in instead of requiring a
separate login. Reference implementation: gptimage's src/auth.js
(loadAuth / refreshTokens / writeBack).
"""
import base64
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
TOKEN_URL = "https://auth.openai.com/oauth/token"

GPTIMAGE_STORE = Path.home() / ".gptimage" / "auth.json"
CODEX_STORE = Path.home() / ".codex" / "auth.json"

_AUTH_CLAIM = "https://api.openai.com/auth"

# Refresh proactively this far ahead of expiry — mirrors the DB-token margin.
EXPIRY_MARGIN = timedelta(seconds=60)


def _decode_jwt_payload(token: str) -> Optional[dict]:
    """Decode a JWT's payload segment without verifying its signature (the backend does that)."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return None


def _account_id_from_token(access_token: str) -> Optional[str]:
    claims = _decode_jwt_payload(access_token)
    if not claims:
        return None
    return (claims.get(_AUTH_CLAIM) or {}).get("chatgpt_account_id")


def _expiry_from_token(access_token: str) -> Optional[datetime]:
    """Read the `exp` claim straight off the access token, as a naive UTC datetime."""
    claims = _decode_jwt_payload(access_token)
    exp = claims.get("exp") if claims else None
    if isinstance(exp, (int, float)):
        return datetime.fromtimestamp(exp, tz=timezone.utc).replace(tzinfo=None)
    return None


@dataclass
class ExternalOAuthRecord:
    access: str
    refresh: Optional[str]
    account_id: Optional[str]
    expires: Optional[datetime]  # naive UTC, or None if unknown
    store: Path
    format: str  # 'gptimage' | 'codex' — which file/shape this came from


def _read_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _normalize_gptimage(data: dict, store: Path) -> Optional["ExternalOAuthRecord"]:
    access = data.get("access")
    if not access:
        return None
    expires_ms = data.get("expires")
    expires = (
        datetime.fromtimestamp(expires_ms / 1000, tz=timezone.utc).replace(tzinfo=None)
        if isinstance(expires_ms, (int, float)) else _expiry_from_token(access)
    )
    return ExternalOAuthRecord(
        access=access,
        refresh=data.get("refresh"),
        account_id=data.get("account_id") or _account_id_from_token(access),
        expires=expires,
        store=store,
        format="gptimage",
    )


def _normalize_codex(data: dict, store: Path) -> Optional["ExternalOAuthRecord"]:
    tokens = (data or {}).get("tokens") or {}
    access = tokens.get("access_token")
    if not access:
        return None
    return ExternalOAuthRecord(
        access=access,
        refresh=tokens.get("refresh_token"),
        account_id=tokens.get("account_id") or _account_id_from_token(access),
        expires=_expiry_from_token(access),
        store=store,
        format="codex",
    )


def load_external_oauth() -> Optional[ExternalOAuthRecord]:
    """Return the first usable external OAuth record: gptimage's store, then the Codex CLI's."""
    data = _read_json(GPTIMAGE_STORE)
    if data:
        record = _normalize_gptimage(data, GPTIMAGE_STORE)
        if record:
            return record
    data = _read_json(CODEX_STORE)
    if data:
        record = _normalize_codex(data, CODEX_STORE)
        if record:
            return record
    return None


def is_expiring(record: ExternalOAuthRecord) -> bool:
    """True if the token is expired or within the refresh margin. Unknown expiry -> assume usable."""
    if record.expires is None:
        return False
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return record.expires < now + EXPIRY_MARGIN


def refresh_external_token(record: ExternalOAuthRecord) -> Optional[ExternalOAuthRecord]:
    """Refresh an expiring external token and write the rotated tokens back to its
    SOURCE FILE, preserving that file's own format. Never touches our database —
    this credential belongs to whichever external tool logged it in."""
    if not record.refresh:
        return None
    import requests

    try:
        resp = requests.post(
            TOKEN_URL,
            data=urlencode({
                "grant_type": "refresh_token",
                "refresh_token": record.refresh,
                "client_id": CLIENT_ID,
            }),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        logger.warning("External OAuth token refresh failed (%s): %s", record.store, exc)
        return None

    new_access = payload.get("access_token")
    if not new_access:
        logger.warning("External OAuth refresh response missing access_token (%s)", record.store)
        return None
    new_refresh = payload.get("refresh_token") or record.refresh
    expires_in = payload.get("expires_in")
    new_expires = (
        datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=expires_in)
        if isinstance(expires_in, (int, float)) else _expiry_from_token(new_access)
    )
    updated = ExternalOAuthRecord(
        access=new_access,
        refresh=new_refresh,
        account_id=record.account_id or _account_id_from_token(new_access),
        expires=new_expires,
        store=record.store,
        format=record.format,
    )
    _write_back(updated)
    return updated


def _write_back(record: ExternalOAuthRecord) -> None:
    """Persist rotated tokens to the record's own source file, in that file's own format."""
    try:
        record.store.parent.mkdir(parents=True, exist_ok=True)
        now_iso = datetime.now(timezone.utc).isoformat()
        if record.format == "codex":
            existing = _read_json(record.store) or {
                "auth_mode": "chatgpt", "OPENAI_API_KEY": None, "tokens": {},
            }
            existing["tokens"] = {
                **(existing.get("tokens") or {}),
                "access_token": record.access,
                "refresh_token": record.refresh,
                "account_id": record.account_id,
            }
            existing["last_refresh"] = now_iso
            record.store.write_text(json.dumps(existing, indent=2))
        else:
            expires_ms = (
                int(record.expires.replace(tzinfo=timezone.utc).timestamp() * 1000)
                if record.expires else None
            )
            payload = {
                "type": "oauth",
                "access": record.access,
                "refresh": record.refresh,
                "account_id": record.account_id,
                "expires": expires_ms,
                "last_refresh": now_iso,
            }
            record.store.write_text(json.dumps(payload, indent=2))
        os.chmod(record.store, 0o600)
    except Exception as exc:
        logger.warning("Failed to write back refreshed external OAuth token to %s: %s", record.store, exc)
