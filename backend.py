"""
Agentic Business Intelligence System - FastAPI Backend
Uses Anthropic Claude API instead of Ollama so it works anywhere.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import pandas as pd
import sqlite3
import os
import json
import anthropic
from datetime import datetime
from typing import Optional
import io

app = FastAPI(title="Agentic BI System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Anthropic client (reads ANTHROPIC_API_KEY from env) ──────────────────────
client = anthropic.Anthropic()

# ─── In-memory dataframe store (keyed by session) ─────────────────────────────
_df_store: dict[str, pd.DataFrame] = {}

# ─── SQLite memory ────────────────────────────────────────────────────────────
DB_PATH = "memory.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            kpis TEXT,
            insights TEXT,
            root_causes TEXT,
            recommendations TEXT,
            status TEXT DEFAULT 'new'
        )
    """)
    conn.commit()
    return conn


# ─── Agent helpers ────────────────────────────────────────────────────────────

def llm_call(system: str, user: str, max_tokens: int = 800) -> str:
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}]
    )
    return msg.content[0].text


# ─── API Routes ───────────────────────────────────────────────────────────────

@app.get("/")
def index():
    """Serve the web UI so the whole app lives at one URL."""
    return FileResponse(os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend.html"))


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Agentic BI System"}


@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)):
    """Upload a CSV file. Returns session_id and column preview."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV files accepted")
    
    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content), encoding="latin1")
    except Exception as e:
        raise HTTPException(400, f"Could not parse CSV: {e}")
    
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    _df_store[session_id] = df
    
    return {
        "session_id": session_id,
        "rows": len(df),
        "columns": list(df.columns),
        "preview": df.head(3).to_dict(orient="records")
    }


@app.post("/api/analyze/{session_id}")
def analyze(session_id: str):
    """Agent 1: Compute KPIs from uploaded data."""
    df = _df_store.get(session_id)
    if df is None:
        raise HTTPException(404, "Session not found. Upload a CSV first.")
    
    kpis = {}
    
    # Numeric KPIs
    for col in ["Sales", "Profit", "Discount", "Quantity"]:
        if col in df.columns:
            kpis[f"total_{col.lower()}"] = round(float(df[col].sum()), 2)
            kpis[f"avg_{col.lower()}"] = round(float(df[col].mean()), 4)
    
    kpis["total_orders"] = int(df.shape[0])
    
    if "Profit" in df.columns and "Sales" in df.columns and kpis.get("total_sales", 0) != 0:
        kpis["profit_margin_pct"] = round((kpis["total_profit"] / kpis["total_sales"]) * 100, 2)
    
    # Categorical breakdowns
    for group_col in ["Category", "Region", "Segment"]:
        if group_col in df.columns and "Sales" in df.columns:
            grouped = df.groupby(group_col)["Sales"].sum()
            kpis[f"top_{group_col.lower()}_by_sales"] = grouped.idxmax()
            kpis[f"bottom_{group_col.lower()}_by_sales"] = grouped.idxmin()
    
    if "Profit" in df.columns and "Region" in df.columns:
        kpis["worst_region_profit"] = df.groupby("Region")["Profit"].sum().idxmin()

    return {"kpis": kpis}


@app.post("/api/insights/{session_id}")
def generate_insights(session_id: str, body: dict):
    """Agent 2: Generate business insights from KPIs."""
    kpis = body.get("kpis", {})
    if not kpis:
        raise HTTPException(400, "kpis required in body")
    
    kpi_text = "\n".join(f"  • {k}: {v}" for k, v in kpis.items())
    
    insights_text = llm_call(
        system="You are a sharp business intelligence analyst. Be concise and actionable.",
        user=f"""Given these KPIs from a retail/business dataset:
{kpi_text}

Generate exactly 4 key business insights. Each must be specific to the numbers above.
Format strictly as:
[INSIGHT 1]: <text>
[INSIGHT 2]: <text>
[INSIGHT 3]: <text>
[INSIGHT 4]: <text>"""
    )
    
    insights = []
    for line in insights_text.strip().split("\n"):
        line = line.strip()
        if line.startswith("[INSIGHT"):
            parts = line.split("]: ", 1)
            if len(parts) == 2:
                insights.append(parts[1].strip())
    
    if not insights:
        insights = [insights_text.strip()]
    
    return {"insights": insights}


@app.post("/api/root-causes")
def root_causes(body: dict):
    """Agent 3: Root cause analysis."""
    insights = body.get("insights", [])
    kpis = body.get("kpis", {})
    
    if not insights:
        raise HTTPException(400, "insights required")
    
    insights_text = "\n".join(f"• {i}" for i in insights)
    kpi_text = "\n".join(f"• {k}: {v}" for k, v in kpis.items())
    
    rc_text = llm_call(
        system="You are a root cause analysis expert for business data.",
        user=f"""Business Insights:
{insights_text}

