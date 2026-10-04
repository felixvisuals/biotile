# BIOTILE – working rules (short form of docs/PROJECT_BRIEF.de.md, section 0)

1. **No invented API parameters.** Tripo: only what the brief (section 7) documents. Where it says
   "verify", check https://developers.tripo3d.ai/en/docs and ask if in doubt.
2. **Mock first.** `TripoClient` with `LiveTripoClient` / `MockTripoClient` (+ `RecordingTripoClient`);
   switch with `TRIPO_MODE=mock|live`. Development and tests never spend credits.
3. **Deterministic, versioned pipeline.** Same input + params + seeds = same geometry. Any change that
   alters geometry bumps `PIPELINE_VERSION` in `packages/biotile_geometry/constants.py`.
4. **Scientific constants live in `packages/biotile_geometry/constants.py`**, each with a source comment.
5. **API key server side only.** Never in the browser, the repo or logs. `.env.example` holds placeholders.
6. **Geometry is tested** (`tests/test_geometry.py`, brief 13.3), not just looked at.
7. **UI language:** English default, German second (`apps/web/src/i18n`). i18n everywhere.
8. **Conflicts between the brief and a tempting simplification: ask**, do not deviate silently.

Layout: `packages/biotile_geometry` (pipeline, tools, metrics, PDFs) · `services/api` (FastAPI, Tripo
client, DB) · `services/worker` (RQ tasks) · `apps/web` (React/Vite/three.js) · `tests`.

Commands: `uv sync` · `uv run pytest` · `uv run uvicorn biotile_api.main:app --reload` ·
`cd apps/web && npm install && npm run dev` · `uv run python scripts/seed_demo.py`.
