import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import repo_path
from app.routers.branches import router as branches_router
from app.routers.credentials import router as credentials_router
from app.routers.deploy import router as deploy_router
from app.routers.websocket import router as websocket_router
from app.services.deployer import Deployer
from app.services.eta_manager import EtaManager
from app.services.log_streamer import LogStreamer
from app.services.token_manager import TokenManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.deployments = {}
    app.state.repo_locks = {
        "nbn-daemon": asyncio.Lock(),
        "unity": asyncio.Lock(),
    }
    app.state.log_streamer = LogStreamer()
    app.state.eta_manager = EtaManager()
    app.state.token_manager = TokenManager()
    app.state.deployer = Deployer(app.state.log_streamer, app.state.token_manager)
    app.state.repo_path = repo_path
    yield


app = FastAPI(title="Deploy Tool API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(branches_router)
app.include_router(credentials_router)
app.include_router(deploy_router)
app.include_router(websocket_router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
