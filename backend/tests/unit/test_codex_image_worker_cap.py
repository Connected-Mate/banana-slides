"""Codex image worker concurrency cap — regression test for a real production
bug: MAX_IMAGE_WORKERS defaults to 20, but a single ChatGPT account can't
sustain 20 parallel image generations against the Codex backend, causing a
cascade of connection-timeout retries. When the effective image provider is
codex, image_resource_limiter's capacity must be capped independently of the
user's configured MAX_IMAGE_WORKERS.
"""
from unittest.mock import patch

import pytest

from services.task_manager import (
    CODEX_MAX_IMAGE_WORKERS,
    image_resource_limiter,
    sync_resource_limits,
    text_resource_limiter,
)


@pytest.fixture(autouse=True)
def restore_limiter_capacity():
    """sync_resource_limits mutates module-level singletons shared across the
    whole test session — restore capacities after every test."""
    original_image_capacity = image_resource_limiter.capacity
    original_text_capacity = text_resource_limiter.capacity
    yield
    image_resource_limiter.update_capacity(original_image_capacity)
    text_resource_limiter.update_capacity(original_text_capacity)


def test_codex_provider_caps_image_workers(client, app):
    with app.app_context():
        with patch('services.task_manager._effective_image_provider_format', return_value='codex'):
            sync_resource_limits(description_workers=5, image_workers=20)

    assert image_resource_limiter.capacity == CODEX_MAX_IMAGE_WORKERS
    assert CODEX_MAX_IMAGE_WORKERS == 2


def test_non_codex_provider_does_not_cap_image_workers(client, app):
    with app.app_context():
        with patch('services.task_manager._effective_image_provider_format', return_value='gemini'):
            sync_resource_limits(description_workers=5, image_workers=20)

    assert image_resource_limiter.capacity == 20


def test_codex_provider_does_not_cap_below_a_lower_user_setting(client, app):
    """If the user already configured fewer workers than the cap, don't raise it."""
    with app.app_context():
        with patch('services.task_manager._effective_image_provider_format', return_value='codex'):
            sync_resource_limits(description_workers=5, image_workers=1)

    assert image_resource_limiter.capacity == 1


def test_text_worker_capacity_is_never_capped_by_the_codex_image_rule(client, app):
    with app.app_context():
        with patch('services.task_manager._effective_image_provider_format', return_value='codex'):
            sync_resource_limits(description_workers=15, image_workers=20)

    assert text_resource_limiter.capacity == 15


def test_effective_image_provider_format_reads_image_model_source_override(app):
    with app.app_context():
        app.config['IMAGE_MODEL_SOURCE'] = 'codex'
        app.config['AI_PROVIDER_FORMAT'] = 'gemini'
        from services.task_manager import _effective_image_provider_format
        try:
            assert _effective_image_provider_format() == 'codex'
        finally:
            app.config.pop('IMAGE_MODEL_SOURCE', None)


def test_effective_image_provider_format_falls_back_to_global_format(app):
    with app.app_context():
        app.config.pop('IMAGE_MODEL_SOURCE', None)
        app.config['AI_PROVIDER_FORMAT'] = 'gemini'
        from services.task_manager import _effective_image_provider_format
        assert _effective_image_provider_format() == 'gemini'
