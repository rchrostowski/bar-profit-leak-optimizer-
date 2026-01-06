import streamlit as st
from src.utils import get_settings
from src.auth import require_login
from src.db import q_all, q_one, exec_one, require_user

settings = get_settings()
require_login()
user = require_user()

st.title("🏠 Dashboard")

# Create bar
with st.expander("➕ Create a new bar", expanded=True):
    c1, c2, c3 = st.columns(3)
    name = c1.text_input("Bar name")
    city = c2.text_input("City (optional)")
    state = c3.text_input("State (optional)")
    if st.button("Create bar", use_container_width=True):
        if not name.strip():
            st.error("Bar name is required.")
        else:
            exec_one(
                settings["DB_PATH"],
                "INSERT INTO bars (user_id, name, city, state) VALUES (?, ?, ?, ?)",
                (user["id"], name.strip(), city.strip() or None, state.strip() or None),
            )
            st.success("Bar created.")
            st.rerun()

bars = q_all(settings["DB_PATH"], "SELECT * FROM bars WHERE user_id = ? ORDER BY created_at DESC", (user["id"],))

if not bars:
    st.warning("No bars yet. Create one above.")
    st.stop()

st.subheader("Your bars")
bar_labels = [f"{b['name']} ({b.get('city') or '—'}, {b.get('state') or '—'})" for b in bars]
bar_idx = st.selectbox("Select a bar", range(len(bars)), format_func=lambda i: bar_labels[i])
selected = bars[bar_idx]

st.session_state["active_bar_id"] = selected["id"]
st.session_state["active_bar_name"] = selected["name"]

st.success(f"Active bar set to: **{selected['name']}**")

# Quick stats
uploads = q_all(settings["DB_PATH"], "SELECT * FROM uploads WHERE bar_id = ? ORDER BY created_at DESC LIMIT 5", (selected["id"],))
reports = q_all(settings["DB_PATH"], "SELECT * FROM reports WHERE bar_id = ? ORDER BY created_at DESC LIMIT 5", (selected["id"],))

c1, c2 = st.columns(2)
with c1:
    st.metric("Recent uploads", len(uploads))
    if uploads:
        for u in uploads[:5]:
            st.caption(f"• {u['label']} — {u['created_at']}")
with c2:
    st.metric("Recent reports", len(reports))
    if reports:
        for r in reports[:5]:
            st.caption(f"• {r['label']} — {r['created_at']}")

