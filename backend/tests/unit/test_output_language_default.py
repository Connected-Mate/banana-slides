"""Output language default should be 'en', not 'zh' — regression test for a
real bug found in manual testing: an English prompt produced a Chinese
outline because every fallback in the pipeline defaulted to 'zh'. An
explicit user choice (DB setting, or an explicit `language` argument) must
always be respected unchanged.
"""
from config import Config
from services.prompts import (
    get_default_output_language,
    get_language_instruction,
    get_ppt_language_instruction,
    LANGUAGE_CONFIG,
)


def test_config_output_language_defaults_to_en():
    assert Config.OUTPUT_LANGUAGE == 'en'


def test_get_default_output_language_returns_en():
    assert get_default_output_language() == 'en'


def test_get_language_instruction_defaults_to_english_when_no_language_given():
    assert get_language_instruction() == LANGUAGE_CONFIG['en']['instruction']
    assert get_language_instruction(None) == LANGUAGE_CONFIG['en']['instruction']


def test_get_ppt_language_instruction_defaults_to_english_when_no_language_given():
    assert get_ppt_language_instruction() == LANGUAGE_CONFIG['en']['ppt_text']


def test_get_language_instruction_respects_explicit_language():
    """An explicit language argument must never be overridden by the default."""
    assert get_language_instruction('zh') == LANGUAGE_CONFIG['zh']['instruction']
    assert get_language_instruction('ja') == LANGUAGE_CONFIG['ja']['instruction']


def test_settings_explicit_output_language_overrides_en_default(app):
    """A user's saved output_language in the DB must win over the new 'en' default."""
    with app.app_context():
        from models import Settings, db

        settings = Settings.get_settings()
        settings.output_language = 'zh'
        db.session.commit()

        assert settings.to_dict()['output_language'] == 'zh'


def test_settings_null_output_language_falls_back_to_en(app):
    """No explicit choice stored -> falls back to the new 'en' default, not 'zh'."""
    with app.app_context():
        from models import Settings, db

        settings = Settings.get_settings()
        settings.output_language = None
        db.session.commit()

        assert settings.to_dict()['output_language'] == 'en'
