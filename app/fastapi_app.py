# ================================================================
#   NeuralRetail – FastAPI Scoring API
#   Amdox Technologies | AMX-DS-2026-04 | April 2026
#   Prepared by: Ayush Tiwari | Data Science & Analytics
#
#   HOW TO RUN (in a terminal):
#   uvicorn fastapi_app:app --reload --port 8000
#
#   Interactive API docs auto-open at:
#   http://localhost:8000/docs
# ================================================================
import os
from datetime import datetime
from pathlib import Path

from xgboost import data

BASE_DIR = Path(__file__).resolve().parent.parent

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
import pandas as pd
import numpy as np
import os
from datetime import datetime

# ── App Setup ────────────────────────────────────────────────
app = FastAPI(
    title       = "NeuralRetail API",
    description = "AI-Powered Sales Intelligence — Amdox Technologies",
    version     = "1.0.0",
    contact     = {"name": "Ayush Tiwari"},
)
@app.get("/")
def home():
    return {
        "project": "NeuralRetail AI Sales Intelligence",
        "status": "running",
        "docs": "/docs"
    }
# ── Load All Data at Startup (once, into RAM) ─────────────────
# This means every request reads from memory, not disk
# Result: <5ms response time vs ~500ms if we read Excel per request
def load_data():
    data = {}

    files = {
        "rfm": BASE_DIR / "data" / "rfm_segments_churn.xlsx",
        "inventory": BASE_DIR / "data" / "inventory_eoq.xlsx",
        "forecast": BASE_DIR / "data" / "demand_forecast.xlsx",
        "sales": BASE_DIR / "data" / "online_retail_CLEANED.xlsx",
    }

    for key, filename in files.items():
        if filename.exists():
            data[key] = pd.read_excel(filename)
            print(f"Loaded {filename}")
        else:
            print(f"WARNING: {filename} not found")

    return data

DATA = load_data()


# ════════════════════════════════════════════════════════════
#   PYDANTIC SCHEMAS
#   Define the shape of every request and response.
#   FastAPI uses these to auto-validate all input/output.
# ════════════════════════════════════════════════════════════

class ChurnRequest(BaseModel):
    customer_id: str = Field(..., example="12345")

class ChurnResponse(BaseModel):
    customer_id   : str
    churn_proba   : float
    churn_risk    : str
    segment       : Optional[str]
    recency_days  : Optional[int]
    frequency     : Optional[int]
    monetary      : Optional[float]
    recommendation: str

class DemandRequest(BaseModel):
    stock_code : str = Field(..., example="85123A")
    days_ahead : int = Field(30, ge=1, le=90)

class DemandResponse(BaseModel):
    stock_code    : str
    forecast_days : int
    predictions   : List[dict]
    avg_daily_qty : Optional[float]
    message       : str

class SegmentRequest(BaseModel):
    customer_id: str = Field(..., example="12345")

class SegmentResponse(BaseModel):
    customer_id   : str
    segment       : str
    kmeans_cluster: Optional[int]
    rfm_score     : Optional[float]
    is_vip        : Optional[bool]
    clv_estimate  : Optional[float]
    churn_risk    : Optional[str]

class ReorderRequest(BaseModel):
    stock_code: str = Field(..., example="85123A")

class ReorderResponse(BaseModel):
    stock_code    : str
    eoq           : float
    safety_stock  : float
    reorder_point : float
    avg_daily_qty : float
    abc_class     : Optional[str]
    xyz_class     : Optional[str]
    abc_xyz       : Optional[str]
    is_dead_stock : bool
    stockout_risk : Optional[str]
    recommendation: str


# ════════════════════════════════════════════════════════════
#   HELPER FUNCTIONS
#   Convert numeric scores into plain-language actions.
#   These are what make the API useful for CRM teams.
# ════════════════════════════════════════════════════════════

def get_churn_recommendation(risk: str, segment: str = "") -> str:
    recs = {
        "High"  : "Immediate action: Send win-back offer with 20% discount. Flag for CRM.",
        "Medium": "Proactive outreach: Send loyalty reward email. Suggest related products.",
        "Low"   : "Customer is healthy. Continue engagement via newsletter.",
    }
    return recs.get(str(risk), "Monitor customer activity.")

