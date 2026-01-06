from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

def menu_summary(sales: pd.DataFrame) -> pd.DataFrame:
    g = (sales.groupby("drink_name", as_index=False)
         .agg(quantity_sold=("quantity_sold", "sum"),
              revenue=("revenue", "sum"),
              first_date=("date", "min"),
              last_date=("date", "max")))
    g["rev_per_unit"] = np.where(g["quantity_sold"] > 0, g["revenue"] / g["quantity_sold"], 0.0)
    g = g.sort_values("revenue", ascending=False)
    total_rev = float(g["revenue"].sum()) if len(g) else 0.0
    g["revenue_share"] = np.where(total_rev > 0, g["revenue"] / total_rev, 0.0)
    return g

def purchases_summary(purchases: pd.DataFrame) -> pd.DataFrame:
    g = (purchases.groupby("item_name", as_index=False)
         .agg(units_purchased=("units_purchased", "sum"),
              unit_cost=("unit_cost", "mean"),
              total_spend=("unit_cost", "sum")))
    # Note: unit_cost in purchases is assumed to be "cost per unit purchased" row-wise.
    # total_spend should be units_purchased * unit_cost; if user’s export already has total spend,
    # they can map accordingly — but we keep it simple.
    g["total_spend"] = purchases["units_purchased"] * purchases["unit_cost"]
    g = g.groupby("item_name", as_index=False).agg(
        units_purchased=("units_purchased", "sum"),
        avg_unit_cost=("unit_cost", "mean"),
        total_spend=("total_spend", "sum"),
    )
    return g.sort_values("total_spend", ascending=False)

def approximate_cogs_for_menu(sales: pd.DataFrame, purchases: pd.DataFrame) -> pd.DataFrame:
    """
    Defensible approximation:
    - allocate total purchases spend across drinks proportional to revenue share
    - gives a bar owner a "directionally correct" profit leak ranking
    - clearly labeled as 'approximate' in output
    """
    m = menu_summary(sales)
    total_spend = float((purchases["units_purchased"] * purchases["unit_cost"]).sum()) if len(purchases) else 0.0
    m["approx_cogs_allocated"] = m["revenue_share"] * total_spend
    m["approx_gross_profit"] = m["revenue"] - m["approx_cogs_allocated"]
    m["approx_margin"] = np.where(m["revenue"] > 0, m["approx_gross_profit"] / m["revenue"], 0.0)
    return m.sort_values("approx_gross_profit", ascending=True)

def shrinkage_estimate(
    sales: pd.DataFrame,
    purchases: pd.DataFrame,
    recipes: pd.DataFrame,
    ml_per_unit_purchased_default: float = 750.0
) -> Optional[pd.DataFrame]:
    """
    Requires recipes mapping drink -> item_name and ml_per_drink.
    Purchases must include item_name and units_purchased.
    We assume each purchased unit is a bottle (default 750ml) unless user changes.
    """
    if recipes is None or len(recipes) == 0:
        return None
    # normalize names
    sales2 = sales.copy()
    sales2["drink_name"] = sales2["drink_name"].astype(str).str.strip()
    recipes2 = recipes.copy()
    recipes2["drink_name"] = recipes2["drink_name"].astype(str).str.strip()
    recipes2["item_name"] = recipes2["item_name"].astype(str).str.strip()
    purchases2 = purchases.copy()
    purchases2["item_name"] = purchases2["item_name"].astype(str).str.strip()

    # total drinks sold per drink_name
    sold = sales2.groupby("drink_name", as_index=False).agg(qty=("quantity_sold", "sum"))
    # join to recipes to get ml used per item
    use = sold.merge(recipes2, on="drink_name", how="inner")
    use["ml_expected"] = use["qty"] * use["ml_per_drink"]
    use_item = use.groupby("item_name", as_index=False).agg(ml_expected=("ml_expected", "sum"))

    # purchased ml available
    purch = purchases2.groupby("item_name", as_index=False).agg(units_purchased=("units_purchased", "sum"),
                                                                avg_unit_cost=("unit_cost", "mean"))
    purch["ml_purchased"] = purch["units_purchased"] * float(ml_per_unit_purchased_default)

    out = use_item.merge(purch, on="item_name", how="left")
    out["ml_purchased"] = out["ml_purchased"].fillna(0.0)
    out["ml_gap"] = out["ml_purchased"] - out["ml_expected"]
    # if gap is negative, you "should have" needed more than purchased -> indicates recipe mismatch or missing purchases
    # if gap is positive and very large, indicates shrinkage/overpour/waste *or* starting inventory not accounted for.
    out["gap_pct_of_expected"] = np.where(out["ml_expected"] > 0, out["ml_gap"] / out["ml_expected"], 0.0)

    # dollarize rough leakage: if gap is "too negative" ignore; if gap positive, estimate wasted bottles * avg cost
    out["bottles_gap_est"] = out["ml_gap"] / float(ml_per_unit_purchased_default)
    out["est_cost_of_gap"] = np.where(out["bottles_gap_est"] > 0,
                                      out["bottles_gap_est"] * out["avg_unit_cost"].fillna(0.0),
                                      0.0)

    return out.sort_values("est_cost_of_gap", ascending=False)

