# 3D ULPIN Vertical Property Mapping — Deployable PoC

A browser-first Flask PoC for demonstrating the core 3D cadastral workflow using a real Bengaluru map context (Silk Board / HSR Layout) and synthetic demo building records.

## Included workflow
- Public browser map with registered-building points
- Admin login
- Admin can create surveyor accounts
- Surveyor login
- Surveyor can register buildings
- Automatic floor/unit generation
- Hierarchical ULPIN examples
- 3D Cesium viewer with floor volumes and basement volume
- Sanctioned-vs-observed floor validation
- Optional OpenRouter AI analysis (server-side API key)
- SQLite database for zero-friction Render demo deployment

## Demo credentials
- Admin: `admin / admin123`
- Surveyor: `surveyor1 / survey123`

Change these before any public production use.

## Local run
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Render
Render settings:
- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:app`
- Set `OPENROUTER_API_KEY` in Environment Variables if AI analysis is needed.

A `render.yaml` is included for Blueprint deployment.

## AI configuration
Set `OPENROUTER_API_KEY` in Render before using the AI analysis button. The selected model defaults to `openai/gpt-oss-20b` and can be changed with `OPENROUTER_MODEL`. Test the key and model locally with:
```bash
python test_api.py
```

## Important scope note
This is a **PoC**, not an official cadastral or land-title system. Building attributes, ownership names, floor plans and ULPIN examples are synthetic. The base map is OpenStreetMap. The production version should replace synthetic geometry/attributes with authoritative parcel, survey, LiDAR/DSM, approved-plan and registry data, and move from SQLite to PostgreSQL/PostGIS.
# 3D-ULPIN-DEMO
