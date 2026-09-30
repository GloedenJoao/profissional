from app.config import Settings


def test_settings_do_not_require_anthropic_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    settings = Settings(_env_file=None)

    assert settings.anthropic_api_key is None
    assert settings.database_url.startswith("sqlite")


def test_settings_accept_optional_anthropic_api_key():
    settings = Settings(anthropic_api_key="dummy-key", _env_file=None)

    assert settings.anthropic_api_key == "dummy-key"
