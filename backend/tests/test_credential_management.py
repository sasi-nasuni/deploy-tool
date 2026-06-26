import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.config import Settings
from app.services.credential_manager import CredentialManager
from app.services.deployer import Deployer


class _RecordingLogStreamer:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str, str, bool]] = []

    async def broadcast(
        self,
        deployment_id: str,
        message_type: str,
        line: str,
        *,
        done: bool = False,
    ) -> None:
        self.messages.append((deployment_id, message_type, line, done))


class TestCredentialManager(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(github_pat="token", developer_machine_mac="aa:bb:cc:dd:ee:ff")

    def test_store_get_and_invalidate_token(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            token_file = Path(temp_dir) / "aws_token.json"
            with patch.object(CredentialManager, "TOKEN_FILE", token_file):
                manager = CredentialManager(self.settings)
                stored = manager.store_token("abc123", source="user")

                self.assertEqual(manager.get_valid_token(), stored["uv_extra_index_url"])
                self.assertTrue(token_file.exists())
                self.assertEqual(stored["fetched_from"], "user")

                manager.invalidate_token()

                self.assertIsNone(manager.get_valid_token())
                self.assertFalse(token_file.exists())

    def test_resolve_dev_machine_ip_uses_arp_output(self) -> None:
        with patch.object(
            CredentialManager,
            "_read_command_output",
            return_value="? (192.168.1.25) at aa:bb:cc:dd:ee:ff on en0\n",
        ):
            manager = CredentialManager(self.settings)
            self.assertEqual(manager.resolve_dev_machine_ip(), "192.168.1.25")


class TestDeployerCredentialFlow(unittest.IsolatedAsyncioTestCase):
    async def test_nbn_daemon_retries_after_codeartifact_auth_failure(self) -> None:
        settings = Settings(github_pat="token")
        log_streamer = _RecordingLogStreamer()

        with tempfile.TemporaryDirectory() as temp_dir:
            token_file = Path(temp_dir) / "aws_token.json"
            with patch.object(CredentialManager, "TOKEN_FILE", token_file):
                credential_manager = CredentialManager(settings)
                credential_manager.fetch_token_from_dev_machine = AsyncMock(return_value=None)
                credential_manager.validate_token = AsyncMock(return_value=True)

                deployer = Deployer(settings, log_streamer, credential_manager)
                deployer._run_process = AsyncMock(
                    side_effect=[
                        (1, "", "HTTP 403 from CodeArtifact"),
                        (0, "ok", ""),
                    ]
                )

                deployment_id = "deployment-1"
                deploy_task = asyncio.create_task(
                    deployer.deploy_nbn_daemon("10.0.0.42", deployment_id, Path("/tmp"))
                )

                await asyncio.sleep(0)
                deployer.submit_token("first-token", deployment_id)
                await asyncio.sleep(0)
                deployer.submit_token("second-token", deployment_id)

                exit_code = await deploy_task

                self.assertEqual(exit_code, 0)
                self.assertEqual(deployer._run_process.await_count, 2)
                self.assertIsNotNone(credential_manager.get_valid_token())
                self.assertEqual(credential_manager._token_data["token"], "second-token")
                self.assertEqual(
                    credential_manager.get_valid_token(),
                    credential_manager._token_data["uv_extra_index_url"],
                )
                self.assertEqual(
                    [message_type for _, message_type, _, _ in log_streamer.messages].count("credential_required"),
                    2,
                )


if __name__ == "__main__":
    unittest.main()
