"""
Settings controller tests for provider format handling.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import requests
from flask import Flask

from controllers import settings_controller
from controllers.settings_controller import temporary_settings_override, update_settings, verify_api_key
from controllers.settings_controller import _sync_settings_to_config
from services import ai_providers


def _build_settings(**overrides):
    defaults = {
        'ai_provider_format': 'gemini',
        'api_key': None,
        'api_base_url': None,
        'text_model': None,
    }
    defaults.update(overrides)

    settings = SimpleNamespace(**defaults)
    settings.to_dict = lambda: {
        'ai_provider_format': settings.ai_provider_format,
        'api_key_length': len(settings.api_key) if settings.api_key else 0,
    }
    return settings


def test_get_test_image_path_prefers_pyinstaller_meipass(tmp_path, monkeypatch):
    """Packaged desktop builds should resolve bundled assets from sys._MEIPASS."""
    project_root = tmp_path / 'project'
    meipass_root = tmp_path / 'bundle'
    bundled_asset = meipass_root / 'assets' / 'test_img.png'
    bundled_asset.parent.mkdir(parents=True)
    bundled_asset.write_bytes(b'png')

    monkeypatch.setattr(settings_controller, 'PROJECT_ROOT', str(project_root))
    monkeypatch.setattr(settings_controller.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(settings_controller.sys, '_MEIPASS', str(meipass_root), raising=False)

    assert settings_controller._get_test_image_path() == bundled_asset


def _build_sync_settings(**overrides):
    defaults = {
        'ai_provider_format': 'gemini',
        'api_key': None,
        'api_base_url': None,
        'text_model': None,
        'image_model': None,
        'image_resolution': None,
        'image_aspect_ratio': None,
        'max_description_workers': None,
        'max_image_workers': None,
        'mineru_api_base': None,
        'mineru_token': None,
        'image_caption_model': None,
        'output_language': None,
        'enable_text_reasoning': False,
        'text_thinking_budget': 1024,
        'enable_image_reasoning': False,
        'image_thinking_budget': 1024,
        'baidu_api_key': None,
        'text_model_source': None,
        'image_model_source': None,
        'image_caption_model_source': None,
        'text_api_key': None,
        'text_api_base_url': None,
        'image_api_key': None,
        'image_api_base_url': None,
        'image_caption_api_key': None,
        'image_caption_api_base_url': None,
        'openai_image_api_protocol': None,
        'lazyllm_api_keys': None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_update_settings_accepts_lazyllm_provider():
    """`lazyllm` should be accepted as a valid provider format."""
    app = Flask(__name__)

    settings = _build_settings()
    with app.app_context():
        with app.test_request_context('/api/settings/', method='PUT', json={'ai_provider_format': 'lazyllm'}):
            with patch('controllers.settings_controller.Settings.get_settings', return_value=settings):
                with patch('controllers.settings_controller.db.session.commit'):
                    with patch('controllers.settings_controller._sync_settings_to_config'):
                        response, status_code = update_settings()

    assert status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['data']['ai_provider_format'] == 'lazyllm'


def test_update_settings_accepts_volcengine_provider():
    """`volcengine` should be accepted as a valid provider format."""
    app = Flask(__name__)

    settings = _build_settings()
    with app.app_context():
        with app.test_request_context('/api/settings/', method='PUT', json={'ai_provider_format': 'volcengine'}):
            with patch('controllers.settings_controller.Settings.get_settings', return_value=settings):
                with patch('controllers.settings_controller.db.session.commit'):
                    with patch('controllers.settings_controller._sync_settings_to_config'):
                        response, status_code = update_settings()

    assert status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['data']['ai_provider_format'] == 'volcengine'


def test_volcengine_text_provider_uses_modelark_openai_compatible_base():
    """Volcengine AgentPlans should reuse the OpenAI-compatible text provider."""
    app = Flask(__name__)
    app.config.update(
        AI_PROVIDER_FORMAT='volcengine',
        VOLCENGINE_API_KEY='volcengine-key',
        VOLCENGINE_API_BASE='https://ark.cn-beijing.volces.com/api/v3',
    )

    with app.app_context():
        with patch('services.ai_providers.OpenAITextProvider') as provider_cls:
            provider = ai_providers.get_text_provider(model='doubao-seed-2-0')

    assert provider == provider_cls.return_value
    provider_cls.assert_called_once_with(
        api_key='volcengine-key',
        api_base='https://ark.cn-beijing.volces.com/api/v3',
        model='doubao-seed-2-0',
    )


def test_volcengine_provider_does_not_fallback_to_gemini_key():
    """Volcengine should not send a Gemini key to an OpenAI-compatible endpoint."""
    app = Flask(__name__)
    app.config.update(
        AI_PROVIDER_FORMAT='volcengine',
        GOOGLE_API_KEY='gemini-key',
        OPENAI_API_KEY='',
        VOLCENGINE_API_KEY='',
        ARK_API_KEY='',
        VOLCENGINE_API_BASE='https://ark.cn-beijing.volces.com/api/v3',
    )

    with app.app_context():
        with pytest.raises(ValueError, match='AI_PROVIDER_FORMAT=volcengine'):
            ai_providers.get_text_provider(model='doubao-seed-2-0')


def test_volcengine_provider_does_not_fallback_to_openai_key():
    """Volcengine should not send an OpenAI key to the Volcengine endpoint."""
    app = Flask(__name__)
    app.config.update(
        AI_PROVIDER_FORMAT='volcengine',
        GOOGLE_API_KEY='',
        OPENAI_API_KEY='openai-key',
        VOLCENGINE_API_KEY='',
        ARK_API_KEY='',
        VOLCENGINE_API_BASE='https://ark.cn-beijing.volces.com/api/v3',
    )

    with app.app_context():
        with pytest.raises(ValueError, match='AI_PROVIDER_FORMAT=volcengine'):
            ai_providers.get_text_provider(model='doubao-seed-2-0')


def test_per_model_volcengine_source_does_not_fallback_to_openai_key():
    """Per-model Volcengine sources should require Volcengine/Ark credentials."""
    app = Flask(__name__)
    app.config.update(
        AI_PROVIDER_FORMAT='gemini',
        OPENAI_API_KEY='openai-key',
        VOLCENGINE_API_KEY='',
        ARK_API_KEY='',
        TEXT_API_KEY='',
        TEXT_MODEL_SOURCE='volcengine',
    )

    with app.app_context():
        with pytest.raises(ValueError, match='Volcengine AgentPlans'):
            ai_providers.get_text_provider(model='doubao-seed-2-0')


def test_settings_to_dict_uses_volcengine_defaults_for_selected_provider(monkeypatch):
    """Saved Volcengine selections should display ModelArk defaults from Config."""
    from config import Config
    from models.settings import Settings

    monkeypatch.setattr(Config, 'AI_PROVIDER_FORMAT', 'gemini')
    monkeypatch.setattr(Config, 'GOOGLE_API_BASE', 'https://generativelanguage.googleapis.com')
    monkeypatch.setattr(Config, 'GOOGLE_API_KEY', 'gemini-key')
    monkeypatch.setattr(Config, 'VOLCENGINE_API_BASE', 'https://custom-volc.example/api/v3')
    monkeypatch.setattr(Config, 'VOLCENGINE_API_KEY', 'volcengine-key')
    monkeypatch.setattr(Config, 'OPENAI_API_KEY', 'openai-key')

    settings = Settings(ai_provider_format='volcengine')
    data = settings.to_dict()

    assert data['api_base_url'] == 'https://custom-volc.example/api/v3'
    assert data['api_key_length'] == len('volcengine-key')
    assert data['text_api_base_url'] is None
    assert data['image_api_base_url'] is None
    assert data['image_caption_api_base_url'] is None


def test_settings_to_dict_volcengine_defaults_do_not_use_openai_key(monkeypatch):
    """Settings should not present an OpenAI key as a Volcengine key."""
    from config import Config
    from models.settings import Settings

    monkeypatch.setattr(Config, 'AI_PROVIDER_FORMAT', 'gemini')
    monkeypatch.setattr(Config, 'GOOGLE_API_BASE', 'https://generativelanguage.googleapis.com')
    monkeypatch.setattr(Config, 'GOOGLE_API_KEY', 'gemini-key')
    monkeypatch.setattr(Config, 'VOLCENGINE_API_BASE', 'https://custom-volc.example/api/v3')
    monkeypatch.setattr(Config, 'VOLCENGINE_API_KEY', '')
    monkeypatch.setattr(Config, 'OPENAI_API_KEY', 'openai-key')

    settings = Settings(ai_provider_format='volcengine')
    data = settings.to_dict()

    assert data['api_base_url'] == 'https://custom-volc.example/api/v3'
    assert data['api_key_length'] == 0


def test_settings_to_dict_uses_volcengine_defaults_for_per_model_source(monkeypatch):
    """Per-model Volcengine selections should display ModelArk defaults for that row only."""
    from config import Config
    from models.settings import Settings

    monkeypatch.setattr(Config, 'AI_PROVIDER_FORMAT', 'gemini')
    monkeypatch.setattr(Config, 'GOOGLE_API_BASE', 'https://generativelanguage.googleapis.com')
    monkeypatch.setattr(Config, 'GOOGLE_API_KEY', 'gemini-key')
    monkeypatch.setattr(Config, 'VOLCENGINE_API_BASE', 'https://custom-volc.example/api/v3')
    monkeypatch.setattr(Config, 'VOLCENGINE_API_KEY', 'volcengine-key')
    monkeypatch.setattr(Config, 'OPENAI_API_KEY', 'openai-key')

    settings = Settings(ai_provider_format='gemini', text_model_source='volcengine')
    data = settings.to_dict()

    assert data['api_base_url'] == 'https://generativelanguage.googleapis.com'
    assert data['text_api_base_url'] == 'https://custom-volc.example/api/v3'
    assert data['text_api_key_length'] == len('volcengine-key')
    assert data['image_api_base_url'] is None
    assert data['image_caption_api_base_url'] is None


def test_settings_to_dict_uses_specific_per_model_api_defaults(monkeypatch):
    """Per-model provider rows should prefer TEXT/IMAGE-specific env credentials."""
    from config import Config
    from models.settings import Settings

    monkeypatch.setattr(Config, 'AI_PROVIDER_FORMAT', 'gemini')
    monkeypatch.setattr(Config, 'GOOGLE_API_BASE', 'https://generativelanguage.googleapis.com')
    monkeypatch.setattr(Config, 'GOOGLE_API_KEY', 'gemini-key')
    monkeypatch.setattr(Config, 'VOLCENGINE_API_BASE', 'https://global-volc.example/api/v3')
    monkeypatch.setattr(Config, 'VOLCENGINE_API_KEY', 'global-volc-key')
    monkeypatch.setattr(Config, 'TEXT_API_BASE', 'https://text-volc.example/api/v3')
    monkeypatch.setattr(Config, 'TEXT_API_KEY', 'text-volc-key')

    settings = Settings(ai_provider_format='gemini', text_model_source='volcengine')
    data = settings.to_dict()

    assert data['text_api_base_url'] == 'https://text-volc.example/api/v3'
    assert data['text_api_key_length'] == len('text-volc-key')
    assert data['api_base_url'] == 'https://generativelanguage.googleapis.com'


def test_sync_settings_scopes_global_api_override_to_active_provider(monkeypatch):
    """Global Volcengine credentials must not pollute Gemini/OpenAI config used by per-model sources."""
    from config import Config

    monkeypatch.setattr(Config, 'AI_PROVIDER_FORMAT', 'gemini')
    monkeypatch.setattr(Config, 'GOOGLE_API_BASE', 'https://google-env.example')
    monkeypatch.setattr(Config, 'OPENAI_API_BASE', 'https://openai-env.example/v1')
    monkeypatch.setattr(Config, 'VOLCENGINE_API_BASE', 'https://volc-env.example/api/v3')
    monkeypatch.setattr(Config, 'GOOGLE_API_KEY', 'google-env-key')
    monkeypatch.setattr(Config, 'OPENAI_API_KEY', 'openai-env-key')
    monkeypatch.setattr(Config, 'VOLCENGINE_API_KEY', 'volc-env-key')

    app = Flask(__name__)
    app.config.update(
        AI_PROVIDER_FORMAT='gemini',
        GOOGLE_API_BASE='polluted-base',
        OPENAI_API_BASE='polluted-base',
        VOLCENGINE_API_BASE='polluted-base',
        GOOGLE_API_KEY='polluted-key',
        OPENAI_API_KEY='polluted-key',
        VOLCENGINE_API_KEY='polluted-key',
    )
    settings = _build_sync_settings(
        ai_provider_format='volcengine',
        api_base_url='https://volc-db.example/api/v3',
        api_key='volc-db-key',
        text_model_source='gemini',
    )

    with app.app_context():
        with patch('services.task_manager.sync_resource_limits'):
            with patch('services.ai_service_manager.clear_ai_service_cache'):
                _sync_settings_to_config(settings)

    assert app.config['GOOGLE_API_BASE'] == 'https://google-env.example'
    assert app.config['OPENAI_API_BASE'] == 'https://openai-env.example/v1'
    assert app.config['VOLCENGINE_API_BASE'] == 'https://volc-db.example/api/v3'
    assert app.config['GOOGLE_API_KEY'] == 'google-env-key'
    assert app.config['OPENAI_API_KEY'] == 'openai-env-key'
    assert app.config['VOLCENGINE_API_KEY'] == 'volc-db-key'
    assert app.config['TEXT_MODEL_SOURCE'] == 'gemini'


def test_temporary_settings_override_scopes_global_api_override_to_active_provider():
    """Settings service tests should not temporarily route other providers through Volcengine."""
    app = Flask(__name__)
    app.config.update(
        AI_PROVIDER_FORMAT='gemini',
        GOOGLE_API_BASE='https://google-env.example',
        OPENAI_API_BASE='https://openai-env.example/v1',
        VOLCENGINE_API_BASE='https://volc-env.example/api/v3',
        GOOGLE_API_KEY='google-env-key',
        OPENAI_API_KEY='openai-env-key',
        VOLCENGINE_API_KEY='volc-env-key',
    )

    with app.app_context():
        with temporary_settings_override({
            'ai_provider_format': 'volcengine',
            'api_base_url': 'https://volc-test.example/api/v3',
            'api_key': 'volc-test-key',
        }):
            assert app.config['GOOGLE_API_BASE'] == 'https://google-env.example'
            assert app.config['OPENAI_API_BASE'] == 'https://openai-env.example/v1'
            assert app.config['VOLCENGINE_API_BASE'] == 'https://volc-test.example/api/v3'
            assert app.config['GOOGLE_API_KEY'] == 'google-env-key'
            assert app.config['OPENAI_API_KEY'] == 'openai-env-key'
            assert app.config['VOLCENGINE_API_KEY'] == 'volc-test-key'

        assert app.config['VOLCENGINE_API_BASE'] == 'https://volc-env.example/api/v3'
        assert app.config['VOLCENGINE_API_KEY'] == 'volc-env-key'


def test_verify_uses_configured_text_model():
    """Verify endpoint should use configured text model, not a hardcoded gemini model."""
    app = Flask(__name__)
    app.config.update(
        TEXT_MODEL='gemini-3-flash-preview',
        AI_PROVIDER_FORMAT='lazyllm',
    )

    settings = _build_settings(ai_provider_format='lazyllm', text_model='deepseek-chat')
    mock_provider = MagicMock()
    mock_provider.generate_text.return_value = 'OK'

    with app.app_context():
        with app.test_request_context('/api/settings/verify', method='POST'):
            with patch('controllers.settings_controller.Settings.get_settings', return_value=settings):
                with patch('services.ai_providers.get_text_provider', return_value=mock_provider) as mock_get_provider:
                    response, status_code = verify_api_key()

    assert status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['data']['available'] is True
    mock_get_provider.assert_called_once_with(model='deepseek-chat')
    mock_provider.generate_text.assert_called_once()


def test_codex_401_settings_test_disconnects_oauth_and_reports_state(client, app):
    """A Codex 401 during settings tests should clear stale OAuth state."""
    with app.app_context():
        from models import Settings, Task, db

        settings = Settings.get_settings()
        settings.openai_oauth_access_token = 'expired-access-token'
        settings.openai_oauth_refresh_token = 'expired-refresh-token'
        settings.openai_oauth_account_id = 'user@example.com'
        task = Task(
            project_id='settings-test',
            task_type='TEST_TEXT_MODEL',
            status='PENDING',
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id

        response = requests.Response()
        response.status_code = 401
        response.url = 'https://chatgpt.com/backend-api/codex/responses'
        error = requests.exceptions.HTTPError(
            '401 Client Error: Unauthorized for url: https://chatgpt.com/backend-api/codex/responses',
            response=response,
        )

        def fail_with_codex_401():
            raise error

        with patch.dict(settings_controller.TEST_FUNCTIONS, {'text-model': fail_with_codex_401}):
            settings_controller._run_test_async(
                task_id,
                'text-model',
                {'text_model_source': 'codex'},
                app,
            )

        db.session.expire_all()
        settings = Settings.get_settings()
        assert settings.openai_oauth_access_token is None
        assert settings.openai_oauth_refresh_token is None
        assert settings.openai_oauth_account_id is None

    status_response = client.get(f'/api/settings/tests/{task_id}/status')
    assert status_response.status_code == 200
    data = status_response.get_json()
    assert data['success'] is True
    assert data['data']['status'] == 'FAILED'
    assert data['data']['openai_oauth_disconnected'] is True
    assert 'log in to OpenAI again' in data['data']['error']


@pytest.mark.parametrize(
    ('test_name', 'source_key', 'task_type'),
    [
        ('text-model', 'text_model_source', 'TEST_TEXT_MODEL'),
        ('image-model', 'image_model_source', 'TEST_IMAGE_MODEL'),
        ('caption-model', 'image_caption_model_source', 'TEST_CAPTION_MODEL'),
    ],
)
def test_codex_oauth_not_connected_settings_test_disconnects_oauth_and_reports_state(
    client,
    app,
    test_name,
    source_key,
    task_type,
):
    """A Codex settings test should sync OAuth state when no token can be loaded."""
    with app.app_context():
        from models import Settings, Task, db

        settings = Settings.get_settings()
        settings.openai_oauth_access_token = 'stale-access-token'
        settings.openai_oauth_refresh_token = 'stale-refresh-token'
        settings.openai_oauth_account_id = 'user@example.com'
        task = Task(
            project_id='settings-test',
            task_type=task_type,
            status='PENDING',
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id

        def fail_with_missing_codex_oauth():
            raise ValueError(
                'OpenAI OAuth is not connected. Please log in with your OpenAI account in Settings.'
            )

        with patch.dict(settings_controller.TEST_FUNCTIONS, {test_name: fail_with_missing_codex_oauth}):
            settings_controller._run_test_async(
                task_id,
                test_name,
                {source_key: 'codex'},
                app,
            )

        db.session.expire_all()
        settings = Settings.get_settings()
        assert settings.openai_oauth_access_token is None
        assert settings.openai_oauth_refresh_token is None
        assert settings.openai_oauth_account_id is None

    status_response = client.get(f'/api/settings/tests/{task_id}/status')
    assert status_response.status_code == 200
    data = status_response.get_json()
    assert data['success'] is True
    assert data['data']['status'] == 'FAILED'
    assert data['data']['openai_oauth_disconnected'] is True
    assert 'log in to OpenAI again' in data['data']['error']


def test_non_codex_oauth_not_connected_error_does_not_disconnect_codex_oauth(client, app):
    """The local OAuth-not-connected text should only clear OAuth for Codex tests."""
    with app.app_context():
        from models import Settings, Task, db

        settings = Settings.get_settings()
        settings.openai_oauth_access_token = 'still-valid-access-token'
        settings.openai_oauth_refresh_token = 'still-valid-refresh-token'
        settings.openai_oauth_account_id = 'user@example.com'
        task = Task(
            project_id='settings-test',
            task_type='TEST_TEXT_MODEL',
            status='PENDING',
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id

        def fail_with_missing_oauth_text():
            raise ValueError(
                'OpenAI OAuth is not connected. Please log in with your OpenAI account in Settings.'
            )

        with patch.dict(settings_controller.TEST_FUNCTIONS, {'text-model': fail_with_missing_oauth_text}):
            settings_controller._run_test_async(
                task_id,
                'text-model',
                {'text_model_source': 'gemini'},
                app,
            )

        db.session.expire_all()
        settings = Settings.get_settings()
        assert settings.openai_oauth_access_token == 'still-valid-access-token'
        assert settings.openai_oauth_refresh_token == 'still-valid-refresh-token'
        assert settings.openai_oauth_account_id == 'user@example.com'

    status_response = client.get(f'/api/settings/tests/{task_id}/status')
    assert status_response.status_code == 200
    data = status_response.get_json()
    assert data['success'] is True
    assert data['data']['status'] == 'FAILED'
    assert 'openai_oauth_disconnected' not in data['data']


def test_unrelated_401_settings_test_does_not_disconnect_codex_oauth(client, app):
    """A non-Codex service test should not clear OAuth just because Codex is configured globally."""
    with app.app_context():
        from models import Settings, Task, db

        settings = Settings.get_settings()
        settings.openai_oauth_access_token = 'still-valid-access-token'
        settings.openai_oauth_refresh_token = 'still-valid-refresh-token'
        settings.openai_oauth_account_id = 'user@example.com'
        task = Task(
            project_id='settings-test',
            task_type='TEST_BAIDU_OCR',
            status='PENDING',
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id

        response = requests.Response()
        response.status_code = 401
        error = requests.exceptions.HTTPError(
            '401 Client Error: Unauthorized for url: https://example.com/ocr',
            response=response,
        )

        def fail_with_unrelated_401():
            raise error

        with patch.dict(settings_controller.TEST_FUNCTIONS, {'baidu-ocr': fail_with_unrelated_401}):
            settings_controller._run_test_async(
                task_id,
                'baidu-ocr',
                {'ai_provider_format': 'codex'},
                app,
            )

        db.session.expire_all()
        settings = Settings.get_settings()
        assert settings.openai_oauth_access_token == 'still-valid-access-token'
        assert settings.openai_oauth_refresh_token == 'still-valid-refresh-token'
        assert settings.openai_oauth_account_id == 'user@example.com'

    status_response = client.get(f'/api/settings/tests/{task_id}/status')
    assert status_response.status_code == 200
    data = status_response.get_json()
    assert data['success'] is True
    assert data['data']['status'] == 'FAILED'
    assert 'openai_oauth_disconnected' not in data['data']


def test_codex_test_error_text_with_4010_does_not_disconnect_oauth(client, app):
    """A non-401 number in error text should not be treated as an OAuth 401."""
    with app.app_context():
        from models import Settings, Task, db

        settings = Settings.get_settings()
        settings.openai_oauth_access_token = 'still-valid-access-token'
        settings.openai_oauth_refresh_token = 'still-valid-refresh-token'
        settings.openai_oauth_account_id = 'user@example.com'
        task = Task(
            project_id='settings-test',
            task_type='TEST_TEXT_MODEL',
            status='PENDING',
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id

        def fail_with_port_number():
            raise ValueError('Connection failed to http://localhost:4010/codex-proxy')

        with patch.dict(settings_controller.TEST_FUNCTIONS, {'text-model': fail_with_port_number}):
            settings_controller._run_test_async(
                task_id,
                'text-model',
                {'text_model_source': 'codex'},
                app,
            )

        db.session.expire_all()
        settings = Settings.get_settings()
        assert settings.openai_oauth_access_token == 'still-valid-access-token'
        assert settings.openai_oauth_refresh_token == 'still-valid-refresh-token'
        assert settings.openai_oauth_account_id == 'user@example.com'

    status_response = client.get(f'/api/settings/tests/{task_id}/status')
    data = status_response.get_json()
    assert data['data']['status'] == 'FAILED'
    assert 'openai_oauth_disconnected' not in data['data']


def test_codex_text_provider_substitutes_stale_gemini_model():
    """A leftover Gemini text model under format=codex should fall back to gpt-5.5."""
    app = Flask(__name__)
    app.config.update(AI_PROVIDER_FORMAT='codex')

    with app.app_context():
        with patch('services.ai_providers._get_openai_oauth_token', return_value='oauth-token'):
            with patch('services.ai_providers.CodexTextProvider') as provider_cls:
                provider = ai_providers.get_text_provider(model='gemini-3-flash-preview')

    assert provider == provider_cls.return_value
    provider_cls.assert_called_once_with(api_key='oauth-token', model='gpt-5.5')


def test_codex_image_provider_substitutes_stale_gemini_model():
    """A leftover Gemini image model under format=codex should fall back to gpt-image-2."""
    app = Flask(__name__)
    app.config.update(AI_PROVIDER_FORMAT='codex', DEFAULT_RESOLUTION='2K')

    with app.app_context():
        with patch('services.ai_providers._get_openai_oauth_token', return_value='oauth-token'):
            with patch('services.ai_providers.CodexImageProvider') as provider_cls:
                provider = ai_providers.get_image_provider(model='gemini-3-pro-image-preview')

    assert provider == provider_cls.return_value
    provider_cls.assert_called_once_with(api_key='oauth-token', model='gpt-image-2', resolution='2K')


def test_codex_text_provider_keeps_explicit_non_gemini_model():
    """A genuine ChatGPT model name for Codex must pass through untouched."""
    app = Flask(__name__)
    app.config.update(AI_PROVIDER_FORMAT='codex')

    with app.app_context():
        with patch('services.ai_providers._get_openai_oauth_token', return_value='oauth-token'):
            with patch('services.ai_providers.CodexTextProvider') as provider_cls:
                ai_providers.get_text_provider(model='gpt-5.4-mini')

    provider_cls.assert_called_once_with(api_key='oauth-token', model='gpt-5.4-mini')


def test_get_openai_oauth_token_refreshes_within_60s_margin(client, app):
    """A token expiring in <60s should be refreshed proactively, not handed out as-is."""
    with app.app_context():
        from datetime import timedelta
        from models import Settings, db
        from models.settings import _utcnow_naive

        settings = Settings.get_settings()
        settings.openai_oauth_access_token = 'stale-access-token'
        settings.openai_oauth_refresh_token = 'refresh-token'
        settings.openai_oauth_expires_at = _utcnow_naive() + timedelta(seconds=30)
        db.session.commit()

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {'access_token': 'refreshed-token', 'expires_in': 3600}
        with patch('requests.post', return_value=mock_resp) as mock_post:
            token = settings.get_openai_oauth_token()

        assert token == 'refreshed-token'
        mock_post.assert_called_once()


def test_get_openai_oauth_token_returns_as_is_when_outside_margin(client, app):
    """A token with plenty of time left should be returned without refreshing."""
    with app.app_context():
        from datetime import timedelta
        from models import Settings, db
        from models.settings import _utcnow_naive

        settings = Settings.get_settings()
        settings.openai_oauth_access_token = 'still-fresh-token'
        settings.openai_oauth_refresh_token = 'refresh-token'
        settings.openai_oauth_expires_at = _utcnow_naive() + timedelta(minutes=30)
        db.session.commit()

        with patch('requests.post') as mock_post:
            token = settings.get_openai_oauth_token()

        assert token == 'still-fresh-token'
        mock_post.assert_not_called()


def test_refresh_network_error_logs_warning(client, app, caplog):
    """A failed OAuth refresh (network error) should log a warning instead of failing silently."""
    with app.app_context():
        import logging
        from datetime import timedelta
        from models import Settings, db
        from models.settings import _utcnow_naive

        settings = Settings.get_settings()
        settings.openai_oauth_access_token = 'expired-token'
        settings.openai_oauth_refresh_token = 'refresh-token'
        settings.openai_oauth_expires_at = _utcnow_naive() - timedelta(seconds=5)
        db.session.commit()

        with patch('requests.post', side_effect=requests.exceptions.ConnectionError('network down')):
            with caplog.at_level(logging.WARNING, logger='models.settings'):
                token = settings.get_openai_oauth_token()

        assert token is None
        assert any('OpenAI OAuth token refresh failed' in r.message for r in caplog.records)


def test_refresh_401_logs_warning_and_clears_oauth(client, app, caplog):
    """A 401 from token refresh should log a warning AND clear stored OAuth credentials."""
    with app.app_context():
        import logging
        from datetime import timedelta
        from models import Settings, db
        from models.settings import _utcnow_naive

        settings = Settings.get_settings()
        settings.openai_oauth_access_token = 'expired-token'
        settings.openai_oauth_refresh_token = 'refresh-token'
        settings.openai_oauth_expires_at = _utcnow_naive() - timedelta(seconds=5)
        db.session.commit()

        resp = MagicMock()
        resp.status_code = 401
        http_err = requests.exceptions.HTTPError(response=resp)
        with patch('requests.post', side_effect=http_err):
            with caplog.at_level(logging.WARNING, logger='models.settings'):
                token = settings.get_openai_oauth_token()

        assert token is None
        assert settings.openai_oauth_access_token is None
        assert any('OpenAI OAuth token refresh failed' in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# External OAuth store fallback (~/.gptimage, ~/.codex) — priority & disconnect
#
# These patch utils.external_oauth_stores.* directly rather than touching real
# files: settings.py's fallback is exercised in isolation here, while the file
# I/O itself is covered by test_external_oauth_stores.py.
# ---------------------------------------------------------------------------

def _external_record(**overrides):
    from utils.external_oauth_stores import ExternalOAuthRecord
    defaults = dict(
        access='ext-access-token', refresh='ext-refresh-token',
        account_id='acct_ext', expires=None, store='irrelevant', format='gptimage',
    )
    defaults.update(overrides)
    return ExternalOAuthRecord(**defaults)


def test_get_openai_oauth_token_falls_back_to_external_when_db_empty(client, app):
    """No DB token -> use whatever external store (gptimage/codex) is logged in."""
    with app.app_context():
        from models import Settings, db

        settings = Settings.get_settings()
        settings.openai_oauth_access_token = None
        db.session.commit()

        with patch('utils.external_oauth_stores.load_external_oauth', return_value=_external_record()):
            token = settings.get_openai_oauth_token()

        assert token == 'ext-access-token'


def test_get_openai_oauth_token_db_token_takes_priority_over_external(client, app):
    """A DB token must win even if an external store also has one — external is never consulted."""
    with app.app_context():
        from datetime import timedelta
        from models import Settings, db
        from models.settings import _utcnow_naive

        settings = Settings.get_settings()
        settings.openai_oauth_access_token = 'db-token'
        settings.openai_oauth_refresh_token = 'db-refresh'
        settings.openai_oauth_expires_at = _utcnow_naive() + timedelta(hours=1)
        db.session.commit()

        with patch('utils.external_oauth_stores.load_external_oauth', return_value=_external_record()) as mock_load:
            token = settings.get_openai_oauth_token()

        assert token == 'db-token'
        mock_load.assert_not_called()


def test_get_openai_oauth_token_refreshes_expiring_external_token(client, app):
    """An expiring external token with a refresh token should be refreshed via the store helper."""
    with app.app_context():
        from models import Settings, db

        settings = Settings.get_settings()
        settings.openai_oauth_access_token = None
        db.session.commit()

        expiring = _external_record()
        refreshed = _external_record(access='ext-access-refreshed')
        with patch('utils.external_oauth_stores.load_external_oauth', return_value=expiring):
            with patch('utils.external_oauth_stores.is_expiring', return_value=True):
                with patch('utils.external_oauth_stores.refresh_external_token', return_value=refreshed) as mock_refresh:
                    token = settings.get_openai_oauth_token()

        assert token == 'ext-access-refreshed'
        mock_refresh.assert_called_once()


def test_get_openai_oauth_token_external_disabled_flag_blocks_fallback(client, app):
    """After an explicit disconnect, external stores must not be consulted at all."""
    with app.app_context():
        from models import Settings, db

        settings = Settings.get_settings()
        settings.openai_oauth_access_token = None
        settings.openai_oauth_external_disabled = True
        db.session.commit()

        with patch('utils.external_oauth_stores.load_external_oauth', return_value=_external_record()) as mock_load:
            token = settings.get_openai_oauth_token()

        assert token is None
        mock_load.assert_not_called()


def test_is_openai_oauth_connected_reflects_external_fallback(client, app):
    with app.app_context():
        from models import Settings, db

        settings = Settings.get_settings()
        settings.openai_oauth_access_token = None
        db.session.commit()

        with patch('utils.external_oauth_stores.load_external_oauth', return_value=_external_record()):
            assert settings.is_openai_oauth_connected() is True

        with patch('utils.external_oauth_stores.load_external_oauth', return_value=None):
            assert settings.is_openai_oauth_connected() is False


def test_get_openai_oauth_account_id_reflects_external_fallback(client, app):
    with app.app_context():
        from models import Settings, db

        settings = Settings.get_settings()
        settings.openai_oauth_access_token = None
        db.session.commit()

        with patch('utils.external_oauth_stores.load_external_oauth', return_value=_external_record(account_id='acct_ext_id')):
            assert settings.get_openai_oauth_account_id() == 'acct_ext_id'


def test_disconnect_openai_oauth_clears_db_sets_flag_and_blocks_external(client, app):
    """disconnect_openai_oauth() must not touch any file — it only clears DB state
    and sets the flag that makes the app stop consulting external stores."""
    with app.app_context():
        from datetime import timedelta
        from models import Settings, db
        from models.settings import _utcnow_naive

        settings = Settings.get_settings()
        settings.openai_oauth_access_token = 'db-token'
        settings.openai_oauth_refresh_token = 'db-refresh'
        settings.openai_oauth_expires_at = _utcnow_naive() + timedelta(hours=1)
        settings.openai_oauth_account_id = 'acct_db'
        settings.openai_oauth_external_disabled = False
        db.session.commit()

        settings.disconnect_openai_oauth()
        db.session.commit()

        assert settings.openai_oauth_access_token is None
        assert settings.openai_oauth_account_id is None
        assert settings.openai_oauth_external_disabled is True

        # Even though an external store is "available", disconnect must suppress it.
        with patch('utils.external_oauth_stores.load_external_oauth', return_value=_external_record()) as mock_load:
            assert settings.get_openai_oauth_token() is None
            assert settings.is_openai_oauth_connected() is False
        mock_load.assert_not_called()


# ---------------------------------------------------------------------------
# apply_codex_defaults_if_untouched — boot-time server-side equivalent of the
# frontend's applyCodexDefaultsIfUntouched (covers OAuth via DB *or* the
# external ~/.gptimage / ~/.codex fallback from task #10 — the gap the
# frontend-only version missed for desktop installs with no in-app login).
# ---------------------------------------------------------------------------

def test_apply_codex_defaults_when_db_connected_and_untouched(client, app):
    with app.app_context():
        from datetime import timedelta
        from models import Settings, db
        from models.settings import _utcnow_naive

        settings = Settings.get_settings()
        settings.openai_oauth_access_token = 'db-token'
        settings.openai_oauth_refresh_token = 'db-refresh'
        settings.openai_oauth_expires_at = _utcnow_naive() + timedelta(hours=1)
        settings.ai_provider_format = None
        settings.text_model = None
        settings.image_model = None
        settings.api_key = None
        db.session.commit()

        changed = settings.apply_codex_defaults_if_untouched()

        assert changed is True
        assert settings.ai_provider_format == 'codex'
        assert settings.text_model == 'gpt-5.5'
        assert settings.image_model == 'gpt-image-2'


def test_apply_codex_defaults_when_external_fallback_connected_and_untouched(client, app):
    """The exact real-world gap: desktop app connected only via ~/.gptimage or
    ~/.codex (no in-app OAuth token in DB), still gets Codex defaults at boot."""
    with app.app_context():
        from models import Settings, db

        settings = Settings.get_settings()
        settings.openai_oauth_access_token = None
        settings.ai_provider_format = None
        settings.text_model = None
        settings.image_model = None
        settings.api_key = None
        db.session.commit()

        with patch('utils.external_oauth_stores.load_external_oauth', return_value=_external_record()):
            changed = settings.apply_codex_defaults_if_untouched()

        assert changed is True
        assert settings.ai_provider_format == 'codex'
        assert settings.text_model == 'gpt-5.5'
        assert settings.image_model == 'gpt-image-2'


def test_apply_codex_defaults_is_noop_when_user_configured_explicitly(client, app):
    with app.app_context():
        from datetime import timedelta
        from models import Settings, db
        from models.settings import _utcnow_naive

        settings = Settings.get_settings()
        settings.openai_oauth_access_token = 'db-token'
        settings.openai_oauth_refresh_token = 'db-refresh'
        settings.openai_oauth_expires_at = _utcnow_naive() + timedelta(hours=1)
        settings.ai_provider_format = 'volcengine'  # user explicitly chose something else
        settings.text_model = None
        settings.image_model = None
        settings.api_key = None
        db.session.commit()

        changed = settings.apply_codex_defaults_if_untouched()

        assert changed is False
        assert settings.ai_provider_format == 'volcengine'
        assert settings.text_model is None
        assert settings.image_model is None


def test_apply_codex_defaults_is_noop_when_not_connected(client, app):
    with app.app_context():
        from models import Settings, db

        settings = Settings.get_settings()
        settings.openai_oauth_access_token = None
        settings.ai_provider_format = None
        settings.text_model = None
        settings.image_model = None
        settings.api_key = None
        db.session.commit()

        with patch('utils.external_oauth_stores.load_external_oauth', return_value=None):
            changed = settings.apply_codex_defaults_if_untouched()

        assert changed is False
        assert settings.ai_provider_format is None


def test_apply_codex_defaults_is_idempotent_second_call_is_noop(client, app):
    """Once applied, a later boot must not re-clobber a subsequent explicit user choice."""
    with app.app_context():
        from datetime import timedelta
        from models import Settings, db
        from models.settings import _utcnow_naive

        settings = Settings.get_settings()
        settings.openai_oauth_access_token = 'db-token'
        settings.openai_oauth_refresh_token = 'db-refresh'
        settings.openai_oauth_expires_at = _utcnow_naive() + timedelta(hours=1)
        settings.ai_provider_format = None
        settings.text_model = None
        settings.image_model = None
        settings.api_key = None
        db.session.commit()

        assert settings.apply_codex_defaults_if_untouched() is True

        # User then explicitly switches to something else.
        settings.ai_provider_format = 'openai'
        settings.text_model = 'gpt-4o'
        db.session.commit()

        assert settings.apply_codex_defaults_if_untouched() is False
        assert settings.ai_provider_format == 'openai'
        assert settings.text_model == 'gpt-4o'
