from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.config import repo_path

router = APIRouter(prefix="/api", tags=["branches"])


@router.get("/branches/{repo}")
async def list_branches(repo: str) -> dict[str, list[str]]:
    if repo not in {"nbn-daemon", "unity"}:
        raise HTTPException(status_code=400, detail="Unsupported repo")

    path = repo_path(repo)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Repo not found: {path}")

    git_dir = path / ".git"
    if not git_dir.exists():
        raise HTTPException(status_code=400, detail="Not a git repository")

    import subprocess

    result = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes/origin"],
        cwd=str(path),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail="Unable to read branches")

    cleaned: set[str] = set()
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("origin/"):
            line = line[len("origin/") :]
        cleaned.add(line)

    return {"branches": sorted(cleaned)}
