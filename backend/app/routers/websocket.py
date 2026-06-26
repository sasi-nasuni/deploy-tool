import json

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/api", tags=["websocket"])


@router.websocket("/ws/logs/{deployment_id}")
async def logs_websocket(websocket: WebSocket, deployment_id: str, request: Request) -> None:
    streamer = request.app.state.log_streamer
    deployer = request.app.state.deployer
    await streamer.connect(deployment_id, websocket)
    try:
        while True:
            message = await websocket.receive_text()
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                continue

            if payload.get("type") == "credential_response":
                token = str(payload.get("token", "")).strip()
                if token:
                    deployer.submit_token(token, deployment_id)
    except WebSocketDisconnect:
        pass
    finally:
        await streamer.disconnect(deployment_id, websocket)
