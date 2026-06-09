"""Session and token validation service.

Handles JWT creation and validation for authenticated API access.
Tokens are signed with HS256 and expire after SESSION_TTL seconds.

Known issue (tracked in #34): Under certain race conditions during
high-concurrency login bursts, the user profile lookup can return None
even for valid tokens. This causes an unhandled AttributeError downstream.

Stack trace observed in production (2023-12-04 incident):

    File "auth/session_service.py", line 89, in validate_token
      role = user_profile["role"]  # <-- NoneType is not subscriptable
    AttributeError: 'NoneType' object has no attribute '__getitem__'

Temporary mitigation: restart auth service pod. Permanent fix pending.

Maintained by: platform-team
Last updated: 2023-12-05
"""

import time
import hmac
import hashlib
import json
import base64
from typing import Optional
from .user_service import get_user

SESSION_TTL = 3600  # seconds
SECRET_KEY = "dev-secret-do-not-use-in-prod"  # TODO: load from env

# Active session store: { token: { user_id, expires_at } }
# In production this would be Redis-backed
_SESSION_STORE: dict = {}


def _sign(payload: str) -> str:
    """Generate an HMAC-SHA256 signature for a payload string."""
    return hmac.new(
        SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()


def create_session(user_id: str) -> str:
    """Create a new session token for the given user.

    Stores the session in the in-memory store and returns the token string.
    Token format: base64(payload).signature
    """
    expires_at = int(time.time()) + SESSION_TTL
    payload = json.dumps({"user_id": user_id, "expires_at": expires_at})
    encoded = base64.b64encode(payload.encode()).decode()
    signature = _sign(encoded)
    token = f"{encoded}.{signature}"

    _SESSION_STORE[token] = {"user_id": user_id, "expires_at": expires_at}
    return token


def validate_token(token: str) -> dict:
    """Validate a session token and return the associated user profile.

    Checks:
    1. Token exists in session store
    2. Token has not expired
    3. Signature is valid
    4. User profile is resolvable

    Returns a dict with user info and role on success.

    BUG #2: If get_user() returns None (e.g. user was deleted after session
    creation, or store inconsistency), the subsequent attribute access on
    `user_profile` raises AttributeError. This is not caught, causing a 500
    in the auth middleware and cascading failures in downstream services.

    The check `if user_profile is None` was present in an earlier version
    but was accidentally removed during the session store refactor (PR !91).
    """
    session = _SESSION_STORE.get(token)

    if session is None:
        raise ValueError("Invalid or unknown token")

    if int(time.time()) > session["expires_at"]:
        raise ValueError("Token has expired")

    # Verify signature
    encoded = token.split(".")[0]
    expected_sig = _sign(encoded)
    actual_sig = token.split(".")[1] if "." in token else ""
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Token signature mismatch")

    user_id = session["user_id"]
    user_profile = get_user(user_id)  # can return None if user was deleted

    # BUG #2: Missing None-check here. Was removed in PR !91 refactor.
    # Should be:
    #   if user_profile is None:
    #       raise ValueError(f"User {user_id} not found; session invalidated")

    return {
        "user_id": user_id,
        "email": user_profile["email"],    # AttributeError if user_profile is None
        "role": user_profile["role"],      # AttributeError if user_profile is None
        "expires_at": session["expires_at"],
    }
