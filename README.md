# BIOTILE

**A gift for the living things of the city.** BIOTILE turns a photo of a natural surface that is
demonstrably colonised in the city (bark, weathered rock, a washed-out mortar joint) into a
**printable tool set** (matrix/stamp, casting frame, back plate) for standardised, *bioreceptive*
habitat tiles, using the [Tripo](https://www.tripo3d.ai) API. Schools and citizens document the
installed tiles for months in an open database, producing comparable field data on how surface
geometry affects colonisation by mosses, lichens, algae and micro-fauna.

*Tripothon S1 · Direction track: App · Tool track: Tripo.* Plastic is a tool, never habitat.

> Deutsche Fassung: [README.de.md](README.de.md) · Full concept (German): [docs/PROJECT_BRIEF.de.md](docs/PROJECT_BRIEF.de.md)

## What it does

```
photo ──► Tripo image-to-model (PBR, delight, fixed seeds)
      ──► align (PCA) · orthographic max-Z raster · detrend
      ──► rotate main structure "along the flow" (FFT anisotropy)
      ──► seamless (periodic-plus-smooth, Moisan 2011) · macro/meso band split
      ──► + moss nests in the natural hollows, fed by rills along the valleys (or diagonal channels)
      ──► draft-angle limiting (cone erosion) · edge mode · min-thickness · shrinkage
      ──► tile code embossed on the front (BT-XXXXXX)
      ──► tools: matrix + frame + back plate (slanted hanging holes) + hole punch (STL/3MF)
      ──► ISO 25178 + habitat metrics · PDF instructions · reference card · design.json
```

* **Macro relief from Tripo geometry, micro relief from the PBR normal map** (micro band: v1).
* Tool sizes are compensated for clay shrinkage (`s = 1/(1-shrink)`) and checked against the
  printer build volume (Bambu Lab A1 mini / P1S).
* Every design stores model/texture/raster seeds and the pipeline version, so results are
  reproducible: same input + params + seeds = same height-field hash.
* Square tiles or hexagonal tiles ("Barcelona mode", after Gaudí's paving tile): everything is
  computed on the tiling lattice's torus, so joints are seamless by construction.
* Each pattern has a code (`BT-XXXXXX`, embossed on the front); every hanging tile gets a number
  (`BT-XXXXXX-001`, `-002`, …), a printable photo card (ArUco markers, colour patches, 50 mm
  scale, QR code), an optional position (rounded publicly; never exact for schools) and a photo log.

## For the jury

* **Jury login:** click "Jury login" on the login page: no email, no invite code. The shared jury
  account has its own small generation limit; a global daily cap protects the credit budget.
* **Map:** the dots in Barcelona are example locations for the presentation.
* **Demo data:** patterns marked "(Beispiel)" come from synthetic stand-in models.

## Quick start

### Docker (mock mode, no Tripo key needed)

```bash
cp .env.example .env
docker compose up --build
```

Open <http://localhost:8080>. The API container seeds the gallery with REF-FLAT, REF-GEO and three
synthetic library surfaces on first start.

### Without Docker (SQLite, local files, in-process jobs)

Requirements: [uv](https://docs.astral.sh/uv/) (installs Python 3.11) and Node.js ≥ 20.

```bash
uv sync
uv run python scripts/seed_demo.py              # optional: example designs
uv run uvicorn biotile_api.main:app --port 8000
# second terminal
cd apps/web && npm install && npm run dev       # http://127.0.0.1:5173
```

### Accounts and invite codes

Registration needs an invite code. Codes are created on the server only and are never stored in
plain text (only an HMAC keyed with `SECRET_KEY`):

```bash
uv run python scripts/invites.py init                                   # once: SECRET_KEY in .env
uv run python scripts/invites.py create --note "School X" --uses 1 --days 60
uv run python scripts/invites.py list
```

Every account has a generation limit (`GENERATION_LIMIT_MOCK`, `GENERATION_LIMIT_LIVE`) plus a
global daily cap (`GLOBAL_DAILY_GENERATION_CAP`), enforced atomically on the server.

### Going live with Tripo

1. Put the key into `.env` (never commit it): `TRIPO_MODE=live` and `TRIPO_API_KEY=...`
2. Optional: `TRIPO_RECORD=true` stores each round trip as a fixture in
   `tests/fixtures/tripo/recorded/<sha256>/`, and the mock then replays it for the same photo.
3. Restart the API (and the worker in Docker). The banner switches from *mock* to *Tripo live*.

The key is only read server side; it never reaches the browser, the database or logs.

## Hosting

- **Frontend on Netlify:** `netlify.toml` builds `apps/web` and proxies `/api/*` to the backend. Set the backend host in that file.
- **Backend anywhere that runs Docker** (Render, Fly.io, Railway, a small VPS): use the `Dockerfile` or `docker-compose.yml`. Set the secrets as environment variables of that service, never in the repo:
  - `TRIPO_API_KEY` (the `tsk_…` key, not the `tcli_…` client id)
  - `SECRET_KEY`
  - `COOKIE_SECURE=true`
  - `TRIPO_MODE=live`
- Give it a persistent volume for `var/` (SQLite and files) or use Postgres/S3.
- Netlify alone cannot run the Python geometry pipeline. Without a backend, the hosted page has no generation, login or map.

## Tests

```bash
uv run pytest
```

Covers the mandatory geometry tests of brief 13.3: periodicity, watertight meshes, minimum
material thickness, maximum flank angle, build-volume fit per printer, shrinkage back-calculation
(fired size = 150 mm), hanging points vs. channels, determinism (hash). It also covers the
Tripo client (request schema, error codes 2010/1004, back-off polling, record/replay) and the API
end to end.

## Repository

```
apps/web                    React + Vite + TypeScript, three.js relief editor, i18n (EN/DE)
services/api                FastAPI, Tripo client (live/mock/recording), DB models, storage
services/worker             RQ worker entry points
packages/biotile_geometry   pipeline, functional layer, tools, metrics, PDFs, constants.py
data/library                surface library (19 entries, prompt templates for text mode v1)
tests                       geometry, Tripo, API tests; fixtures/tripo (synthetic stand-ins)
docs                        concept, method notes, printing & casting guide
```

## Status (hackathon MVP)

Done: photo/library/reference → Tripo (mock + live client) → relief pipeline → editor with 3D and
3 × 3 seam preview, checks panel → tool package ZIP → gallery, design pages, remix lineage → tile
registration with compass helper → reference card PDF → observations.

Next (v1): text and hybrid mode, micro band from the normal map, concrete back plate with M6
sleeves, half channels, walls with REF checks and randomisation, drill template, ArUco-based green
cover analysis, school accounts with quotas, moderation.

**Open, blocking for public STLs from real Tripo output:** the Tripo terms of service on
redistributing generated meshes (brief 13.2). The included fixtures are synthetic.

## Licences

Code: [MIT](LICENSE) · Designs/STL: [CC BY-SA 4.0](LICENSE-DESIGNS) · Data: [CC BY 4.0](LICENSE-DATA)

Key sources: Mustafa et al. 2021 (*Sustainability* 13:7453), Jakubovskis 2025 (*Buildings* 15:3646),
Larrieu et al. 2018, Moisan 2011, Schell et al. 2024 (surfalize). See the Method page in the app.