KPIs:
{kpi_text}

Identify exactly 3 root causes behind these patterns.
Format strictly as:
[ROOT CAUSE 1]: <cause> — <why it likely happened>
[ROOT CAUSE 2]: <cause> — <why it likely happened>
[ROOT CAUSE 3]: <cause> — <why it likely happened>"""
    )
    
    causes = []
    for line in rc_text.strip().split("\n"):
        line = line.strip()
        if line.startswith("[ROOT CAUSE"):
            parts = line.split("]: ", 1)
            if len(parts) == 2:
                causes.append(parts[1].strip())
    
    if not causes:
        causes = [rc_text.strip()]
    
    return {"root_causes": causes}


@app.post("/api/recommendations")
def recommendations(body: dict):
    """Agent 4: Strategic recommendations."""
    root_causes = body.get("root_causes", [])
    kpis = body.get("kpis", {})
    
    if not root_causes:
        raise HTTPException(400, "root_causes required")
    
    rc_text = "\n".join(f"• {c}" for c in root_causes)
    kpi_text = "\n".join(f"• {k}: {v}" for k, v in kpis.items())
    
    rec_text = llm_call(
        system="You are a strategic business advisor. Give specific, actionable recommendations.",
        user=f"""Root Causes:
{rc_text}

KPIs:
{kpi_text}

Provide exactly 3 actionable business recommendations.
Format strictly as:
[ACTION 1]: <recommendation> — Expected impact: <impact>
[ACTION 2]: <recommendation> — Expected impact: <impact>
[ACTION 3]: <recommendation> — Expected impact: <impact>"""
    )
    
    recs = []
    for line in rec_text.strip().split("\n"):
        line = line.strip()
        if line.startswith("[ACTION"):
            parts = line.split("]: ", 1)
            if len(parts) == 2:
                recs.append(parts[1].strip())
    
    if not recs:
        recs = [rec_text.strip()]
    
    return {"recommendations": recs}


@app.post("/api/save")
def save_to_memory(body: dict):
    """Memory Agent: Save pipeline results to SQLite."""
    conn = get_db()
    conn.execute(
        "INSERT INTO recommendations (timestamp, kpis, insights, root_causes, recommendations, status) VALUES (?,?,?,?,?,?)",
        (
            datetime.now().isoformat(),
            json.dumps(body.get("kpis", {})),
            json.dumps(body.get("insights", [])),
            json.dumps(body.get("root_causes", [])),
            json.dumps(body.get("recommendations", [])),
            "new"
        )
    )
    conn.commit()
    conn.close()
    return {"saved": True}


@app.get("/api/history")
def get_history():
    """Return past pipeline runs from memory."""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, timestamp, kpis, insights, recommendations, status FROM recommendations ORDER BY timestamp DESC LIMIT 10"
    ).fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            "id": row[0],
            "timestamp": row[1],
            "kpis": json.loads(row[2]),
            "insights": json.loads(row[3]),
            "recommendations": json.loads(row[4]),
            "status": row[5]
        })
    return {"history": history}


@app.post("/api/pipeline/{session_id}")
def run_full_pipeline(session_id: str):
    """Run the entire 4-agent pipeline end-to-end."""
    # Agent 1
    result1 = analyze(session_id)
    kpis = result1["kpis"]
    
    # Agent 2
    result2 = generate_insights(session_id, {"kpis": kpis})
    insights = result2["insights"]
    
    # Agent 3
    result3 = root_causes({"insights": insights, "kpis": kpis})
    rc = result3["root_causes"]
    
    # Agent 4
    result4 = recommendations({"root_causes": rc, "kpis": kpis})
    recs = result4["recommendations"]
    
    # Memory
    save_to_memory({"kpis": kpis, "insights": insights, "root_causes": rc, "recommendations": recs})
    
    return {
        "kpis": kpis,
        "insights": insights,
        "root_causes": rc,
        "recommendations": recs
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