def build_report(
    sales: pd.DataFrame,
    purchases: Optional[pd.DataFrame] = None,
    recipes: Optional[pd.DataFrame] = None,
    ml_per_unit_purchased_default: float = 750.0
) -> Dict[str, Any]:
    report: Dict[str, Any] = {}
    menu = menu_summary(sales)
    report["menu_summary"] = menu.to_dict(orient="records")

    # core top-line metrics
    report["kpis"] = {
        "total_revenue": float(menu["revenue"].sum()),
        "total_units": float(menu["quantity_sold"].sum()),
        "unique_drinks": int(menu["drink_name"].nunique()),
        "date_min": str(sales["date"].min().date()) if len(sales) else None,
        "date_max": str(sales["date"].max().date()) if len(sales) else None,
    }

    if purchases is not None and len(purchases) > 0:
        total_spend = float((purchases["units_purchased"] * purchases["unit_cost"]).sum())
        report["kpis"]["total_purchases_spend"] = total_spend
        approx = approximate_cogs_for_menu(sales, purchases)
        report["menu_profit_approx"] = approx.to_dict(orient="records")
        report["method_notes"] = {
            "cogs_method": "Approximate allocation of total purchases spend to drinks proportional to revenue share. Directional, not exact."
        }
    else:
        report["method_notes"] = {
            "cogs_method": "Purchases not provided. Profit/leak estimates limited to revenue-side insights until purchases are uploaded."
        }

    if purchases is not None and recipes is not None and len(purchases) > 0 and len(recipes) > 0:
        shrink = shrinkage_estimate(sales, purchases, recipes, ml_per_unit_purchased_default)
        report["shrinkage"] = shrink.to_dict(orient="records") if shrink is not None else []
        report["method_notes"]["shrinkage_method"] = "Expected usage computed from recipes (ml per drink) vs purchased volume (default 750ml/bottle). Starting/ending inventory not included unless you model it separately."
    else:
        report.setdefault("method_notes", {})
        report["method_notes"]["shrinkage_method"] = "Recipes and purchases required for shrinkage estimates."

    # action recommendations (simple, blunt, safe)
    report["actions"] = _suggest_actions(report)
    return report

def _suggest_actions(report: Dict[str, Any]) -> Dict[str, Any]:
    actions = {"top_3": []}

    kpis = report.get("kpis", {})
    total_rev = float(kpis.get("total_revenue", 0.0) or 0.0)

    menu = pd.DataFrame(report.get("menu_summary", []))
    if len(menu) > 0 and total_rev > 0:
        top_share = menu.sort_values("revenue", ascending=False).head(5)
        share = float(top_share["revenue"].sum() / total_rev)
        if share > 0.60:
            actions["top_3"].append({
                "title": "Revenue concentration is high",
                "why": f"Top 5 drinks drive ~{share:.0%} of revenue. A price tweak here moves the needle.",
                "do_this": "Test +$0.50 to +$1 on your top 1–2 sellers (track volume change for 2 weeks)."
            })
        else:
            actions["top_3"].append({
                "title": "Tighten menu focus during peaks",
                "why": "Your revenue is spread across many drinks.",
                "do_this": "During peak hours, feature a smaller set of high-velocity drinks to increase throughput."
            })

    approx = pd.DataFrame(report.get("menu_profit_approx", []))
    if len(approx) > 0:
        worst = approx.sort_values("approx_gross_profit", ascending=True).head(3)
        if len(worst) > 0:
            names = ", ".join(worst["drink_name"].astype(str).tolist()[:2])
            actions["top_3"].append({
                "title": "Bottom performers to investigate",
                "why": f"These drinks look weakest on an approximate profit basis: {names}.",
                "do_this": "Either raise price, simplify recipe, or stop pushing these."
            })
    else:
        actions["top_3"].append({
            "title": "Upload purchases to unlock profit leaks",
            "why": "Without purchases, we can’t estimate costs.",
            "do_this": "Export last 30–90 days of invoice/purchase history and re-run."
        })

    shrink = pd.DataFrame(report.get("shrinkage", []))
    if len(shrink) > 0:
        top = shrink.sort_values("est_cost_of_gap", ascending=False).head(1)
        if len(top) > 0:
            item = str(top.iloc[0]["item_name"])
            cost = float(top.iloc[0]["est_cost_of_gap"])
            actions["top_3"].append({
                "title": "Possible shrinkage hotspot",
                "why": f"{item} shows the largest expected-vs-purchased gap (est. cost impact ~${cost:,.0f}).",
                "do_this": "Reconfirm pour spec + training; spot-check counts weekly for 2 weeks."
            })
    else:
        actions["top_3"].append({
            "title": "Optional: enable shrinkage detection",
            "why": "Shrinkage estimates require a simple recipes mapping.",
            "do_this": "Create a recipe CSV (drink → spirit + ml per drink) for your top 20 cocktails."
        })

    actions["top_3"] = actions["top_3"][:3]
    return actions

