import asyncio
import os
from pathlib import Path

from app.config import Settings
from app.services.credential_manager import CredentialManager
from app.services.log_streamer import LogStreamer

TIMEOUT_KILLED_EXIT_CODE = 124


class Deployer:
    def __init__(
        self,
        settings: Settings,
        log_streamer: LogStreamer,
        credential_manager: CredentialManager,
    ) -> None:
        self._settings = settings
        self._log_streamer = log_streamer
        self._credential_manager = credential_manager
        self._pending_tokens: dict[str, asyncio.Future[str]] = {}

    async def _read_stream(
        self,
        deployment_id: str,
        stream: asyncio.StreamReader,
        message_type: str,
        collector: list[str],
    ) -> None:
        while True:
            line = await stream.readline()
            if not line:
                break
            decoded = line.decode(errors="replace").rstrip("\n")
            collector.append(decoded)
            await self._log_streamer.broadcast(
                deployment_id,
                message_type,
                decoded,
            )

    async def _run_process(
        self,
        deployment_id: str,
        cwd: Path,
        command: list[str],
        *,
        env: dict[str, str] | None = None,
    ) -> tuple[int, str, str]:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(cwd),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        assert process.stdout is not None
        assert process.stderr is not None

        stdout_lines: list[str] = []
        stderr_lines: list[str] = []
        stdout_task = asyncio.create_task(
            self._read_stream(deployment_id, process.stdout, "stdout", stdout_lines)
        )
        stderr_task = asyncio.create_task(
            self._read_stream(deployment_id, process.stderr, "stderr", stderr_lines)
        )

        try:
            await asyncio.wait_for(process.wait(), timeout=self._settings.deploy_timeout_seconds)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            await asyncio.gather(stdout_task, stderr_task)
            await self._log_streamer.broadcast(
                deployment_id,
                "system",
                f"Deployment timed out after {self._settings.deploy_timeout_seconds}s.",
            )
            return TIMEOUT_KILLED_EXIT_CODE, "\n".join(stdout_lines), "\n".join(stderr_lines)

        await asyncio.gather(stdout_task, stderr_task)
        return (
            process.returncode if process.returncode is not None else 1,
            "\n".join(stdout_lines),
            "\n".join(stderr_lines),
        )

    async def _wait_for_token(self, deployment_id: str) -> str:
        future = self._pending_tokens.get(deployment_id)
        if future is None or future.done():
            future = asyncio.get_running_loop().create_future()
            self._pending_tokens[deployment_id] = future

        try:
            return await future
        finally:
            if self._pending_tokens.get(deployment_id) is future:
                self._pending_tokens.pop(deployment_id, None)

    async def _request_token(self, deployment_id: str, message: str) -> str:
        await self._log_streamer.broadcast(deployment_id, "credential_required", message)
        return await self._wait_for_token(deployment_id)

    async def _resolve_nbn_daemon_token(self, deployment_id: str) -> str:
        while True:
            token_url = self._credential_manager.get_valid_token()
            if token_url and await self._credential_manager.validate_token(token_url):
                return token_url

            if token_url:
                self._credential_manager.invalidate_token()

            await self._credential_manager.fetch_token_from_dev_machine()
            token_url = self._credential_manager.get_valid_token()
            if token_url and await self._credential_manager.validate_token(token_url):
                return token_url

            self._credential_manager.invalidate_token()
            await self._request_token(
                deployment_id,
                "AWS token required. Paste your CodeArtifact token:",
            )

    def submit_token(self, raw_token: str, deployment_id: str | None = None) -> str:
        token_data = self._credential_manager.store_token(raw_token, source="user")
        target_deployment_id = deployment_id
        if target_deployment_id is None and self._pending_tokens:
            target_deployment_id = next(reversed(self._pending_tokens))

        if target_deployment_id is not None:
            future = self._pending_tokens.get(target_deployment_id)
            if future is not None and not future.done():
                future.set_result(token_data["uv_extra_index_url"])

        return token_data["expires_at"]

    @staticmethod
    def _has_codeartifact_auth_error(*outputs: str) -> bool:
        combined_output = "\n".join(outputs).lower()
        return "codeartifact" in combined_output and ("401" in combined_output or "403" in combined_output)

    async def deploy_nbn_daemon(self, filer_ip: str, deployment_id: str, repo_path: Path) -> int:
        await self._log_streamer.broadcast(deployment_id, "system", "Starting nbn-daemon deployment")
        token_url = await self._resolve_nbn_daemon_token(deployment_id)
        env = os.environ.copy()
        env["UV_EXTRA_INDEX_URL"] = token_url
        exit_code, stdout, stderr = await self._run_process(
            deployment_id,
            repo_path,
            ["make", "deploy-rpm", f"FILER={filer_ip}"],
            env=env,
        )

        if exit_code == 0 or not self._has_codeartifact_auth_error(stdout, stderr):
            return exit_code

        self._credential_manager.invalidate_token()
        await self._request_token(
            deployment_id,
            "Credentials failed. Paste a fresh CodeArtifact token:",
        )
        retry_token_url = await self._resolve_nbn_daemon_token(deployment_id)
        retry_env = os.environ.copy()
        retry_env["UV_EXTRA_INDEX_URL"] = retry_token_url
        retry_exit_code, _, _ = await self._run_process(
            deployment_id,
            repo_path,
            ["make", "deploy-rpm", f"FILER={filer_ip}"],
            env=retry_env,
        )
        return retry_exit_code

    async def deploy_unity(self, filer_ip: str, deployment_id: str, repo_path: Path) -> int:
        await self._log_streamer.broadcast(deployment_id, "system", "Starting unity sync-dev deployment")
        sync_exit, _, _ = await self._run_process(
            deployment_id,
            repo_path,
            ["python", "python/tools/sync-dev.py", "--restart", filer_ip],
        )
        if sync_exit != 0:
            return sync_exit

        await self._log_streamer.broadcast(
            deployment_id,
            "system",
            "Running unity post-sync SSH cleanup and service restarts",
        )
        post_sync_cmd = (
            "find /opt/nasuni/lib/nasuni/ -name '*.pyc' -delete && "
            "find /opt/nasuni/lib/nasuni/ -name '*.pyo' -delete && "
            "systemctl restart filer-route-http qman && "
            "systemctl restart httpd"
        )
        post_sync_exit, _, _ = await self._run_process(
            deployment_id,
            repo_path,
            ["ssh", "-p222", f"root@{filer_ip}", post_sync_cmd],
        )
        return post_sync_exit
