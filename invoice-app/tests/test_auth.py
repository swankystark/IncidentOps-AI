"""Unit tests for the auth module.

Covers user lookup, credential validation, session creation,
and token validation. Bug #2 is demonstrated via a failing test
that triggers the null profile AttributeError.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# User service tests
# ---------------------------------------------------------------------------

def test_get_user_exists():
    from auth.user_service import get_user
    user = get_user("user-001")
    assert user is not None
    assert user["email"] == "alice@invoiceapp.io"


def test_get_user_not_found():
    from auth.user_service import get_user
    assert get_user("user-999") is None


def test_lookup_user_by_email_found():
    from auth.user_service import lookup_user_by_email
    user = lookup_user_by_email("bob@invoiceapp.io")
    assert user["user_id"] == "user-002"


def test_lookup_user_by_email_case_insensitive():
    from auth.user_service import lookup_user_by_email
    user = lookup_user_by_email("ALICE@INVOICEAPP.IO")
    assert user is not None


def test_lookup_user_by_email_not_found():
    from auth.user_service import lookup_user_by_email
    assert lookup_user_by_email("ghost@nowhere.com") is None


def test_validate_credentials_valid():
    from auth.user_service import validate_credentials
    user = validate_credentials("alice@invoiceapp.io", "anypassword")
    assert user is not None
    assert user["role"] == "admin"


def test_validate_credentials_inactive_user():
    """Inactive users should be rejected even with valid credentials."""
    from auth.user_service import validate_credentials
    user = validate_credentials("carol@invoiceapp.io", "anypassword")
    assert user is None


def test_validate_credentials_empty_password():
    from auth.user_service import validate_credentials
    assert validate_credentials("alice@invoiceapp.io", "") is None


# ---------------------------------------------------------------------------
# Session service tests
# ---------------------------------------------------------------------------

def test_create_session_returns_token():
    from auth.session_service import create_session
    token = create_session("user-001")
    assert isinstance(token, str)
    assert "." in token


def test_validate_token_valid():
    from auth.session_service import create_session, validate_token
    token = create_session("user-001")
    profile = validate_token(token)
    assert profile["user_id"] == "user-001"
    assert profile["role"] == "admin"


def test_validate_token_invalid():
    from auth.session_service import validate_token
    with pytest.raises(ValueError, match="Invalid or unknown token"):
        validate_token("not-a-real-token")


# ---------------------------------------------------------------------------
# BUG #2 -- Failing test demonstrating null profile AttributeError
#
# If a session exists for a user_id that has since been removed from the
# user store (e.g. account deletion, store inconsistency), validate_token()
# calls get_user() which returns None, then immediately accesses
# user_profile["email"] -- raising AttributeError.
#
# Observed in production on 2023-12-04. Causes cascading 500s in all
# services that depend on the auth middleware.
#
# Fix: add `if user_profile is None: raise ValueError(...)` after get_user().
# ---------------------------------------------------------------------------

def test_validate_token_deleted_user_raises_attribute_error():
    """FAILING TEST (Bug #2): Token for a deleted user causes AttributeError.

    Expected behaviour: raises ValueError with a clear message.
    Actual behaviour:   raises AttributeError (NoneType not subscriptable).
    """
    from auth.session_service import create_session, validate_token, _SESSION_STORE

    # Create a valid session for a ghost user (not in user store)
    token = create_session("user-ghost-deleted")

    # validate_token should raise ValueError, but instead raises AttributeError
    with pytest.raises(ValueError, match="User .* not found"):
        validate_token(token)  # AttributeError: 'NoneType' object is not subscriptable
