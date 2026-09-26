# 3D-ULPIN-DEMO

## Project Overview
3D-ULPIN-DEMO is a Flask-based proof of concept (PoC) for visualizing vertical property records (floors/units) on a real map context (Silk Board / HSR Layout, Bengaluru) using synthetic cadastral data.

## Executive Summary
The project demonstrates how a base ULPIN-like identifier can be extended to floor/unit-level records, displayed in both 2D (Leaflet) and 3D (Cesium), with role-based workflows for admins and surveyors. It is designed for demo/experimentation, not production land governance.

## Problem Statement
Traditional parcel-centric records do not directly represent vertical subdivisions (floors/units) in an interactive map-first workflow. This PoC explores a minimal web implementation for verticalized records.

## Background and Motivation
- Smart India Hackathon-style prototype context appears in UI content.
- Uses synthetic records while keeping real-world map coordinates to show the concept safely.

## Proposed Solution
- Flask web app with SQLite persistence.
- Role-based access (admin/surveyor) for creating surveyors and registering buildings.
- Automatic per-floor/per-unit record generation.
- 2D and 3D visualization plus optional AI narrative analysis.

## Project Objectives
- Demonstrate vertical cadastral modeling concepts.
- Show end-to-end entry-to-visualization flow in a lightweight stack.
- Provide deployable PoC defaults (Render + SQLite).

## Project Scope
### In Scope
- Demo login and role-based pages.
- Building registration with dimensions, floors, sanctioned floors, and metadata.
- Generated unit records and protected floor-record updates.
- Public and protected JSON endpoints.
- 2D/3D visualizations.

### Out of Scope
- Official cadastral/legal workflows.
- Verified ownership/legal adjudication.
- Production-grade identity, observability, HA/DR, compliance controls.

### Future Scope
- Replace synthetic data with authoritative datasets.
- Move from SQLite to PostgreSQL/PostGIS for scale/governance.

## Target Users
- Demo evaluators/stakeholders.
- Admin users managing surveyor accounts.
- Surveyors entering building records.

## Real-World Use Cases
- Demonstrating sanctioned vs observed floor checks.
- Showing floor-level property record updates in 3D context.
- Prototyping vertical property data capture UX.

## Key Features
- Public building map (`/`) with OpenStreetMap tiles.
- Admin/surveyor login (`/login`) and dashboard (`/dashboard`).
- Surveyor building registration (`/surveyor/buildings/new`).
- 3D building view (`/view/<id>`) and city 3D mode (`/3d`).
- Optional OpenRouter-powered building analysis (`/api/ai/analyze`).

## Functional Requirements (Implemented)
- User authentication (session-based login/logout).
- Admin can create surveyor users.
- Surveyor can register buildings and generate units.
- API access to building and unit records.
- Protected update API for floor records.

## Non-Functional Requirements (Current PoC State)
- Lightweight deployment (Flask + SQLite, no external DB required).
- Browser-based interaction via Leaflet/Cesium CDNs.
- Not optimized/tested for high concurrency or high availability.

## User Roles and Permissions
- **Public**: view map and public JSON (`/api/buildings`, `/api/buildings/<id>`).
- **Authenticated (admin/surveyor)**: dashboard access, protected record API.
- **Admin**: create surveyor accounts.
- **Surveyor**: register new buildings.

## System Workflow
1. User logs in.
2. Surveyor submits building metadata and dimensions.
3. App stores building in SQLite and auto-generates floor/unit rows.
4. Data appears in 2D map and 3D views.
5. Authorized user can update floor JSON records via city 3D editor.

## Technology Stack
- **Backend**: Python, Flask, Werkzeug security helpers.
- **Database**: SQLite (`ulpin_demo.db`).
- **Frontend**: Jinja templates, vanilla JS/CSS.
- **Mapping/3D**: Leaflet, Cesium, OpenStreetMap tiles.
- **Optional AI**: OpenRouter Chat Completions API.
- **Deployment**: Render (Blueprint via `render.yaml`), Gunicorn.

## System Architecture
Single Flask service serving server-rendered pages and JSON APIs, backed by SQLite. Client-side JS calls API endpoints for map/3D data and updates.

## Application and Data Flow
- `new_building` form -> DB insert (`buildings`, `units`) -> map/3D fetch from `/api/buildings*`.
- `/3d` editor -> POST `/api/buildings/<id>/floor-record` -> `units` update.
- `/view/<id>` AI button -> POST `/api/ai/analyze` -> OpenRouter (if key configured).

## Project Structure
```text
app.py
requirements.txt
render.yaml
.env.example
test_api.py
templates/
static/
```

## Database Design (Implemented)
SQLite tables created in `app.py`:
- `users` (username, password_hash, role)
- `buildings` (base ULPIN, geo/dimension/floor metadata, JSON fields)
- `units` (floor/unit records, ownership/legal metadata, JSON fields)

## API Documentation
### Public APIs
- `GET /api/buildings`
- `GET /api/buildings/<bid>`
- `GET /api/maps/resolve?url=...`

