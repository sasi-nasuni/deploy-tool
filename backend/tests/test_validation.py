import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.services.repo_manager import RepoManager
from app.utils.validation import validate_branch_name, validate_ipv4_address


class ValidationTests(unittest.TestCase):
    def test_validate_ipv4_accepts_valid_address(self) -> None:
        validate_ipv4_address("10.0.0.42")

    def test_validate_ipv4_rejects_invalid_address(self) -> None:
        with self.assertRaises(ValueError):
            validate_ipv4_address("999.10.10.10")

    def test_parse_remote_branches(self) -> None:
        output = "  origin/HEAD -> origin/main\n  origin/main\n  origin/feature/x\n"
        self.assertEqual(RepoManager._parse_remote_branches(output), ["main", "feature/x"])

    def test_parse_remote_branches_deduplicates_entries(self) -> None:
        output = "  origin/main\n  origin/main\n  origin/feature/x\n  origin/feature/x\n"
        self.assertEqual(RepoManager._parse_remote_branches(output), ["main", "feature/x"])

    def test_validate_branch_name_rejects_invalid_ref(self) -> None:
        process = AsyncMock()
        process.communicate = AsyncMock(return_value=(b"", b"invalid"))
        process.returncode = 1

        async def run() -> None:
            with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=process)):
                with self.assertRaises(ValueError):
                    await validate_branch_name("bad branch")

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
