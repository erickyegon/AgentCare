# Deploying AgentCare

Two supported paths. **Docker Compose** is the fastest way to run the whole stack; **Render +
Vercel** gives you public URLs for the judged demo. The app runs with the deterministic **mock**
LLM provider by default, so it works with no API key — set `LLM_PROVIDER=anthropic` +
`ANTHROPIC_API_KEY` for genuine Claude reasoning.

---

## Option 1 — Docker Compose (local / any Docker host)

```bash
cp .env.example .env        # optionally set ANTHROPIC_API_KEY and LLM_PROVIDER=anthropic
docker compose up --build
```
- Web → http://localhost:3000 · API → http://localhost:8000/docs · Postgres → localhost:5432

On first boot the API migrates the schema, seeds synthetic data, and runs a few demo workflows so
the dashboards are populated.

---

## Option 2 — Render (backend + Postgres) + Vercel (frontend)

This gives two public URLs. Free tiers are fine for a demo (the Render free service sleeps when
idle and wakes on the next request).

### A. Backend + database → Render (Blueprint)

1. Push this repo to GitHub (done).
2. Go to **https://dashboard.render.com → New → Blueprint** and connect the repo.
   Render reads [`render.yaml`](../render.yaml) and provisions:
   - `agentcare-db` (PostgreSQL)
   - `agentcare-api` (the FastAPI Docker service, migrated + seeded on boot)
3. (Optional) In the `agentcare-api` service → **Environment**, set `LLM_PROVIDER=anthropic` and
   `ANTHROPIC_API_KEY` for real Claude. `SECRET_KEY` is auto-generated.
4. When it's live, note the API URL, e.g. `https://agentcare-api.onrender.com`
   (check `https://agentcare-api.onrender.com/health`).

### B. Frontend → Vercel

1. Go to **https://vercel.com/new** and import the repo.
2. Set **Root Directory** to `frontend`.
3. Add an environment variable:
   `NEXT_PUBLIC_API_URL = https://agentcare-api.onrender.com` (your Render API URL).
4. Deploy. Vercel gives you a URL like `https://agentcare.vercel.app`.

### C. Connect them (CORS)

In the Render `agentcare-api` service, set `BACKEND_CORS_ORIGINS` to your Vercel URL
(e.g. `https://agentcare.vercel.app`) and redeploy — or leave it as `*` for a quick demo
(safe here because auth uses Bearer tokens, not cookies).

Sign in with a demo account (`patient@agentcare.io` / `staff@agentcare.io`, password
`AgentCare!2026`) and run the flows in [`USER_GUIDE.md`](USER_GUIDE.md).

---

## Notes

- **Managed Postgres URLs** (`postgres://…`) are normalized automatically to the SQLAlchemy
  `postgresql+psycopg2://…` driver in `app/core/config.py`.
- **Railway** works the same way as Render: create a Postgres plugin + a service from
  `backend/Dockerfile`, set `DATABASE_URL`, and deploy the frontend from `frontend/Dockerfile`
  (build arg `NEXT_PUBLIC_API_URL`).
- The frontend Docker image bakes `NEXT_PUBLIC_API_URL` at **build** time — rebuild if the backend
  URL changes.
