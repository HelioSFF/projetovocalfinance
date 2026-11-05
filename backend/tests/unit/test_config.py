from app.core.config import Settings


def test_dev_tools_enabled_only_for_development():
    assert Settings(app_env="development").dev_tools_enabled() is True
    assert Settings(app_env="Development ").dev_tools_enabled() is True
    for value in ["production", "", "dev", "test", "PROD", "develop"]:
        assert Settings(app_env=value).dev_tools_enabled() is False
