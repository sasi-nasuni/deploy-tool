import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models import DeploymentState
from app.routers.branches import router as branches_router
from app.routers.credentials import router as credentials_router
from app.routers.deploy import router as deploy_router
from app.routers.status import router as status_router
from app.routers.websocket import router as websocket_router
from app.services.credential_manager import CredentialManager
from app.services.deployer import Deployer
from app.services.log_streamer import LogStreamer
from app.services.repo_manager import RepoManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.repos_base_path = str(Path(settings.repos_base_path).expanduser())

    app.state.settings = settings
    app.state.deployments: dict[str, DeploymentState] = {}
    app.state.repo_locks = {
        "nbn-daemon": asyncio.Lock(),
        "unity": asyncio.Lock(),
    }
    app.state.log_streamer = LogStreamer()
    app.state.repo_manager = RepoManager(settings)
    app.state.credential_manager = CredentialManager(settings)
    app.state.deployer = Deployer(
        settings,
        app.state.log_streamer,
        app.state.credential_manager,
    )
    credential_refresh_task: asyncio.Task[None] | None = None

    for repo_name in ("nbn-daemon", "unity"):
        await app.state.repo_manager.ensure_cloned(repo_name)

    if settings.developer_machine_mac:
        credential_refresh_task = asyncio.create_task(
            app.state.credential_manager.background_refresh_loop()
        )

    try:
        yield
    finally:
        if credential_refresh_task is not None:
            credential_refresh_task.cancel()
            with suppress(asyncio.CancelledError):
                await credential_refresh_task


app = FastAPI(title="Deploy Tool Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(status_router)
app.include_router(branches_router)
app.include_router(credentials_router)
app.include_router(deploy_router)
app.include_router(websocket_router)
