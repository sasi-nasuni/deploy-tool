import asyncio

from fastapi import APIRouter, Request

from app.models import StatusResponse

router = APIRouter(prefix="/api", tags=["status"])


async def _docker_running() -> bool:
    try:
        process = await asyncio.create_subprocess_exec(
            "docker",
            "info",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        return False

    await process.communicate()
    return process.returncode == 0


@router.get("/status", response_model=StatusResponse)
async def get_status(request: Request) -> StatusResponse:
    repo_manager = request.app.state.repo_manager
    repos = {
        "nbn-daemon": (repo_manager.repo_path("nbn-daemon") / ".git").exists(),
        "unity": (repo_manager.repo_path("unity") / ".git").exists(),
    }
    docker = await _docker_running()
    status = "ok" if docker and all(repos.values()) else "degraded"
    return StatusResponse(status=status, repos=repos, docker=docker)
