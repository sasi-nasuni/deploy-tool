import asyncio
import json
import subprocess
from datetime import datetime, timedelta, timezone
from ipaddress import IPv4Interface, IPv4Network
from pathlib import Path

from app.config import Settings


class CredentialManager:
    TOKEN_FILE = Path("~/.deploy_tool/aws_token.json").expanduser()
    TOKEN_TTL = timedelta(hours=12)

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._token_data: dict[str, str] | None = None
        self._load_cached_token()

    def _codeartifact_url(self, raw_token: str) -> str:
        return (
            f"https://aws:{raw_token}@"
            f"{self._settings.aws_codeartifact_domain}-{self._settings.aws_codeartifact_owner}"
            f".d.codeartifact.us-east-1.amazonaws.com/pypi/"
            f"{self._settings.aws_codeartifact_repo}/simple/"
        )

    def _load_cached_token(self) -> None:
        if not self.TOKEN_FILE.exists():
            return

        try:
            self._token_data = json.loads(self.TOKEN_FILE.read_text())
        except (OSError, json.JSONDecodeError):
            self.invalidate_token()

    def get_valid_token(self) -> str | None:
        if not self._token_data:
            return None

        try:
            expires_at = datetime.fromisoformat(self._token_data["expires_at"])
            token_url = self._token_data["uv_extra_index_url"]
        except (KeyError, ValueError):
            self.invalidate_token()
            return None

        if datetime.now(timezone.utc) < expires_at:
            return token_url
        return None

    def store_token(self, raw_token: str, source: str = "user") -> dict[str, str]:
        now = datetime.now(timezone.utc)
        self._token_data = {
            "token": raw_token,
            "uv_extra_index_url": self._codeartifact_url(raw_token),
            "expires_at": (now + self.TOKEN_TTL).isoformat(),
            "fetched_from": source,
            "fetched_at": now.isoformat(),
        }
        self.TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.TOKEN_FILE.write_text(json.dumps(self._token_data, indent=2))
        return dict(self._token_data)

    def invalidate_token(self) -> None:
        self._token_data = None
        if self.TOKEN_FILE.exists():
            self.TOKEN_FILE.unlink()

    async def validate_token(self, url: str) -> bool:
        try:
            process = await asyncio.create_subprocess_exec(
                "curl",
                "-s",
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
                url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            return False

        stdout, _ = await process.communicate()
        return stdout.decode().strip() == "200"

    def _read_command_output(self, command: list[str]) -> str:
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
        except OSError:
            return ""
        return result.stdout

    def _ip_from_arp(self, mac: str) -> str | None:
        output = self._read_command_output(["arp", "-a"])
        for line in output.splitlines():
            if mac not in line.lower():
                continue
            parts = line.split("(")
            if len(parts) > 1:
                return parts[1].split(")")[0].strip()
        return None

    def _candidate_subnets(self) -> list[str]:
        output = self._read_command_output(["ip", "-o", "-4", "addr", "show"])
        subnets: list[str] = []
        seen: set[str] = set()

        for line in output.splitlines():
            parts = line.split()
            if "inet" not in parts:
                continue
            cidr = parts[parts.index("inet") + 1]
            network = str(IPv4Network(f"{IPv4Interface(cidr).ip}/24", strict=False))
            if network not in seen:
                seen.add(network)
                subnets.append(network)

        return subnets

    def _prime_arp_cache(self) -> None:
        for subnet in self._candidate_subnets():
            try:
                subprocess.run(["nmap", "-sn", subnet], capture_output=True, text=True, check=False)
            except OSError:
                return

    def resolve_dev_machine_ip(self) -> str | None:
        mac = self._settings.developer_machine_mac.strip().lower()
        if not mac:
            return None

        ip_address = self._ip_from_arp(mac)
        if ip_address:
            return ip_address

        self._prime_arp_cache()
        return self._ip_from_arp(mac)

    async def fetch_token_from_dev_machine(self) -> str | None:
        ip_address = self.resolve_dev_machine_ip()
        if not ip_address:
            return None

        remote_command = (
            "aws codeartifact get-authorization-token "
            f"--domain {self._settings.aws_codeartifact_domain} "
            f"--domain-owner {self._settings.aws_codeartifact_owner} "
            f"--profile {self._settings.aws_profile} "
            "--query authorizationToken --output text"
        )
        command = [
            "ssh",
            "-p",
            str(self._settings.developer_machine_ssh_port),
            "-o",
            "ConnectTimeout=5",
            "-o",
            "StrictHostKeyChecking=no",
            f"{self._settings.developer_machine_user}@{ip_address}",
            remote_command,
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            return None

        stdout, _ = await process.communicate()
        if process.returncode != 0:
            return None

        token = stdout.decode().strip()
        if not token:
            return None

        self.store_token(token, source="dev-machine")
        return token

    async def background_refresh_loop(self) -> None:
        interval_seconds = max(self._settings.credential_refresh_interval_minutes, 1) * 60
        while True:
            try:
                await self.fetch_token_from_dev_machine()
            except asyncio.CancelledError:
                raise
            except Exception:
                pass
            await asyncio.sleep(interval_seconds)
