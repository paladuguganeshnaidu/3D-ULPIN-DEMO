# 3D ULPIN Vertical Property Mapping Demo

A browser-first Flask proof of concept for demonstrating a **3D cadastral / vertical property mapping workflow** using a Bengaluru map context (Silk Board / HSR Layout) with synthetic demonstration records.

> **Status:** Prototype / demonstration only. This is not an official cadastral, land-title, ownership, or government ULPIN system.

## Overview

The application demonstrates:

- Public map view with registered-building points.
- Admin authentication and surveyor-account creation.
- Surveyor authentication and building registration.
- Automatic floor/unit generation.
- Hierarchical ULPIN-style examples.
- 3D Cesium visualization of floor volumes and basement volume.
- Sanctioned-vs-observed floor validation.
- Optional OpenRouter-powered AI analysis.
- SQLite persistence for a low-friction demo deployment.

All building attributes, ownership names, floor plans, geometry and ULPIN examples in the demo are **synthetic**.

## Demo accounts

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Surveyor | `surveyor1` | `survey123` |

These credentials are for the demonstration only. Change them before any public or production deployment.

## Technology

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Server | Gunicorn |
| External integration | OpenRouter API (optional) |
| Data | SQLite |
| Mapping / 3D | Browser-side map/3D components used by the app |

Pinned runtime dependencies are declared in `requirements.txt`.

## Local development

### Prerequisites

- Python 3.x
- A working virtual environment
- Internet access if OpenRouter analysis is enabled

### Install

```bash
python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\activate
```

macOS / Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run:

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## AI configuration

Set the following environment variables only when using the optional AI analysis:

```text
OPENROUTER_API_KEY=your-key
OPENROUTER_MODEL=openai/gpt-oss-20b
```

The repository also provides `test_api.py` for checking the configured API/model path.

Do not commit API keys.

## Render deployment

The repository includes `render.yaml`.

Typical Render configuration:

```text
Build: pip install -r requirements.txt
Start: gunicorn app:app
```

For AI analysis, configure `OPENROUTER_API_KEY` in the service environment.

## Security notes

This demo contains fixed demonstration credentials and synthetic records. It should not be exposed as an authoritative land-record service.

Before production use, at minimum:

- Replace demo credentials with a managed identity system.
- Store passwords using strong password hashing.
- Use PostgreSQL/PostGIS rather than SQLite for multi-user production persistence.
- Add formal authorization policies and audit controls.
- Separate authoritative survey/registry data from AI-derived suggestions.
- Protect API keys and operational secrets with a secret manager.

## Data and legal scope

The map context is based on OpenStreetMap data. The repository explicitly treats its building attributes, ownership details, floor plans and ULPIN examples as synthetic demonstration data.

This project does **not** establish:

- legal ownership;
- legal parcel boundaries;
- an official national 3D ULPIN standard;
- survey-grade positional accuracy;
- production cadastral interoperability.

A production implementation would require authoritative parcel/survey sources, validated elevation data, approved plans and appropriate government/registry integration.

## Project scope

### In scope

- Demonstration of vertical property concepts.
- User-role workflow for admin and surveyor.
- Building/floor/unit registration.
- 3D visualization.
- Demo validation and optional AI analysis.
- Lightweight deployment suitable for demonstrations.

### Out of scope

- Official land-title issuance.
- Government registry integration.
- Survey-grade measurements.
- Production-scale geospatial data infrastructure.
- Legal ownership decisions.

### Future scope

- PostgreSQL/PostGIS persistence.
- Authoritative parcel and survey datasets.
- LiDAR / DSM / DEM pipelines.
- Stronger identity and role management.
- Formal audit and approval workflows.
- Production observability and infrastructure hardening.

## API / application surface

The application is a Flask web application. API routes should be treated as implementation details of the current prototype; the repository does not claim a stable public API contract.

## Testing and verification

The repository includes a local API test utility (`test_api.py`). No independent benchmark, load-test result, code-coverage percentage, P95/P99 latency, or production availability figure is claimed by this README.

Where a metric is not measured, it is intentionally not reported.

## License

No explicit open-source license is currently declared for this repository.

Unless a license is added by the copyright holder, the code remains subject to applicable copyright law and should not be treated as MIT/Apache/public-domain software.

## Author

Paladugu Ganesh Naidu

Repository: https://github.com/paladuguganeshnaidu/3D-ULPIN-DEMO
