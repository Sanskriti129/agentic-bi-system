# Agentic BI System — Frontend + Backend

A full-stack implementation of your 4-agent Business Intelligence pipeline, 
now with a FastAPI backend and a polished web UI.

## Architecture

```
frontend.html  ←── HTTP/JSON ──→  backend.py (FastAPI)
                                       │
                     ┌─────────────────┼──────────────────┐
                     ▼                 ▼                   ▼
               Agent 1            Agents 2-4          Memory Agent
            (pandas KPIs)    (Groq API)          (SQLite memory.db)
```

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set your Groq API key
Get one at https://console.groq.com/keys, then:
```bash
export GROQ_API_KEY=gsk_...          # macOS/Linux
$env:GROQ_API_KEY="gsk_..."          # Windows PowerShell
```
Optional: `GROQ_MODEL` picks the model (default `openai/gpt-oss-120b`).

### 3. Start the backend
```bash
python backend.py
# Server runs at http://localhost:8000
```

### 4. Open the app
Go to http://localhost:8000 — the backend serves the web UI.
(You can also still open `frontend.html` directly in your browser.)

> **Note:** The frontend connects to `http://localhost:8000` by default.
> You can change this in the sidebar's Config section.

---

## Deploy (Render, free)

1. On [render.com](https://render.com), choose **New → Blueprint** and connect this repo.
   Render reads `render.yaml`.
2. Enter your `GROQ_API_KEY` when asked.
3. The app goes live at `https://<service-name>.onrender.com`.

> Free instances sleep when idle, so the first request can take ~30–60s.
> `memory.db` is reset on each redeploy.

---

## How It Works

| Step | Agent | What it does |
|------|-------|-------------|
| 1 | Data Analysis Agent | Reads CSV, computes KPIs (sales, profit, margin, top category, etc.) |
| 2 | Insight Generation Agent | Sends KPIs to the LLM → returns 4 business insights |
| 3 | Root Cause Agent | Sends insights → the LLM finds 3 root causes |
| 4 | Recommendation Agent | Sends root causes → the LLM gives 3 actionable recommendations |
| 5 | Memory Agent | Saves full run to SQLite (`memory.db`) |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload CSV file |
| POST | `/api/analyze/{session_id}` | Run Agent 1 (KPIs) |
| POST | `/api/insights/{session_id}` | Run Agent 2 (Insights) |
| POST | `/api/root-causes` | Run Agent 3 |
| POST | `/api/recommendations` | Run Agent 4 |
| POST | `/api/pipeline/{session_id}` | Run ALL agents in one call |
| POST | `/api/save` | Save results to memory |
| GET  | `/api/history` | Retrieve past runs |

## Notes

- **Original code used Ollama/Mistral** (local LLM). This version uses the 
  **Groq API** — fast, free tier available, no GPU needed.
- The CSV must have columns like `Sales`, `Profit`, `Discount`, `Category`, 
  `Region`, `Segment` for full KPI extraction (Superstore format).
  Other CSVs work too — numeric columns will be picked up automatically.
