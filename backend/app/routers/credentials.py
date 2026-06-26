from datetime import datetime

from fastapi import APIRouter, Request

from app.models import CredentialTokenRequest, CredentialTokenResponse

router = APIRouter(prefix="/api", tags=["credentials"])


@router.post("/credentials/token", response_model=CredentialTokenResponse)
async def store_credential_token(
    payload: CredentialTokenRequest,
    request: Request,
) -> CredentialTokenResponse:
    expires_at = request.app.state.deployer.submit_token(payload.token.strip())
    return CredentialTokenResponse(
        status="stored",
        expires_at=datetime.fromisoformat(expires_at),
    )
