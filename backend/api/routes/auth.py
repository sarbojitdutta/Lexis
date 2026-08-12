import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from auth.oauth import get_google_auth_url, exchange_code_for_token, get_google_user
from auth.jwt   import create_token

router = APIRouter()

FRONTEND_URL = "http://localhost:5173"

@router.get("/auth/google")
def google_login():
    url = get_google_auth_url()
    return RedirectResponse(url)

@router.get("/auth/callback")
async def oogle_callback(code: str, state: str = ""): 
    try:
        token_data = await exchange_code_for_token(code)
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="No access token")
        user = await get_google_user(access_token)

        jwt_token = create_token({
            "sub"    : user["id"],
            "email"  : user["email"],
            "name"   : user.get("name", ""),
            "picture": user.get("picture", ""),
        })

        return RedirectResponse(
            f"{FRONTEND_URL}?token={jwt_token}"
        )
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail      = f"OAuth failed: {str(e)}"
        )

@router.get("/auth/me")
def get_me(user: dict = None):
    from auth.middleware import get_optional_user
    from fastapi import Depends
    if not user:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "email"        : user.get("email"),
        "name"         : user.get("name"),
        "picture"      : user.get("picture"),
    }

@router.post("/auth/logout")
def logout():
    return {"status": "logged out"}

    