def get_reorder_recommendation(row: pd.Series) -> str:
    if row.get("IsDeadStock", 0) == 1:
        return "Dead stock: Consider markdown or liquidation. Do not reorder."
    risk = str(row.get("StockoutRisk", ""))
    eoq  = int(row.get("EOQ", 0))
    rop  = int(row.get("ReorderPoint", 0))
    if   risk == "High"  : return f"URGENT: Reorder {eoq} units now. Below safety stock."
    elif risk == "Medium" : return f"Reorder soon: EOQ = {eoq} units. Monitor weekly."
    else                  : return f"Stock healthy. Next reorder at {rop} units remaining."
    
# ════════════════════════════════════════════════════════════
#   ENDPOINT 1 – Health Check
#   GET /health
#   Always the first endpoint to build. Lets you verify
#   the server is running and data loaded correctly.
# ════════════════════════════════════════════════════════════

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status"   : "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "data_loaded": {
            "rfm_customers" : len(DATA["rfm"]),
            "inventory_skus": len(DATA["inventory"]),
            "forecast_rows" : len(DATA["forecast"]),
            "sales_rows"    : len(DATA["sales"]),
        }
    }


# ════════════════════════════════════════════════════════════
#   ENDPOINT 2 – Summary KPIs
#   GET /summary
#   Returns headline numbers across all models in one call.
#   Used for the executive dashboard smoke test.
# ════════════════════════════════════════════════════════════

@app.get("/summary", tags=["System"])
def get_summary():
    rfm = DATA["rfm"]
    inv = DATA["inventory"]
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "customers": {
            "total"          : len(rfm),
            "vip"            : int(rfm["IsVIP"].sum())                               if "IsVIP"         in rfm.columns else 0,
            "high_churn_risk": int((rfm["ChurnRisk"].astype(str)=="High").sum())    if "ChurnRisk"     in rfm.columns else 0,
            "avg_churn_proba": round(float(rfm["ChurnProba"].mean()), 4)             if "ChurnProba"    in rfm.columns else 0.0,
        },
        "inventory": {
            "total_skus"        : len(inv),
            "high_stockout_risk": int((inv["StockoutRisk"].astype(str)=="High").sum()) if "StockoutRisk" in inv.columns else 0,
            "dead_stock_skus"   : int(inv["IsDeadStock"].sum())                         if "IsDeadStock"  in inv.columns else 0,
        },
        "forecast": {"rows_available": len(DATA["forecast"])},
    }


# ════════════════════════════════════════════════════════════
#   ENDPOINT 3 – Churn Prediction
#   POST /predict/churn
#   Input : { "customer_id": "12345" }
#   Output: churn_proba, churn_risk, segment, RFM values,
#           plain-language CRM recommendation
# ════════════════════════════════════════════════════════════

@app.post("/predict/churn", response_model=ChurnResponse, tags=["Models"])
def predict_churn(req: ChurnRequest):
    df   = DATA["rfm"]
    if df.empty:
        raise HTTPException(503, "rfm_segments_churn.xlsx not loaded.")
    mask = df["CustomerID"].astype(str) == str(req.customer_id)
    if not mask.any():
        raise HTTPException(404, f"Customer '{req.customer_id}' not found.")
    row        = df[mask].iloc[0]
    churn_risk = str(row.get("ChurnRisk", "Unknown"))
    segment    = str(row.get("Segment",   "")) if "Segment" in df.columns else None
    return ChurnResponse(
        customer_id    = req.customer_id,
        churn_proba    = round(float(row.get("ChurnProba", 0.0)), 4),
        churn_risk     = churn_risk,
        segment        = segment,
        recency_days   = int(row.get("Recency",   0)),
        frequency      = int(row.get("Frequency", 0)),
        monetary       = round(float(row.get("Monetary", 0.0)), 2),
        recommendation = get_churn_recommendation(churn_risk, segment or ""),
    )


