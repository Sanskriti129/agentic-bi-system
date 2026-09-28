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
            (pandas KPIs)    (Claude API via        (SQLite memory.db)
                              Anthropic SDK)
```

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set your Anthropic API key
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Start the backend
```bash
python backend.py
# Server runs at http://localhost:8000
```

### 4. Open the frontend
Just open `frontend.html` in your browser (double-click it).

> **Note:** The frontend connects to `http://localhost:8000` by default.
> You can change this in the sidebar's Config section.

---

## How It Works

| Step | Agent | What it does |
|------|-------|-------------|
| 1 | Data Analysis Agent | Reads CSV, computes KPIs (sales, profit, margin, top category, etc.) |
| 2 | Insight Generation Agent | Sends KPIs to Claude → returns 4 business insights |
| 3 | Root Cause Agent | Sends insights → Claude finds 3 root causes |
| 4 | Recommendation Agent | Sends root causes → Claude gives 3 actionable recommendations |
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
  **Anthropic Claude API** — much more reliable, no GPU needed.
- The CSV must have columns like `Sales`, `Profit`, `Discount`, `Category`, 
  `Region`, `Segment` for full KPI extraction (Superstore format).
  Other CSVs work too — numeric columns will be picked up automatically.
