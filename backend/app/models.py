from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RepoName = Literal["nbn-daemon", "unity"]
DeploymentStatus = Literal["queued", "running", "success", "failed"]


class DeployRequest(BaseModel):
    repo: RepoName
    branch: str
    filer_ip: str = Field(alias="filerIP")

    model_config = ConfigDict(populate_by_name=True)


class DeployResponse(BaseModel):
    deployment_id: str = Field(alias="deploymentId")
    status: Literal["started"]

    model_config = ConfigDict(populate_by_name=True)


class DeploymentResponse(BaseModel):
    id: str
    repo: RepoName
    branch: str
    filer_ip: str = Field(alias="filerIP")
    status: DeploymentStatus
    exit_code: int | None = Field(alias="exitCode")
    started_at: datetime = Field(alias="startedAt")
    completed_at: datetime | None = Field(alias="completedAt")

    model_config = ConfigDict(populate_by_name=True)


class BranchListResponse(BaseModel):
    branches: list[str]


class StatusResponse(BaseModel):
    status: Literal["ok", "degraded"]
    repos: dict[str, bool]
    docker: bool


@dataclass
class DeploymentState:
    id: str
    repo: RepoName
    branch: str
    filer_ip: str
    status: DeploymentStatus
    exit_code: int | None
    started_at: datetime
    completed_at: datetime | None = None

    def to_response(self) -> DeploymentResponse:
        return DeploymentResponse(
            id=self.id,
            repo=self.repo,
            branch=self.branch,
            filerIP=self.filer_ip,
            status=self.status,
            exitCode=self.exit_code,
            startedAt=self.started_at,
            completedAt=self.completed_at,
        )
