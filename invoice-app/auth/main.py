"""FastAPI entrypoint for the auth service."""

from fastapi import FastAPI, HTTPException, Header
from typing import Optional
from .user_service import validate_credentials
from .session_service import create_session, validate_token

app = FastAPI(title="Auth Service", version="2.0.1")


@app.post("/auth/login")
def login(email: str, password: str):
    """Validate credentials and issue a session token."""
    user = validate_credentials(email, password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_session(user["user_id"])
    return {"token": token, "user_id": user["user_id"], "role": user["role"]}


@app.get("/auth/me")
def get_current_user(authorization: Optional[str] = Header(default=None)):
    """Return the current user profile for a valid session token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed token")
    token = authorization.removeprefix("Bearer ")
    try:
        profile = validate_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except AttributeError:
        # Surface Bug #2 as a 500 -- matches production behaviour
        raise HTTPException(status_code=500, detail="Internal auth error: user profile unavailable")
    return profile
