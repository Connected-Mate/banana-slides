"""
Codex OAuth image provider — uses the ChatGPT Responses API with image_generation tool.

Endpoint: POST https://chatgpt.com/backend-api/codex/responses
Auth:     Bearer <oauth_access_token>

Image generation is done by sending a Responses API request with
tools=[{"type": "image_generation", ...}] and tool_choice={"type": "image_generation"}.
The result contains a base64-encoded image in the output.
"""
import base64
import io
import json
import logging
import os
from io import BytesIO
from typing import Optional, List

import requests as http_requests
from PIL import Image
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from .base import ImageProvider
from .openai_provider import _compute_gpt_image_size

logger = logging.getLogger(__name__)

_CODEX_BASE_URL = "https://chatgpt.com/backend-api/codex"
_RESPONSES_ENDPOINT = f"{_CODEX_BASE_URL}/responses"

# (connect, read) timeout — a scalar timeout only bounds the read, and a stalled
# write on a slow/congested connection would otherwise hang indefinitely.
_DEFAULT_TIMEOUT = (30, 300)

# Outer Responses-API model that orchestrates the image_generation tool call.
# Distinct from the image_generation tool's own `model` (e.g. gpt-image-2).
# Override with CODEX_OUTER_MODEL if OpenAI rotates the subscription model name.
_OUTER_MODEL = os.getenv('CODEX_OUTER_MODEL', 'gpt-5.5')

# Full-resolution reference images encoded as PNG were a major contributor to
# request timeouts against the Codex backend. Downscale to this many px on the
# long side and re-encode as JPEG before sending.
_MAX_REF_IMAGE_DIMENSION = int(os.getenv('CODEX_MAX_REF_IMAGE_DIMENSION', '1568'))
_REF_IMAGE_JPEG_QUALITY = int(os.getenv('CODEX_REF_IMAGE_JPEG_QUALITY', '85'))

# Client identifier sent to the backend. Matches the official Codex CLI.
_ORIGINATOR = os.getenv('CODEX_ORIGINATOR', 'codex_cli_rs')

_AUTH_CLAIM = "https://api.openai.com/auth"


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
    """Extract the chatgpt_account_id claim used for the chatgpt-account-id header."""
    claims = _decode_jwt_payload(access_token)
    if not claims:
        return None
    return (claims.get(_AUTH_CLAIM) or {}).get("chatgpt_account_id")


def _is_retryable_http_error(exc: BaseException) -> bool:
    """Return True for transient HTTP/network errors worth retrying."""
    if isinstance(exc, http_requests.exceptions.HTTPError) and exc.response is not None:
        return exc.response.status_code in (429, 500, 502, 503, 504)
    if isinstance(exc, (
        http_requests.exceptions.SSLError,
        http_requests.exceptions.ConnectionError,
        http_requests.exceptions.Timeout,
        http_requests.exceptions.ChunkedEncodingError,
    )):
        return True
    return False


def _downscale_and_encode_ref_image(img: Image.Image) -> tuple[str, dict]:
    """Downscale a reference image to at most _MAX_REF_IMAGE_DIMENSION px on its
    long side and encode as JPEG instead of full-resolution PNG.

    Returns (data_url, stats) where stats carries before/after dimensions and
    byte sizes for logging.
    """
    original_size = img.size
    baseline_buf = io.BytesIO()
    img.save(baseline_buf, format="PNG")
    baseline_bytes = len(baseline_buf.getvalue())

    working = img
    if working.mode in ('RGBA', 'LA', 'P'):
        # Flatten transparency onto white — JPEG has no alpha channel.
        bg = Image.new('RGB', working.size, (255, 255, 255))
        bg.paste(working, mask=working.split()[-1] if working.mode in ('RGBA', 'LA') else None)
        working = bg
    elif working.mode not in ('RGB', 'L'):
        working = working.convert('RGB')

    if max(working.size) > _MAX_REF_IMAGE_DIMENSION:
        working = working.copy()
        working.thumbnail((_MAX_REF_IMAGE_DIMENSION, _MAX_REF_IMAGE_DIMENSION), Image.Resampling.LANCZOS)

    out_buf = io.BytesIO()
    working.save(out_buf, format="JPEG", quality=_REF_IMAGE_JPEG_QUALITY)
    out_bytes = out_buf.getvalue()

    stats = {
        'original_size': original_size,
        'new_size': working.size,
        'original_bytes': baseline_bytes,
        'new_bytes': len(out_bytes),
    }
    b64 = base64.b64encode(out_bytes).decode('utf-8')
    return f"data:image/jpeg;base64,{b64}", stats


def _log_codex_retry(retry_state):
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    status = getattr(getattr(exc, 'response', None), 'status_code', '?')
    exc_type = type(exc).__name__ if exc else 'UnknownError'
    logger.warning(
        "Codex image request failed (%s, HTTP %s), retrying %d/%d: %s",
        exc_type, status, retry_state.attempt_number, 5, exc,
    )


