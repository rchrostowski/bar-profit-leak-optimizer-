import os
import json
import streamlit as st
import pandas as pd
from src.utils import get_settings
from src.auth import require_login
from src.db import exec_one, q_one, require_user
from src.io_validate import validate_sales, validate_purchases, validate_recipes
from src.analytics import build_report

settings = get_settings()
require_login()
user = require_user()

st.title("📤 Upload & Analyze")

bar_id = st.session_state.get("active_bar_id")
bar_name = st.session_state.get("active_bar_name")

if not bar_id:
    st.warning("Go to Dashboard and select/create a bar first.")
    st.stop()

st.caption(f"Active bar: **{bar_name}**")

st.markdown("### Upload files (CSV)")
sales_file = st.file_uploader("Sales by Drink (required)", type=["csv"], key="sales_csv")
purchases_file = st.file_uploader("Purchases (optional)", type=["csv"], key="purchases_csv")
recipes_file = st.file_uploader("Recipes (optional, enables shrinkage)", type=["csv"], key="recipes_csv")

ml_default = st.number_input("Assumed ml per purchased unit (default bottle size)", min_value=100, max_value=5000, value=750, step=50)

label = st.text_input("Label for this run (e.g., 'Dec 2025 POS Export')", value="New analysis")

def _save_upload_file(file, out_path: str):
    with open(out_path, "wb") as f:
        f.write(file.getbuffer())

if st.button("Run analysis", type="primary", use_container_width=True, disabled=(sales_file is None)):
    # Read CSVs
    try:
        sales_df_raw = pd.read_csv(sales_file)
    except Exception as e:
        st.error(f"Could not read sales CSV: {e}")
        st.stop()

    sales_df, err = validate_sales(sales_df_raw)
    if err:
        st.error(err)
        st.stop()

    purchases_df = None
    recipes_df = None

    if purchases_file is not None:
        try:
            purchases_raw = pd.read_csv(purchases_file)
            purchases_df, err2 = validate_purchases(purchases_raw)
            if err2:
                st.error(err2)
                st.stop()
        except Exception as e:
            st.error(f"Could not read purchases CSV: {e}")
            st.stop()

    if recipes_file is not None:
        try:
            recipes_raw = pd.read_csv(recipes_file)
            recipes_df, err3 = validate_recipes(recipes_raw)
            if err3:
                st.error(err3)
                st.stop()
        except Exception as e:
            st.error(f"Could not read recipes CSV: {e}")
            st.stop()

    # Store files to disk per bar
    bar_dir = os.path.join(settings["DATA_DIR"], f"bar_{bar_id}")
    os.makedirs(bar_dir, exist_ok=True)

    upload_label = label.strip() or "New analysis"
    sales_path = os.path.join(bar_dir, f"sales_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv")
    _save_upload_file(sales_file, sales_path)

    purchases_path = None
    recipes_path = None
    if purchases_file is not None:
        purchases_path = os.path.join(bar_dir, f"purchases_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv")
        _save_upload_file(purchases_file, purchases_path)

    if recipes_file is not None:
        recipes_path = os.path.join(bar_dir, f"recipes_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv")
        _save_upload_file(recipes_file, recipes_path)

    upload_id = exec_one(
        settings["DB_PATH"],
        "INSERT INTO uploads (bar_id, label, sales_path, purchases_path, recipes_path) VALUES (?, ?, ?, ?, ?)",
        (bar_id, upload_label, sales_path, purchases_path, recipes_path),
    )

    # Build report
    report = build_report(sales_df, purchases_df, recipes_df, ml_per_unit_purchased_default=float(ml_default))
    report_json = json.dumps(report)

    report_id = exec_one(
        settings["DB_PATH"],
        "INSERT INTO reports (bar_id, upload_id, label, report_json) VALUES (?, ?, ?, ?)",
        (bar_id, upload_id, upload_label, report_json),
    )

    st.success("Report generated and saved.")
    st.session_state["last_report_id"] = report_id
    st.rerun()

# If a report was just created, show a preview
last_id = st.session_state.get("last_report_id")
if last_id:
    import json
    from src.db import q_one

    row = q_one(settings["DB_PATH"], "SELECT * FROM reports WHERE id = ? AND bar_id = ?", (last_id, bar_id))
    if row:
        rep = json.loads(row["report_json"])
        st.markdown("## Preview")
        k = rep.get("kpis", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Revenue", f"${k.get('total_revenue', 0):,.0f}")
        c2.metric("Units sold", f"{k.get('total_units', 0):,.0f}")
        c3.metric("Unique drinks", f"{k.get('unique_drinks', 0)}")
        c4.metric("Purchases spend", f"${k.get('total_purchases_spend', 0):,.0f}" if "total_purchases_spend" in k else "—")

        st.markdown("### Top actions")
        for a in rep.get("actions", {}).get("top_3", []):
            st.info(f"**{a['title']}**\n\n- Why: {a['why']}\n- Do this: {a['do_this']}")

        menu = pd.DataFrame(rep.get("menu_summary", []))
        if len(menu) > 0:
            st.markdown("### Top drinks by revenue")
            st.dataframe(menu.sort_values("revenue", ascending=False).head(15), use_container_width=True)

        approx = pd.DataFrame(rep.get("menu_profit_approx", []))
        if len(approx) > 0:
            st.markdown("### Approx profit leak ranking (worst first)")
            st.dataframe(approx[["drink_name", "revenue", "approx_cogs_allocated", "approx_gross_profit", "approx_margin"]].head(20), use_container_width=True)

        shrink = pd.DataFrame(rep.get("shrinkage", []))
        if len(shrink) > 0:
            st.markdown("### Shrinkage signals (requires recipes)")
            st.dataframe(shrink[["item_name", "ml_expected", "ml_purchased", "ml_gap", "est_cost_of_gap"]].head(25), use_container_width=True)

