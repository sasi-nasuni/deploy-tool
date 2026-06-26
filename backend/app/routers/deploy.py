import asyncio
import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

from app.models import DeployRequest, DeployResponse, DeploymentResponse, DeploymentState
from app.services.repo_manager import RepoManagerError
from app.utils.validation import validate_branch_name, validate_ipv4_address

router = APIRouter(prefix="/api", tags=["deploy"])
logger = logging.getLogger(__name__)


def _deployments(request: Request) -> dict[str, DeploymentState]:
    return request.app.state.deployments


@router.post("/deploy", response_model=DeployResponse)
async def create_deployment(payload: DeployRequest, request: Request) -> DeployResponse:
    try:
        validate_ipv4_address(payload.filer_ip)
        await validate_branch_name(payload.branch)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    deployment_id = str(uuid4())
    deployment = DeploymentState(
        id=deployment_id,
        repo=payload.repo,
        branch=payload.branch,
        filer_ip=payload.filer_ip,
        status="queued",
        exit_code=None,
        started_at=datetime.now(timezone.utc),
    )
    _deployments(request)[deployment_id] = deployment

    async def run_deployment() -> None:
        locks: dict[str, asyncio.Lock] = request.app.state.repo_locks
        repo_manager = request.app.state.repo_manager
        deployer = request.app.state.deployer
        streamer = request.app.state.log_streamer

        lock = locks[payload.repo]
        async with lock:
            deployment.status = "running"
            try:
                await streamer.broadcast(deployment_id, "system", "Starting git fetch/reset/checkout/rebase")
                await repo_manager.prepare_branch(payload.repo, payload.branch)
                repo_path = repo_manager.repo_path(payload.repo)
                if payload.repo == "nbn-daemon":
                    exit_code = await deployer.deploy_nbn_daemon(payload.filer_ip, deployment_id, repo_path)
                else:
                    exit_code = await deployer.deploy_unity(payload.filer_ip, deployment_id, repo_path)

                deployment.exit_code = exit_code
                deployment.status = "success" if exit_code == 0 else "failed"
                await streamer.broadcast(
                    deployment_id,
                    "system",
                    f"Deployment finished with exit code {exit_code}",
                    done=True,
                )
            except RepoManagerError as exc:
                deployment.status = "failed"
                deployment.exit_code = 1
                await streamer.broadcast(deployment_id, "system", str(exc), done=True)
            except Exception as exc:  # noqa: BLE001
                deployment.status = "failed"
                deployment.exit_code = 1
                logger.exception("Unexpected deployment error for %s", deployment_id)
                await streamer.broadcast(
                    deployment_id,
                    "system",
                    "Deployment failed due to an internal server error.",
                    done=True,
                )
            finally:
                deployment.completed_at = datetime.now(timezone.utc)

    asyncio.create_task(run_deployment())
    return DeployResponse(deploymentId=deployment_id, status="started")


@router.get("/deployments/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(deployment_id: str, request: Request) -> DeploymentResponse:
    deployment = _deployments(request).get(deployment_id)
    if deployment is None:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment.to_response()
