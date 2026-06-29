import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings


class TokenError(Exception):
    pass


@dataclass
class TokenRecord:
    token: str
    expires_at: datetime

    @property
    def uv_extra_index_url(self) -> str:
        host = (
            f"{settings.codeartifact_domain}-{settings.codeartifact_owner}.d.codeartifact."
            f"{settings.aws_region}.amazonaws.com"
        )
        return (
            f"https://aws:{self.token}@{host}/pypi/{settings.codeartifact_repository}/simple/"
        )


class TokenManager:
    def __init__(self) -> None:
        self.cache_file = Path("~/.deploy_tool/aws_token.json").expanduser()
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

    def get_cached_token(self) -> TokenRecord | None:
        if not self.cache_file.exists():
            return None
        try:
            data = json.loads(self.cache_file.read_text())
            expires_at = datetime.fromisoformat(data["expires_at"])
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            return TokenRecord(token=data["token"], expires_at=expires_at)
        except Exception:
            return None

    def is_valid(self, record: TokenRecord | None) -> bool:
        if record is None:
            return False
        return record.expires_at > datetime.now(timezone.utc)

    def _store(self, token: str, expires_at: datetime) -> TokenRecord:
        record = TokenRecord(token=token, expires_at=expires_at)
        payload = {
            "token": token,
            "expires_at": expires_at.isoformat(),
            "uv_extra_index_url": record.uv_extra_index_url,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": "aws_credentials",
        }
        self.cache_file.write_text(json.dumps(payload, indent=2))
        return record

    def exchange_credentials(
        self,
        access_key_id: str,
        secret_access_key: str,
        session_token: str,
    ) -> TokenRecord:
        try:
            session = boto3.session.Session(
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                aws_session_token=session_token,
                region_name=settings.aws_region,
            )
            client = session.client("codeartifact", region_name=settings.aws_region)
            response = client.get_authorization_token(
                domain=settings.codeartifact_domain,
                domainOwner=settings.codeartifact_owner,
                durationSeconds=43200,
            )
            token = response["authorizationToken"]
            expires_at = response["expiration"]
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            return self._store(token, expires_at)
        except (ClientError, BotoCoreError, KeyError) as exc:
            raise TokenError("Unable to exchange AWS credentials for CodeArtifact token") from exc
