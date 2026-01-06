import json
import streamlit as st
import pandas as pd
from src.utils import get_settings
from src.auth import require_login
from src.db import q_all, q_one, require_user

settings = get_settings()
require_login()
user = require_user()

st.title("📄 Reports")

bar_id = st.session_state.get("active_bar_id")
bar_name = st.session_state.get("active_bar_name")

if not bar_id:
    st.warning("Go to Dashboard and select/create a bar first.")
    st.stop()

st.caption(f"Active bar: **{bar_name}**")

rows = q_all(settings["DB_PATH"], "SELECT * FROM reports WHERE bar_id = ? ORDER BY created_at DESC", (bar_id,))
if not rows:
    st.info("No reports yet. Go to Upload & Analyze.")
    st.stop()

labels = [f"{r['label']} — {r['created_at']}" for r in rows]
idx = st.selectbox("Select a report", range(len(rows)), format_func=lambda i: labels[i])
r = rows[idx]
rep = json.loads(r["report_json"])

k = rep.get("kpis", {})
c1, c2, c3, c4 = st.columns(4)
c1.metric("Revenue", f"${k.get('total_revenue', 0):,.0f}")
c2.metric("Units sold", f"{k.get('total_units', 0):,.0f}")
c3.metric("Unique drinks", f"{k.get('unique_drinks', 0)}")
c4.metric("Purchases spend", f"${k.get('total_purchases_spend', 0):,.0f}" if "total_purchases_spend" in k else "—")

st.markdown("## Owner Summary")
for a in rep.get("actions", {}).get("top_3", []):
    st.info(f"**{a['title']}**\n\n- Why: {a['why']}\n- Do this: {a['do_this']}")

st.markdown("## Data Views")

menu = pd.DataFrame(rep.get("menu_summary", []))
if len(menu) > 0:
    st.subheader("Menu summary")
    st.dataframe(menu, use_container_width=True)

approx = pd.DataFrame(rep.get("menu_profit_approx", []))
if len(approx) > 0:
    st.subheader("Approx profit leak ranking (worst first)")
    st.dataframe(approx, use_container_width=True)
else:
    st.caption("No purchases uploaded for this run, so profit approximation is not available.")

shrink = pd.DataFrame(rep.get("shrinkage", []))
if len(shrink) > 0:
    st.subheader("Shrinkage signals")
    st.dataframe(shrink, use_container_width=True)
else:
    st.caption("No recipes+purchases for this run, so shrinkage signals are not available.")

