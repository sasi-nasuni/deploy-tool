import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

from app.models import DeployRequest, DeployResponse, DeploymentStatusResponse
from app.services.token_manager import TokenError

router = APIRouter(prefix="/api", tags=["deploy"])


@router.post("/deploy", response_model=DeployResponse)
async def start_deploy(payload: DeployRequest, request: Request) -> DeployResponse:
    if payload.repo not in {"nbn-daemon", "unity"}:
        raise HTTPException(status_code=400, detail="Unsupported repo")

    deployment_id = str(uuid4())
    request.app.state.deployments[deployment_id] = {
        "deployment_id": deployment_id,
        "repo": payload.repo,
        "branch": payload.branch,
        "filer_ip": payload.filer_ip,
        "status": "queued",
        "current_phase": "queued",
        "progress_percent": 0,
        "eta_seconds": None,
        "eta_confidence": "low",
        "exit_code": None,
        "started_at": datetime.now(timezone.utc),
        "phase_started_at": datetime.now(timezone.utc),
        "phase_durations": {},
        "completed_at": None,
    }

    async def run() -> None:
        lock = request.app.state.repo_locks[payload.repo]
        state = request.app.state.deployments[deployment_id]
        eta_manager = request.app.state.eta_manager

        def set_phase(phase: str, progress: int) -> None:
            now = datetime.now(timezone.utc)
            prev_phase = state.get("current_phase")
            prev_started_at = state.get("phase_started_at")
            if isinstance(prev_phase, str) and isinstance(prev_started_at, datetime):
                elapsed = max(0.0, (now - prev_started_at).total_seconds())
                durations = state.setdefault("phase_durations", {})
                durations[prev_phase] = durations.get(prev_phase, 0.0) + elapsed
            state["current_phase"] = phase
            state["phase_started_at"] = now
            state["progress_percent"] = max(0, min(progress, 100))

        async with lock:
            state["status"] = "running"
            try:
                set_phase("git_prep", 10)
                await request.app.state.log_streamer.broadcast(deployment_id, f"Preparing {payload.repo} deployment")
                import subprocess

                repo_cwd = str(request.app.state.repo_path(payload.repo))
                subprocess.run(["git", "fetch", "--all"], cwd=repo_cwd, check=False)
                subprocess.run(["git", "checkout", payload.branch], cwd=repo_cwd, check=True)
                subprocess.run(["git", "pull", "--rebase", "origin", payload.branch], cwd=repo_cwd, check=False)

                set_phase("deploy_exec", 35)
                code = await request.app.state.deployer.deploy(deployment_id, payload)
                state["exit_code"] = code
                state["status"] = "success" if code == 0 else "failed"
                set_phase("finalize", 95)
            except TokenError as exc:
                state["status"] = "failed"
                state["exit_code"] = 1
                await request.app.state.log_streamer.broadcast(deployment_id, str(exc), done=True)
            except Exception as exc:  # noqa: BLE001
                state["status"] = "failed"
                state["exit_code"] = 1
                await request.app.state.log_streamer.broadcast(deployment_id, f"Deployment failed: {exc}", done=True)
            finally:
                now = datetime.now(timezone.utc)
                current_phase = state.get("current_phase")
                current_started_at = state.get("phase_started_at")
                if isinstance(current_phase, str) and isinstance(current_started_at, datetime):
                    elapsed = max(0.0, (now - current_started_at).total_seconds())
                    durations = state.setdefault("phase_durations", {})
                    durations[current_phase] = durations.get(current_phase, 0.0) + elapsed

                total = max(0.0, (now - state["started_at"]).total_seconds())
                eta_manager.record_run(payload.repo, state.get("phase_durations", {}), total)
                state["progress_percent"] = 100
                state["completed_at"] = datetime.now(timezone.utc)

    asyncio.create_task(run())
    return DeployResponse(deployment_id=deployment_id, status="started")


@router.get("/deployments/{deployment_id}", response_model=DeploymentStatusResponse)
async def deployment_status(deployment_id: str, request: Request) -> DeploymentStatusResponse:
    state = request.app.state.deployments.get(deployment_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Deployment not found")
    eta_seconds, confidence = request.app.state.eta_manager.estimate(state)
    state["eta_seconds"] = eta_seconds
    state["eta_confidence"] = confidence
    return DeploymentStatusResponse(**state)
