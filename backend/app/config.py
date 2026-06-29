from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    repos_base_path: str = "~/.deploy_tool/repos"
    nbn_repo_name: str = "nbn-daemon"
    unity_repo_name: str = "unity"

    aws_region: str = "us-east-1"
    codeartifact_domain: str = "nasuni-portal"
    codeartifact_owner: str = "851725431039"
    codeartifact_repository: str = "nasuni-portal"


settings = Settings()


def repo_path(repo: str) -> Path:
    base = Path(settings.repos_base_path).expanduser()
    name = settings.nbn_repo_name if repo == "nbn-daemon" else settings.unity_repo_name
    return base / name