# ════════════════════════════════════════════════════════════
#   ENDPOINT 4 – Demand Forecast
#   POST /predict/demand
#   Input : { "stock_code": "85123A", "days_ahead": 30 }
#   Output: list of {date, yhat, yhat_lower, yhat_upper}
#           for the requested forecast horizon
# ════════════════════════════════════════════════════════════

@app.post("/predict/demand", response_model=DemandResponse, tags=["Models"])
def predict_demand(req: DemandRequest):
    df = DATA["forecast"]
    if df.empty:
        raise HTTPException(503, "demand_forecast.xlsx not loaded.")
    mask = df["StockCode"].astype(str) == str(req.stock_code)
    if not mask.any():
        raise HTTPException(404, f"StockCode '{req.stock_code}' not found.")
    sku_fc = df[mask].copy().sort_values("ds").tail(req.days_ahead)
    predictions = [{
        "date"      : str(r["ds"])[:10],
        "yhat"      : round(float(r.get("yhat",       0)), 2),
        "yhat_lower": round(float(r.get("yhat_lower", 0)), 2),
        "yhat_upper": round(float(r.get("yhat_upper", 0)), 2),
    } for _, r in sku_fc.iterrows()]
    avg_qty = None
    inv = DATA["inventory"]
    if not inv.empty:
        im = inv["StockCode"].astype(str) == str(req.stock_code)
        if im.any():
            avg_qty = round(float(inv[im].iloc[0].get("AvgDailyQty", 0)), 2)
    return DemandResponse(
        stock_code    = req.stock_code,
        forecast_days = len(predictions),
        predictions   = predictions,
        avg_daily_qty = avg_qty,
        message       = f"Forecast for {len(predictions)} days returned successfully.",
    )


# ════════════════════════════════════════════════════════════
#   ENDPOINT 5 – Customer Segment Score
#   POST /segment/score
#   Input : { "customer_id": "12345" }
#   Output: segment name, KMeans cluster, RFM score,
#           VIP flag, CLV estimate, churn risk
# ════════════════════════════════════════════════════════════

@app.post("/segment/score", response_model=SegmentResponse, tags=["Models"])
def segment_score(req: SegmentRequest):
    df   = DATA["rfm"]
    if df.empty:
        raise HTTPException(503, "rfm_segments_churn.xlsx not loaded.")
    mask = df["CustomerID"].astype(str) == str(req.customer_id)
    if not mask.any():
        raise HTTPException(404, f"Customer '{req.customer_id}' not found.")
    row = df[mask].iloc[0]
    return SegmentResponse(
        customer_id    = req.customer_id,
        segment        = str(row.get("Segment",       "Unknown")) if "Segment"        in df.columns else "N/A",
        kmeans_cluster = int(row.get("KMeans_Cluster", -1))        if "KMeans_Cluster" in df.columns else None,
        rfm_score      = round(float(row.get("RFM_Score", 0)), 2)  if "RFM_Score"      in df.columns else None,
        is_vip         = bool(row.get("IsVIP", False))              if "IsVIP"          in df.columns else None,
        clv_estimate   = round(float(row.get("CLV_Estimate", 0)), 2) if "CLV_Estimate" in df.columns else None,
        churn_risk     = str(row.get("ChurnRisk", "Unknown"))      if "ChurnRisk"      in df.columns else None,
    )


# ════════════════════════════════════════════════════════════
#   ENDPOINT 6 – Inventory Reorder
#   POST /inventory/reorder
#   Input : { "stock_code": "85123A" }
#   Output: EOQ, safety stock, reorder point, ABC-XYZ class,
#           dead-stock flag, plain-language recommendation
# ════════════════════════════════════════════════════════════

