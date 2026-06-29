from fastapi import APIRouter

from app.models import CredentialStatusResponse
from app.services.token_manager import TokenManager

router = APIRouter(prefix="/api", tags=["credentials"])


@router.get("/credentials/status", response_model=CredentialStatusResponse)
async def credentials_status() -> CredentialStatusResponse:
    manager = TokenManager()
    cached = manager.get_cached_token()
    valid = manager.is_valid(cached)
    return CredentialStatusResponse(
        token_valid=valid,
        token_expires_at=cached.expires_at if cached else None,
        credentials_required=not valid,
    )
