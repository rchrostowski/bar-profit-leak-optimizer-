import streamlit as st
from src.utils import get_settings
from src.db import init_db
from src.auth import signup, login

settings = get_settings()
init_db(settings["DB_PATH"])

st.title("⚙️ Account")

tab1, tab2 = st.tabs(["Sign in", "Sign up"])

with tab1:
    st.subheader("Sign in")
    email = st.text_input("Email", key="login_email")
    pw = st.text_input("Password", type="password", key="login_pw")
    if st.button("Sign in", use_container_width=True):
        err = login(settings["DB_PATH"], email, pw)
        if err:
            st.error(err)
        else:
            st.success("Signed in!")
            st.rerun()

with tab2:
    st.subheader("Sign up")
    email2 = st.text_input("Email", key="signup_email")
    pw2 = st.text_input("Password (min 8 chars)", type="password", key="signup_pw")
    pw3 = st.text_input("Confirm password", type="password", key="signup_pw2")
    if st.button("Create account", use_container_width=True):
        if pw2 != pw3:
            st.error("Passwords do not match.")
        else:
            err = signup(settings["DB_PATH"], email2, pw2)
            if err:
                st.error(err)
            else:
                st.success("Account created. Please sign in.")

