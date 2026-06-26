import asyncio
import ipaddress


def validate_ipv4_address(value: str) -> None:
    try:
        ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError as exc:
        raise ValueError("Invalid IP address format.") from exc


async def validate_branch_name(value: str) -> None:
    process = await asyncio.create_subprocess_exec(
        "git",
        "check-ref-format",
        "--branch",
        value,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, _ = await process.communicate()
    if process.returncode != 0:
        raise ValueError("Invalid branch name.")
