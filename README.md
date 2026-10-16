# AIPlanX
AI-powered project planning with task breakdown, risk analysis, scheduling, resource allocation, and progress tracking.

## Run the web app
Copy `.env.example` to `.env` and set `GROQ_API_KEY` (and `GOOGLE_API_KEY` if you use Gemini paths).

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000`. FastAPI uses SQLite by default (`AIPlanX_STORE=sqlite`). CLI scripts still use JSON files unless you point them at the same store.
