import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import httpx
from config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
)

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_URL  = "https://www.googleapis.com/oauth2/v2/userinfo"

def get_google_auth_url(state: str = "") -> str:
    params = {
        "client_id"    : GOOGLE_CLIENT_ID,
        "redirect_uri" : GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope"        : "openid email profile",
        "access_type"  : "offline",
        "state"        : state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query}"


async def exchange_code_for_token(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code"         : code,
                "client_id"    : GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri" : GOOGLE_REDIRECT_URI,
                "grant_type"   : "authorization_code",
            }
        )
        response.raise_for_status()
        return response.json()

async def get_google_user(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GOOGLE_USER_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        return response.json()

