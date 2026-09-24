"""Settings must refuse to start in production with default secrets (PRD §8.3)."""

import pytest

from app.config.settings import Settings


def test_production_rejects_default_secrets():
    with pytest.raises(ValueError):
        Settings(env="production", jwt_secret="", csrf_secret="")


def test_production_accepts_real_secrets():
    settings = Settings(env="production", jwt_secret="a-real-secret", csrf_secret="another-real-secret")
    assert settings.is_production is True


def test_development_allows_default_secrets():
    settings = Settings(env="development", jwt_secret="", csrf_secret="")
    assert settings.is_production is False
