from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    github_pat: str
    repos_base_path: str = "~/.deploy_tool/repos"
    nbn_daemon_repo_url: str = "https://github.com/nasuni/nbn-daemon.git"
    unity_repo_url: str = "https://github.com/nasuni/unity.git"
    deploy_timeout_seconds: int = 1800
    server_port: int = 8000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
