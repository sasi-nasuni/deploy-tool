from fastapi import APIRouter, HTTPException, Request

from app.models import BranchListResponse, RepoName
from app.services.repo_manager import RepoManagerError

router = APIRouter(prefix="/api", tags=["branches"])


@router.get("/branches/{repo}", response_model=BranchListResponse)
async def list_branches(repo: RepoName, request: Request) -> BranchListResponse:
    repo_manager = request.app.state.repo_manager
    try:
        branches = await repo_manager.list_branches(repo)
    except RepoManagerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return BranchListResponse(branches=branches)
