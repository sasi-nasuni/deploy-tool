import asyncio
from pathlib import Path
from urllib.parse import quote

from app.config import Settings


class RepoManagerError(RuntimeError):
    """Raised when repository operations fail."""


class RepoManager:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._repo_urls = {
            "nbn-daemon": settings.nbn_daemon_repo_url,
            "unity": settings.unity_repo_url,
        }

    def repo_path(self, repo_name: str) -> Path:
        return Path(self._settings.repos_base_path).expanduser() / repo_name

    async def _run_git(self, repo_path: Path, *args: str) -> str:
        process = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=str(repo_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RepoManagerError(
                f"Git command failed: {stderr.decode().strip() or stdout.decode().strip()}"
            )
        return stdout.decode().strip()

    def _authed_url(self, repo_name: str) -> str:
        base_url = self._repo_urls[repo_name]
        token = quote(self._settings.github_pat, safe="")
        return base_url.replace("https://", f"https://{token}@", 1)

    async def ensure_cloned(self, repo_name: str) -> None:
        repo_path = self.repo_path(repo_name)
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        if not (repo_path / ".git").exists():
            process = await asyncio.create_subprocess_exec(
                "git",
                "clone",
                self._authed_url(repo_name),
                str(repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                raise RepoManagerError(f"Failed to clone {repo_name}.")

        await self._run_git(repo_path, "remote", "set-url", "origin", self._authed_url(repo_name))

    async def prepare_branch(self, repo_name: str, branch: str) -> None:
        repo_path = self.repo_path(repo_name)
        await self._run_git(repo_path, "fetch", "origin")

        branch_ref = f"refs/remotes/origin/{branch}"
        try:
            await self._run_git(repo_path, "show-ref", "--verify", branch_ref)
        except RepoManagerError as exc:
            raise RepoManagerError(f"Branch '{branch}' not found on remote.") from exc

        await self._run_git(repo_path, "reset", "--hard", "HEAD")
        await self._run_git(repo_path, "clean", "-fd")

        checkout = await asyncio.create_subprocess_exec(
            "git",
            "checkout",
            branch,
            cwd=str(repo_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, _ = await checkout.communicate()
        if checkout.returncode != 0:
            await self._run_git(repo_path, "checkout", "-B", branch, f"origin/{branch}")

        await self._run_git(repo_path, "rebase", f"origin/{branch}")

    async def list_branches(self, repo_name: str) -> list[str]:
        repo_path = self.repo_path(repo_name)
        await self._run_git(repo_path, "fetch", "origin")
        output = await self._run_git(repo_path, "branch", "-r")
        return self._parse_remote_branches(output)

    @staticmethod
    def _parse_remote_branches(output: str) -> list[str]:
        branches: list[str] = []
        for raw_line in output.splitlines():
            line = raw_line.strip()
            if not line or "->" in line:
                continue
            if line.startswith("origin/"):
                line = line.removeprefix("origin/")
            if line and line not in branches:
                branches.append(line)
        return branches