@app.post("/inventory/reorder", response_model=ReorderResponse, tags=["Models"])
def inventory_reorder(req: ReorderRequest):
    df = DATA["inventory"]
    if df.empty:
        raise HTTPException(503, "inventory_eoq.xlsx not loaded.")
    mask = df["StockCode"].astype(str) == str(req.stock_code)
    if not mask.any():
        raise HTTPException(404, f"StockCode '{req.stock_code}' not found.")
    row = df[mask].iloc[0]
    return ReorderResponse(
        stock_code    = req.stock_code,
        eoq           = round(float(row.get("EOQ",          0)), 0),
        safety_stock  = round(float(row.get("SafetyStock",  0)), 0),
        reorder_point = round(float(row.get("ReorderPoint", 0)), 0),
        avg_daily_qty = round(float(row.get("AvgDailyQty",  0)), 2),
        abc_class     = str(row.get("ABC",       "")) if "ABC"        in df.columns else None,
        xyz_class     = str(row.get("XYZ",       "")) if "XYZ"        in df.columns else None,
        abc_xyz       = str(row.get("ABC_XYZ",   "")) if "ABC_XYZ"    in df.columns else None,
        is_dead_stock = bool(row.get("IsDeadStock", 0)),
        stockout_risk = str(row.get("StockoutRisk", "")) if "StockoutRisk" in df.columns else None,
        recommendation= get_reorder_recommendation(row),
    )


# ════════════════════════════════════════════════════════════
#   ENDPOINT 7 – High-Risk Customers Batch
#   GET /predict/churn/high-risk?top_n=20&segment=Champions
#   Returns top-N highest churn probability customers.
#   Used for CRM bulk export and campaign targeting.
# ════════════════════════════════════════════════════════════

@app.get("/predict/churn/high-risk", tags=["Batch"])
def get_high_risk_customers(
    top_n  : int           = Query(20, ge=1, le=200),
    segment: Optional[str] = Query(None, description="Filter by segment name")
):
    df = DATA["rfm"].copy()
    if df.empty:
        raise HTTPException(503, "rfm_segments_churn.xlsx not loaded.")
    if segment and "Segment" in df.columns:
        df = df[df["Segment"].astype(str).str.lower() == segment.lower()]
    top = (df[df["ChurnRisk"].astype(str) == "High"]
             .sort_values("ChurnProba", ascending=False)
             .head(top_n))
    result = [{
        "customer_id" : str(r["CustomerID"]),
        "churn_proba" : round(float(r.get("ChurnProba", 0)), 4),
        "churn_risk"  : str(r.get("ChurnRisk",  "")),
        "segment"     : str(r.get("Segment",    "")) if "Segment" in df.columns else "",
        "monetary"    : round(float(r.get("Monetary", 0)), 2),
        "recency_days": int(r.get("Recency", 0)),
    } for _, r in top.iterrows()]
    return {"total_high_risk": len(result), "customers": result}


# ════════════════════════════════════════════════════════════
#   ENDPOINT 8 – Inventory Reorder Alerts Batch
#   GET /inventory/alerts?abc_class=A&top_n=50
#   Returns SKUs with high stockout risk.
#   Used for automated PO (Purchase Order) generation.
# ════════════════════════════════════════════════════════════

@app.get("/inventory/alerts", tags=["Batch"])
def get_reorder_alerts(
    abc_class: Optional[str] = Query(None, description="Filter: A, B, or C"),
    top_n    : int           = Query(50,   ge=1, le=500)
):
    df = DATA["inventory"].copy()
    if df.empty:
        raise HTTPException(503, "inventory_eoq.xlsx not loaded.")
    if abc_class and "ABC" in df.columns:
        df = df[df["ABC"].astype(str).str.upper() == abc_class.upper()]
    alerts = (df[df["StockoutRisk"].astype(str) == "High"].head(top_n)
              if "StockoutRisk" in df.columns else df.head(top_n))
    result = [{
        "stock_code"   : str(r["StockCode"]),
        "eoq"          : int(r.get("EOQ",           0)),
        "safety_stock" : int(r.get("SafetyStock",   0)),
        "reorder_point": int(r.get("ReorderPoint",  0)),
        "avg_daily_qty": round(float(r.get("AvgDailyQty", 0)), 2),
        "abc_xyz"      : str(r.get("ABC_XYZ", "")) if "ABC_XYZ" in df.columns else "",
        "stockout_risk": str(r.get("StockoutRisk", "")) if "StockoutRisk" in df.columns else "",
    } for _, r in alerts.iterrows()]
    return {"total_alerts": len(result), "skus": result}