### Authenticated APIs
- `GET /api/buildings/<bid>/record`
- `POST /api/buildings/<bid>/floor-record`

### AI API
- `POST /api/ai/analyze` (requires `OPENROUTER_API_KEY` on server)

### Error Behavior
- Validation errors: HTTP 400
- Not found: HTTP 404
- Upstream AI/network issues: HTTP 502

## Authentication and Security
- Passwords are stored as hashes (`generate_password_hash`, `check_password_hash`).
- Session auth enforced with a `login_required` decorator.
- Secret key loaded from `SECRET_KEY` env var (fallback exists for development).
- **Current PoC gaps**: no CSRF protection, no rate limiting, no production hardening defaults.

## Installation and Setup
### Prerequisites
- Python 3.12+ (Render config pins 3.13.10).

### Setup
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open `http://127.0.0.1:5000`.

## Environment Variables
Defined in `.env.example` / `render.yaml`:
- `SECRET_KEY`
- `OPENROUTER_API_KEY` (optional unless AI endpoint used)
- `OPENROUTER_MODEL` (default `openai/gpt-oss-20b`)
- `APP_BASE_URL`
- `PYTHON_VERSION` (Render blueprint)

## Local Development
- Run app with `python app.py` (debug mode in `__main__` path).
- SQLite DB file is auto-created and seeded on first run.

## Running and Deployment
- **Local**: `python app.py`
- **Production (Render)**: build `pip install -r requirements.txt`, start `gunicorn app:app`
- Deployment blueprint provided via `render.yaml`.

## User Guide
- Visit `/` for map view.
- Use `/login` with seeded demo accounts:
  - `admin / admin123`
  - `surveyor1 / survey123`
- Admin creates surveyors from dashboard.
- Surveyor registers buildings from `/surveyor/buildings/new`.
- Open `/view/<id>` or `/3d` for 3D interactions.

## Screenshots / Demo
No screenshots or demo media files are committed in this repository.

## Testing Strategy and Observed Results
This repository does not include a formal unit/integration test suite (e.g., pytest tests for app routes). Available validations were executed:

1. `pip install -r requirements.txt` ✅
2. `python -m compileall app.py test_api.py` ✅
3. `flask --app app routes` ✅ (application imports and routes load)
4. `python test_api.py` ⚠️ exited with:
   - `ERROR: OPENROUTER_API_KEY is not set.`
   - Exit code `2` (expected when key is not configured)

## Performance
No measured benchmarks (latency/throughput/P95/P99) are present in this repository.

## Limitations
- Synthetic building/unit/ownership data.
- SQLite is not ideal for multi-user production scale.
- External CDN/runtime dependencies (Leaflet/Cesium/OSM/OpenRouter availability).

## Known Issues
- `python test_api.py` fails without `OPENROUTER_API_KEY`.
- Demo credentials are insecure for production and must be changed.

## Troubleshooting
- **Login fails**: verify seeded credentials exist and DB is writable.
- **AI analysis fails**: set `OPENROUTER_API_KEY`, verify outbound network, check upstream status.
- **Map link resolve errors**: ensure Google Maps URL contains resolvable coordinates.

## Logging and Monitoring
- No structured logging/metrics/tracing stack is configured in-repo.
- Errors are surfaced via Flask responses/flash messages.

## CI/CD
- No repository `.github/workflows/*` pipeline is present in this clone.
- Runtime checks were performed manually via local commands listed above.

## Backup, Privacy, and Compliance
- No automated backup/recovery policy is implemented in-repo.
- PoC uses synthetic ownership data by default; treat any real data input as sensitive.
- No explicit compliance framework implementation is documented.

## Dependencies and Integrations
- Python packages: `Flask`, `gunicorn`, `requests`.
- Integrations: OpenStreetMap tile service, Leaflet CDN, Cesium CDN, optional OpenRouter API.

## Versioning and Releases
- No formal semantic versioning or release process is documented in-repo.

## Roadmap / Future Improvements
- PostGIS-backed geospatial persistence.
- Stronger authN/authZ and audit controls.
- Production observability and CI/CD workflows.

## Contribution and Development Guidelines
- Keep changes small and evidence-based.
- Validate app startup and route loading before merging docs/code changes.
- For feature work, add automated tests where practical.

## Branching / Commit / PR Guidance
No explicit branching or commit convention is documented in the repository today.

## License
See [`LICENSE`](./LICENSE). This repository is licensed under the MIT License.

## Authors / Contributors
- Paladugu Ganesh Naidu (repository owner)

## Acknowledgements
- OpenStreetMap contributors
- Leaflet and Cesium open-source communities

## References
- Flask: https://flask.palletsprojects.com/
- Leaflet: https://leafletjs.com/
- CesiumJS: https://cesium.com/platform/cesiumjs/
- OpenStreetMap: https://www.openstreetmap.org/
- OpenRouter API: https://openrouter.ai/docs

## FAQ
**Is this an official land-record system?**  
No. This is a PoC with synthetic records.

**Why does AI analysis fail locally?**  
`OPENROUTER_API_KEY` is required for `/api/ai/analyze` and `test_api.py`.
