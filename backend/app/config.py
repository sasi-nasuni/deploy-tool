import os
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    github_pat: str
    repos_base_path: str = "~/.deploy_tool/repos"
    nbn_daemon_repo_url: str = "https://github.com/nasuni/nbn-daemon.git"
    unity_repo_url: str = "https://github.com/nasuni/unity.git"
    deploy_timeout_seconds: int = 1800
    server_port: int = 8000
    developer_machine_mac: str = ""
    developer_machine_user: str = ""
    developer_machine_ssh_port: int = 22
    credential_refresh_interval_minutes: int = 30
    aws_codeartifact_domain: str = "nasuni-portal"
    aws_codeartifact_owner: str = "851725431039"
    aws_codeartifact_repo: str = "nasuni-portal"
    aws_profile: str = "portal-dev"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("developer_machine_user", mode="before")
    @classmethod
    def default_developer_machine_user(cls, value: str | None) -> str:
        if value is None or not str(value).strip():
            return os.environ.get("USER", "root")
        return str(value)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
