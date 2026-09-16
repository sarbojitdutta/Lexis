import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from auth.jwt import verify_token

security = HTTPBearer(auto_error=False)

def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security)
)-> dict:
    
    if not credentials:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Not authenticated",
            headers     = {"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Invalid or expired token",
            headers     = {"WWW-Authenticate": "Bearer"},
        )

    return payload

def get_optional_user(
        credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    if not credentials:
        return None
    return verify_token(credentials.credentials)