"""User lookup and profile service.

Provides user resolution by ID and email. In production this would
query the users DB. For now, uses an in-memory fixture store.

Maintained by: platform-team
Last updated: 2023-10-18
"""

from typing import Optional

# In-memory user store -- replace with DB in Q2
# Note: passwords are bcrypt hashed in production; plaintext here for demo only
_USER_STORE = {
    "user-001": {
        "user_id": "user-001",
        "email": "alice@invoiceapp.io",
        "name": "Alice Nguyen",
        "role": "admin",
        "active": True,
    },
    "user-002": {
        "user_id": "user-002",
        "email": "bob@invoiceapp.io",
        "name": "Bob Patel",
        "role": "billing",
        "active": True,
    },
    "user-003": {
        "user_id": "user-003",
        "email": "carol@invoiceapp.io",
        "name": "Carol Smith",
        "role": "viewer",
        "active": False,  # deactivated account
    },
}


def get_user(user_id: str) -> Optional[dict]:
    """Fetch a user profile by user ID.

    Returns None if the user does not exist.
    """
    return _USER_STORE.get(user_id)


def lookup_user_by_email(email: str) -> Optional[dict]:
    """Fetch a user profile by email address.

    Linear scan over the store -- acceptable at current user volume.
    Will need indexing once user count exceeds ~10k.

    Returns None if no matching user is found.
    """
    for user in _USER_STORE.values():
        if user["email"].lower() == email.lower():
            return user
    return None


def validate_credentials(email: str, password: str) -> Optional[dict]:
    """Validate login credentials and return the user profile on success.

    In production, compares bcrypt hash. Here we accept any non-empty password
    for active users (demo mode).

    Returns None if credentials are invalid or user is inactive.
    """
    user = lookup_user_by_email(email)
    if user is None:
        return None
    if not user.get("active", False):
        return None
    # Demo: accept any non-empty password for active users
    if not password:
        return None
    return user
