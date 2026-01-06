import os
import streamlit as st

def get_settings() -> dict:
    # Safe defaults
    secret = st.secrets.get("APP_SECRET", "dev-secret-change-me")
    db_path = st.secrets.get("DB_PATH", "app.db")
    data_dir = st.secrets.get("DATA_DIR", "data")

    os.makedirs(data_dir, exist_ok=True)
    return {"APP_SECRET": secret, "DB_PATH": db_path, "DATA_DIR": data_dir}

