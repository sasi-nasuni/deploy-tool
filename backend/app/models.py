from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RepoName = Literal["nbn-daemon", "unity"]


class AwsCredentials(BaseModel):
    access_key_id: str = Field(default="")
    secret_access_key: str = Field(default="")
    session_token: str = Field(default="")

    def provided(self) -> bool:
        return bool(self.access_key_id.strip() and self.secret_access_key.strip() and self.session_token.strip())


class DeployRequest(BaseModel):
    repo: RepoName
    branch: str
    filer_ip: str
    aws: AwsCredentials


class DeployResponse(BaseModel):
    deployment_id: str
    status: str


class DeploymentStatusResponse(BaseModel):
    deployment_id: str
    repo: RepoName
    branch: str
    filer_ip: str
    status: Literal["queued", "running", "success", "failed"]
    current_phase: str | None = None
    progress_percent: int = 0
    eta_seconds: int | None = None
    eta_confidence: Literal["low", "medium", "high"] = "low"
    exit_code: int | None = None
    started_at: datetime
    completed_at: datetime | None = None


class CredentialStatusResponse(BaseModel):
    token_valid: bool
    token_expires_at: datetime | None = None
    credentials_required: bool
