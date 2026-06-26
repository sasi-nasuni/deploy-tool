from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/api", tags=["websocket"])


@router.websocket("/ws/logs/{deployment_id}")
async def logs_websocket(websocket: WebSocket, deployment_id: str, request: Request) -> None:
    streamer = request.app.state.log_streamer
    await streamer.connect(deployment_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await streamer.disconnect(deployment_id, websocket)
