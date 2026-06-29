import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

from app.config import repo_path
from app.models import DeployRequest
from app.services.log_streamer import LogStreamer
from app.services.token_manager import TokenError, TokenManager


class Deployer:
    def __init__(self, log_streamer: LogStreamer, token_manager: TokenManager) -> None:
        self.log_streamer = log_streamer
        self.token_manager = token_manager

    async def deploy(self, deployment_id: str, payload: DeployRequest) -> int:
        cwd = repo_path(payload.repo)
        if not cwd.exists():
            raise RuntimeError(f"Repository not found at {cwd}")

        env = os.environ.copy()
        if payload.repo == "nbn-daemon":
            token_record = self._resolve_token(payload)
            env["UV_EXTRA_INDEX_URL"] = token_record.uv_extra_index_url
            self._update_env_local(cwd, token_record.uv_extra_index_url)
            command = ["make", "deploy-rpm", f"FILER={payload.filer_ip}"]
            post_sync_command: list[str] | None = None
        else:
            if payload.aws.provided():
                # Optional refresh path for users who provide credentials even when not required.
                self.token_manager.exchange_credentials(
                    payload.aws.access_key_id.strip(),
                    payload.aws.secret_access_key.strip(),
                    payload.aws.session_token.strip(),
                )
            command = ["python", "python/tools/sync-dev.py", "--restart", payload.filer_ip]
            post_sync_command = [
                "ssh",
                "-p",
                "222",
                f"root@{payload.filer_ip}",
                "find /opt/nasuni/lib/nasuni/ -name '*.pyc' -delete && "
                "find /opt/nasuni/lib/nasuni/ -name '*.pyo' -delete && "
                "systemctl restart filer-route-http qman && "
                "systemctl restart httpd",
            ]

        await self.log_streamer.broadcast(deployment_id, f"Running: {' '.join(command)}")

        proc = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(cwd),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        assert proc.stdout is not None
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            await self.log_streamer.broadcast(deployment_id, line.decode(errors="replace").rstrip())

        return_code = await proc.wait()

        if return_code == 0 and post_sync_command is not None:
            await self.log_streamer.broadcast(deployment_id, f"Running: {' '.join(post_sync_command)}")
            post_sync_proc = await asyncio.create_subprocess_exec(
                *post_sync_command,
                cwd=str(cwd),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            assert post_sync_proc.stdout is not None
            while True:
                line = await post_sync_proc.stdout.readline()
                if not line:
                    break
                await self.log_streamer.broadcast(deployment_id, line.decode(errors="replace").rstrip())

            post_sync_exit_code = await post_sync_proc.wait()
            if post_sync_exit_code != 0:
                return_code = post_sync_exit_code

        await self.log_streamer.broadcast(
            deployment_id,
            f"Deployment finished with exit code {return_code} at {datetime.now(timezone.utc).isoformat()}",
            done=True,
        )
        return return_code

    def _resolve_token(self, payload: DeployRequest):
        cached = self.token_manager.get_cached_token()
        cached_valid = self.token_manager.is_valid(cached)

        if payload.aws.provided():
            return self.token_manager.exchange_credentials(
                payload.aws.access_key_id.strip(),
                payload.aws.secret_access_key.strip(),
                payload.aws.session_token.strip(),
            )

        if cached_valid:
            return cached

        raise TokenError("AWS credentials are required because cached token is expired or missing")

    def _update_env_local(self, repo_root: Path, token_url: str) -> None:
        root = repo_root.resolve()
        env_file = (root / ".env.local").resolve()
        if env_file.parent != root:
            raise RuntimeError("Refusing to write token outside repository root")
        line = f'UV_EXTRA_INDEX_URL="{token_url}"'

        if not env_file.exists():
            env_file.write_text(f"{line}\n")
            return

        original = env_file.read_text()
        lines = original.splitlines()
        updated = False
        new_lines: list[str] = []

        for item in lines:
            if item.strip().startswith("UV_EXTRA_INDEX_URL="):
                new_lines.append(line)
                updated = True
            else:
                new_lines.append(item)

        if not updated:
            if new_lines and new_lines[-1].strip() != "":
                new_lines.append("")
            new_lines.append(line)

        env_file.write_text("\n".join(new_lines) + "\n")
