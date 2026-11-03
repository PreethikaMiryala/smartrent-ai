"""
SmartRent AI - Authentication & Session Management
"""
import hashlib
import secrets
import streamlit as st
from typing import Optional, Tuple


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """
    Hash a password securely using PBKDF2 HMAC SHA-256.
    Returns (hex_hash, hex_salt).
    """
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=password.encode("utf-8"),
        salt=salt.encode("utf-8"),
        iterations=100000
    )
    return key.hex(), salt


def verify_password(plain_password: str, stored_hash: str, salt: str) -> bool:
    """
    Verify a plaintext password against a stored hash and salt.
    """
    computed_hash, _ = hash_password(plain_password, salt=salt)
    return secrets.compare_digest(computed_hash, stored_hash)


def init_session_state():
    """
    Initialize required authentication and navigation keys in session state.
    """
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "groq_api_key" not in st.session_state:
        st.session_state.groq_api_key = ""
    if "messages" not in st.session_state:
        st.session_state.messages = []


def login_user(user: dict):
    """
    Log in a user into session state.
    """
    st.session_state.authenticated = True
    st.session_state.user = user
    st.session_state.messages = []  # reset chat history for the user session


def logout_user():
    """
    Log out the current user and reset session keys.
    """
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.messages = []
    st.rerun()


def get_current_user() -> Optional[dict]:
    """
    Returns the currently logged-in user dictionary or None.
    """
    if st.session_state.get("authenticated") and st.session_state.get("user"):
        return st.session_state.user
    return None


def is_authenticated() -> bool:
    """
    Check if a user is currently logged in.
    """
    return bool(st.session_state.get("authenticated", False))


def is_owner() -> bool:
    """
    Check if currently logged-in user is an owner/administrator.
    """
    user = get_current_user()
    return bool(user and user.get("role") == "owner")


def is_tenant() -> bool:
    """
    Check if currently logged-in user is a tenant.
    """
    user = get_current_user()
    return bool(user and user.get("role") == "tenant")
