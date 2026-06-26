import asyncio
from pathlib import Path

from app.config import Settings
from app.services.log_streamer import LogStreamer


class Deployer:
    def __init__(self, settings: Settings, log_streamer: LogStreamer) -> None:
        self._settings = settings
        self._log_streamer = log_streamer

    async def _read_stream(
        self,
        deployment_id: str,
        stream: asyncio.StreamReader,
        message_type: str,
    ) -> None:
        while True:
            line = await stream.readline()
            if not line:
                break
            await self._log_streamer.broadcast(
                deployment_id,
                message_type,
                line.decode(errors="replace").rstrip("\n"),
            )

    async def _run_process(self, deployment_id: str, cwd: Path, command: list[str]) -> int:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        assert process.stdout is not None
        assert process.stderr is not None

        stdout_task = asyncio.create_task(self._read_stream(deployment_id, process.stdout, "stdout"))
        stderr_task = asyncio.create_task(self._read_stream(deployment_id, process.stderr, "stderr"))

        try:
            await asyncio.wait_for(process.wait(), timeout=self._settings.deploy_timeout_seconds)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            await self._log_streamer.broadcast(
                deployment_id,
                "system",
                f"Deployment timed out after {self._settings.deploy_timeout_seconds}s.",
            )

        await asyncio.gather(stdout_task, stderr_task)
        return process.returncode

    async def deploy_nbn_daemon(self, filer_ip: str, deployment_id: str, repo_path: Path) -> int:
        await self._log_streamer.broadcast(deployment_id, "system", "Starting nbn-daemon deployment")
        return await self._run_process(
            deployment_id,
            repo_path,
            ["make", "deploy-rpm", f"FILER={filer_ip}"],
        )

    async def deploy_unity(self, filer_ip: str, deployment_id: str, repo_path: Path) -> int:
        await self._log_streamer.broadcast(deployment_id, "system", "Starting unity sync-dev deployment")
        sync_exit = await self._run_process(
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
        return await self._run_process(
            deployment_id,
            repo_path,
            ["ssh", "-p222", f"root@{filer_ip}", post_sync_cmd],
        )
