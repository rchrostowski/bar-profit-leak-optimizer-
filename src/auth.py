import bcrypt
import streamlit as st
from typing import Optional, Dict
from src.db import q_one, exec_one
from src.utils import get_settings

def _hash_pw(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))

def _check_pw(password: str, pw_hash: bytes) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), pw_hash)
    except Exception:
        return False

def signup(db_path: str, email: str, password: str) -> Optional[str]:
    email = email.strip().lower()
    if not email or "@" not in email:
        return "Please enter a valid email."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    existing = q_one(db_path, "SELECT id FROM users WHERE email = ?", (email,))
    if existing:
        return "An account with that email already exists."

    pw_hash = _hash_pw(password)
    exec_one(db_path, "INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, pw_hash))
    return None

def login(db_path: str, email: str, password: str) -> Optional[str]:
    email = email.strip().lower()
    row = q_one(db_path, "SELECT id, email, password_hash FROM users WHERE email = ?", (email,))
    if not row:
        return "Invalid email or password."
    # sqlite returns memoryview for BLOB sometimes
    pw_hash = row["password_hash"]
    if isinstance(pw_hash, memoryview):
        pw_hash = pw_hash.tobytes()
    if not _check_pw(password, pw_hash):
        return "Invalid email or password."

    st.session_state["user"] = {"id": row["id"], "email": row["email"]}
    return None

def require_login():
    if not st.session_state.get("user"):
        st.warning("You must be signed in to use this page.")
        st.stop()

def logout_button():
    if st.button("Log out", use_container_width=True):
        st.session_state.pop("user", None)
        st.rerun()