class CodexImageProvider(ImageProvider):
    """Image generation via the ChatGPT Codex Responses API (OAuth)."""

    def __init__(self, api_key: str, model: str = "gpt-image-1", resolution: str = "2K"):
        """
        Args:
            api_key: OAuth access token.
            model:   The image model (e.g. gpt-image-1, gpt-image-2).
                     Used inside the image_generation tool definition.
            resolution: Target resolution (1K/2K/4K) for dynamic size calculation.
        """
        self.api_key = api_key
        self.image_model = model
        self.resolution = resolution

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "originator": _ORIGINATOR,
            "Accept": "text/event-stream",
        }
        account_id = _account_id_from_token(self.api_key)
        if account_id:
            headers["chatgpt-account-id"] = account_id
        return headers

    def _build_payload(self, prompt: str, aspect_ratio: str, ref_images: Optional[List[Image.Image]] = None, quality: str = "high", resolution: Optional[str] = None) -> dict:
        """Build a Responses API request with image_generation tool."""
        size = _compute_gpt_image_size(aspect_ratio, resolution or self.resolution)

        content = []
        if ref_images:
            for img in ref_images:
                data_url, stats = _downscale_and_encode_ref_image(img)
                content.append({"type": "input_image", "image_url": data_url})
                reduction_pct = (
                    100 * (1 - stats['new_bytes'] / stats['original_bytes'])
                    if stats['original_bytes'] else 0.0
                )
                logger.info(
                    "Codex ref image: %dx%d (%d bytes PNG) -> %dx%d (%d bytes JPEG q%d), %.0f%% smaller",
                    stats['original_size'][0], stats['original_size'][1], stats['original_bytes'],
                    stats['new_size'][0], stats['new_size'][1], stats['new_bytes'],
                    _REF_IMAGE_JPEG_QUALITY, reduction_pct,
                )
        content.append({"type": "input_text", "text": prompt})

        return {
            "model": _OUTER_MODEL,
            "instructions": "You are a helpful assistant that generates images.",
            "input": [{"role": "user", "content": content}],
            "tools": [
                {
                    "type": "image_generation",
                    "model": self.image_model,
                    "size": size,
                    "quality": quality,
                }
            ],
            "tool_choice": {"type": "image_generation"},
            "store": False,
            "stream": True,
        }

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        retry=retry_if_exception(_is_retryable_http_error),
        reraise=True,
        before_sleep=_log_codex_retry,
    )
    def generate_image(
        self,
        prompt: str,
        ref_images: Optional[List[Image.Image]] = None,
        aspect_ratio: str = "16:9",
        resolution: str = "2K",
        enable_thinking: bool = False,
        thinking_budget: int = 0,
    ) -> Optional[Image.Image]:
        """Generate an image via the Codex Responses API."""
        payload = self._build_payload(prompt, aspect_ratio, ref_images=ref_images, resolution=resolution)
        logger.debug(
            "Codex image request: image_model=%s, aspect=%s, resolution=%s, ref_images=%d",
            self.image_model, aspect_ratio, resolution, len(ref_images) if ref_images else 0,
        )

        resp = http_requests.post(
            _RESPONSES_ENDPOINT,
            headers=self._headers(),
            json=payload,
            timeout=_DEFAULT_TIMEOUT,
            stream=True,
        )
        resp.raise_for_status()

        return self._parse_sse_for_image(resp)

    # ------------------------------------------------------------------
    # SSE parsing
    # ------------------------------------------------------------------

    def _parse_sse_for_image(self, resp) -> Optional[Image.Image]:
        """Parse SSE stream and extract the generated image.

        The image appears in an output item of type ``image_generation_call``
        with a ``result`` field containing base64-encoded image data.
        We also handle the ``response.completed`` event which carries the
        full response object as a fallback.
        """
        completed_data = None

        for raw_line in resp.iter_lines():
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if not line or not line.startswith("data: "):
                continue
            raw = line[len("data: "):]
            if raw.strip() == "[DONE]":
                break
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue

            event_type = event.get("type", "")

            # Backend-side failure — surface its message instead of hanging until stream end.
            if event_type in ("response.failed", "error"):
                err = (event.get("response") or {}).get("error") or event.get("error") or {}
                message = (err or {}).get("message") or "unknown backend error"
                raise ValueError(f"Codex backend error: {message}")

            # Direct image result in a delta or output item event
            if event_type in (
                "response.output_item.done",
                "response.image_generation_call.done",
            ):
                item = event.get("item", event)
                img = self._try_extract_image(item)
                if img:
                    return img

            # Final completed event — contains the full response
            if event_type == "response.completed":
                completed_data = event.get("response", event)

        # Fallback: parse the completed response
        if completed_data:
            return self._extract_image_from_response(completed_data)

        raise ValueError("No image found in Codex Responses API stream")

    def _try_extract_image(self, item: dict) -> Optional[Image.Image]:
        """Try to decode an image from a single output item."""
        if item.get("type") == "image_generation_call":
            b64 = item.get("result")
            if b64:
                return self._decode_base64_image(b64)
        return None

    def _extract_image_from_response(self, data: dict) -> Optional[Image.Image]:
        """Extract image from the full response.completed payload."""
        for item in data.get("output", []):
            img = self._try_extract_image(item)
            if img:
                return img
        raise ValueError(
            "No image_generation_call found in Codex response output: "
            + str(data)[:500]
        )

    @staticmethod
    def _decode_base64_image(b64: str) -> Image.Image:
        """Decode a base64 string into a PIL Image."""
        # Strip data-URL prefix if present
        if b64.startswith("data:"):
            b64 = b64.split(",", 1)[1]
        image_data = base64.b64decode(b64)
        return Image.open(BytesIO(image_data))
