import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from jose import JWTError, jwt
from config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET

def create_token(data : dict) -> str:
    payload = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload.update({"exp": expire})
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token : str) -> dict:
    return jwt.decode(token , JWT_SECRET, algorithms=JWT_ALGORITHM)

def verify_token(token : str) -> dict | None:
    try:
        return decode_token(token)
    except JWTError:
        return None