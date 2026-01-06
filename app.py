# app.py
import streamlit as st

from src.db import init_db
from src.auth import logout_button
from src.utils import get_settings

# ----------------------------
# Page config
# ----------------------------
st.set_page_config(
    page_title="Bar Profit Leak Optimizer",
    page_icon="🍺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------
# Init settings + DB
# ----------------------------
settings = get_settings()
init_db(settings["DB_PATH"])

# ----------------------------
# Ensure session defaults
# ----------------------------
if "user" not in st.session_state:
    st.session_state["user"] = None
if "active_bar_id" not in st.session_state:
    st.session_state["active_bar_id"] = None
if "active_bar_name" not in st.session_state:
    st.session_state["active_bar_name"] = None

# ----------------------------
# Sidebar
# ----------------------------
with st.sidebar:
    st.markdown("## 🍺 Profit Leak Optimizer")

    if st.session_state.get("user"):
        st.caption(f"Signed in as **{st.session_state['user']['email']}**")
        if st.session_state.get("active_bar_name"):
            st.caption(f"Active bar: **{st.session_state['active_bar_name']}**")
        logout_button()
        st.divider()
        st.markdown(
            """
**Navigation**
- Use the left sidebar page list (Streamlit pages)
- Recommended flow:
  1) **Account** (sign in)
  2) **Dashboard** (create/select bar)
  3) **Upload & Analyze**
  4) **Reports**
"""
        )
    else:
        st.caption("Not signed in")
        st.divider()
        st.markdown(
            """
**Start here**
1) Open **Account** page
2) Create an account
3) Sign in
"""
        )

# ----------------------------
# Main
# ----------------------------
st.title("🍺 Bar Profit Leak Optimizer")

if not st.session_state.get("user"):
    st.info("You’re not signed in yet. Open **Account** from the left sidebar to sign up / sign in.")
    st.stop()

# Signed-in landing experience
st.success("Signed in ✅")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("### 1) Create or select a bar")
    st.markdown("Go to **Dashboard** → create a bar profile (name/city/state) and set it active.")
with c2:
    st.markdown("### 2) Upload POS exports")
    st.markdown("Go to **Upload & Analyze** → upload Sales (required) and Purchases/Recipes (optional).")
with c3:
    st.markdown("### 3) View saved reports")
    st.markdown("Go to **Reports** → browse every historical report for the active bar.")

st.divider()

st.markdown("## What you’ll get from the analysis")
st.markdown(
    """
- **Menu Revenue & Mix**: top drinks, revenue share, price-per-unit, concentration risk  
- **Approx Profit Leak Ranking** *(if purchases uploaded)*: directional “worst performers” list  
- **Shrinkage Signals** *(if purchases + recipes uploaded)*: expected usage vs purchased volume with estimated cost impact  
- **Owner Summary**: 3 blunt actions to take this week
"""
)

st.divider()

st.markdown("## Data you need (CSV)")
st.markdown(
    """
### Sales by Drink *(required)*
Columns:
- `date`
- `drink_name`
- `quantity_sold`
- `revenue`

### Purchases *(optional, unlocks profit estimates)*
Columns:
- `date`
- `item_name`
- `units_purchased`
- `unit_cost`

### Recipes *(optional, unlocks shrinkage estimates)*
Columns:
- `drink_name`
- `item_name`
- `ml_per_drink`
"""
)

st.caption("Tip: If a bar only gives you Sales, you can still deliver value (menu mix + pricing opportunities). Purchases + Recipes makes it killer.")

