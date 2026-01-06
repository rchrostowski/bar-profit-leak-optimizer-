from __future__ import annotations
import pandas as pd
from typing import Dict, Tuple, Optional

SALES_REQUIRED = ["date", "drink_name", "quantity_sold", "revenue"]
PURCHASES_REQUIRED = ["date", "item_name", "units_purchased", "unit_cost"]
RECIPES_REQUIRED = ["drink_name", "item_name", "ml_per_drink"]

def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df

def validate_sales(df: pd.DataFrame) -> Tuple[Optional[pd.DataFrame], str]:
    df = _normalize_cols(df)
    missing = [c for c in SALES_REQUIRED if c not in df.columns]
    if missing:
        return None, f"Sales file missing columns: {missing}"
    # clean
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "drink_name"])
    df["drink_name"] = df["drink_name"].astype(str).str.strip()
    df["quantity_sold"] = pd.to_numeric(df["quantity_sold"], errors="coerce").fillna(0.0)
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce").fillna(0.0)
    df = df[df["quantity_sold"] >= 0]
    df = df[df["revenue"] >= 0]
    return df, ""

def validate_purchases(df: pd.DataFrame) -> Tuple[Optional[pd.DataFrame], str]:
    df = _normalize_cols(df)
    missing = [c for c in PURCHASES_REQUIRED if c not in df.columns]
    if missing:
        return None, f"Purchases file missing columns: {missing}"
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "item_name"])
    df["item_name"] = df["item_name"].astype(str).str.strip()
    df["units_purchased"] = pd.to_numeric(df["units_purchased"], errors="coerce").fillna(0.0)
    df["unit_cost"] = pd.to_numeric(df["unit_cost"], errors="coerce").fillna(0.0)
    df = df[(df["units_purchased"] >= 0) & (df["unit_cost"] >= 0)]
    return df, ""

def validate_recipes(df: pd.DataFrame) -> Tuple[Optional[pd.DataFrame], str]:
    df = _normalize_cols(df)
    missing = [c for c in RECIPES_REQUIRED if c not in df.columns]
    if missing:
        return None, f"Recipes file missing columns: {missing}"
    df["drink_name"] = df["drink_name"].astype(str).str.strip()
    df["item_name"] = df["item_name"].astype(str).str.strip()
    df["ml_per_drink"] = pd.to_numeric(df["ml_per_drink"], errors="coerce").fillna(0.0)
    df = df[df["ml_per_drink"] > 0]
    return df, ""

