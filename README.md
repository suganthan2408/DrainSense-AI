# DrainSense AI

**India-capable geographic filtering with current demonstration data for Coimbatore, Tamil Nadu**

Built for [Environmental Hacks 2026](https://wemakedevs.org) by WeMakeDevs and AWS — Heat & Water track.

---

## The Problem

Urban communities in Coimbatore experience waterlogging during heavy monsoon rainfall. Local drainage inspectors and disaster-response coordinators need better tools to identify which zones need attention first, understand what evidence supports elevated risk, and decide what to do before conditions worsen.

Most existing tools stop at coloured map markers. DrainSense AI goes further by answering: **which zone needs attention first, why, and what specifically should be done?**

---

## What DrainSense AI Does

DrainSense AI is an evidence-based, action-oriented flood-risk decision-support system.

The core workflow:

```
Environmental data → Feature engineering → Heuristic risk score
→ Evidence explanation → Intervention Priority Queue
→ Configured Strands model attempt or deterministic fallback
→ Outcome recording → Model evaluation
```

Key features:
- **Intervention Priority Queue** — zones ranked by risk score × confidence × urgency
- **Evidence-linked recommendations** — each intervention cites the specific factors behind it
- **Strands Agent integration** — Bedrock is the default provider; local Ollama is optional. If the configured provider is unavailable, a deterministic fallback is returned and labelled.
- **Prediction + Outcome tracking** — records whether waterlogging occurred after each prediction
- **Model evaluation** — precision, recall, F1 computed once enough verified outcomes exist
- **Transparent data labelling** — synthetic data is clearly marked; heuristic scores are not misrepresented as flood probabilities

**Target user:** Municipal drainage inspector or local disaster-response coordinator in Coimbatore.

---

## Geographic Coverage

The application includes a national overview and dependent state, district, and monitoring-zone filters. Nine state/UT reference rows are seeded, but their official identifiers and coverage have not been verified. The only district currently present is an unverified Coimbatore reference; the eight existing Coimbatore zones remain linked to it. This is not nationwide monitoring coverage, and other locations have no imported zones, boundaries, or observations.

District reference data can be added idempotently from a verified, normalized Government of India Local Government Directory (LGD) CSV:

```powershell
python manage.py import_lgd_districts .\data\verified-lgd-districts.csv --source-url https://lgdirectory.gov.in/
```

The import requires state and district names, stable local state codes, state type, official LGD codes, and provenance. It does not create monitoring zones or synthetic observations. No official LGD district export has been imported in this repository state.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, Django 4.2, Django REST Framework 3.14 |
| Database | SQLite (dev) / PostgreSQL (production) |
| ML | scikit-learn 1.9, heuristic scorer + evaluation pipeline |
| Frontend | React 18, Leaflet + OpenStreetMap, recharts |
| Agent | Strands Agents SDK 1.59; Bedrock default or optional local Ollama provider |
| Forecast data | Open-Meteo API (free, CC BY 4.0, no key required) |
| Version control | Git (public repository publication not verified) |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  React Frontend                      │
│  Dashboard │ Risk Map │ Zone Detail │ Queue │ Outcomes│
└────────────────────┬────────────────────────────────┘
                     │ REST API (JSON)
┌────────────────────▼────────────────────────────────┐
│              Django REST Framework                   │
│  zones/ │ observations/ │ interventions/ │ outcomes/ │
│  agent/                                             │
└────────────────────┬────────────────────────────────┘
          ┌──────────┼──────────────────┐
          │          │                  │
    ┌─────▼────┐  ┌──▼──────┐   ┌──────▼───────┐
    │ SQLite / │  │ ML Risk │   │ AWS Strands  │
    │ Postgres │  │ Scorer  │   │ Agent (SDK)  │
    └──────────┘  └─────────┘   └──────┬───────┘
                                       │
                               ┌───────▼──────────┐
                               │ Configured model │
                               │ Bedrock or local │
                               │ Ollama provider  │
                               └──────────────────┘
          ┌──────────────────────────┐
          │ Open-Meteo Forecast API  │
          │ (fetch on request; no key)│
          └──────────────────────────┘
```

---

## Setup

### Prerequisites
- Python 3.12 (recommended; the pinned numerical dependencies are not verified on Python 3.13)
- Node.js 18+
- Git

### 1. Configure
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

AWS credentials are not required to run the app. The default Bedrock provider will return a clearly labelled deterministic fallback when credentials are absent. The example Django secret is for local development only; configure a private `DJANGO_SECRET_KEY` and set `DJANGO_DEBUG=False` before deployment. Do not put real credentials in source control.

### 2. Backend
```powershell
Set-Location backend
python manage.py migrate
# For a new, empty demo database only:
python manage.py seed_zones
python manage.py seed_observations
python manage.py runserver
```

Do not run the seed commands against a database containing user data: `seed_zones` updates the seeded zone records, and `seed_observations` adds synthetic observations and attempts a forecast fetch. The existing database is not reset by this setup.

Backend serves at: http://localhost:8000  
API docs: http://localhost:8000/api/schema/swagger-ui/

### 3. Frontend (in a separate terminal)
```powershell
Set-Location frontend
npm install
npm run dev
```

Frontend serves at: http://localhost:3000

### 4. Strands model provider (optional)

Bedrock is the default provider. To attempt a Bedrock call, provide valid credentials through your local environment or `.env`, set the AWS region, and ensure the model is enabled for the account:
```
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
```

Alternatively, install and start Ollama yourself, pull the desired model, then set these local `.env` values:
```
AGENT_MODEL_PROVIDER=ollama
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL_ID=llama3.2:3b
```

Run `ollama pull llama3.2:3b` after installing Ollama. Ollama uses the genuine Strands Agent integration without AWS credentials, but it is local execution, not evidence of Amazon Bedrock/AWS service usage. A configured provider or SDK status is not proof of a successful model call; verify an individual explanation reports `execution_status: success` and the expected provider/model. Provider failures use the deterministic fallback.

---

## Running Tests & Building

### Backend Tests
```bash
cd backend
python manage.py test tests --verbosity=2
```
The current suite contains **59 tests**, including geography filters/import idempotence, scoped outcome/forecast behavior, risk-input freshness, forecast ingestion errors, outcome validation, synthetic-outcome exclusion, and Strands provider/fallback behavior. Strands provider invocation is mocked in tests; these tests do not verify a live model execution.

### Frontend Build
```bash
cd frontend
npm run build
```
Production build compiles with Vite and verifies all JSX syntax, component dependencies, and bundle packaging.

---

## Data Sources

| Source | Type | License | Use |
|--------|------|---------|-----|
| Open-Meteo | External forecast API; fetched on request | CC BY 4.0 | Forecasts only after a successful fetch |
| IMD rainfall classification | Reference | Public | Heuristic threshold calibration |
| Zone attributes | **Synthetic demonstration** | N/A | Geographic zones (NOT official CMC data); no SRTM ingestion |
| Seeded rainfall observations | **Synthetic demonstration** | N/A | Demonstration only; not live observations |

**Important:** Zone attributes and seeded rainfall observations are synthetic demonstration data.  
They are clearly labelled in the application and are not official Coimbatore Municipal Corporation records.

---

## ML Model

The current model is a **documented heuristic risk scorer** (`ml/risk_scorer.py`):
- Score: 0–100 (NOT a probability percentage)
- 6 weighted components: rainfall intensity, forecast, elevation, drainage, imperviousness, history
- Weights based on IMD guidelines and urban flood literature — not tuned on a validation dataset
- Designed to be replaced by a validated ML model once labeled outcome data is available
- Evaluation metrics (precision, recall, F1) computed only when ≥10 verified outcomes exist

---

## AWS Integration

The `backend/agent/strands_agent.py` module uses the **Strands Agents SDK** (open-source, PyPI: `strands-agents`). Bedrock is the default provider; optional Ollama support is available for local model execution. The integration is designed to:
1. Receive structured, validated zone + assessment data
2. Return a JSON explanation: risk summary, contributing factors, recommended action, uncertainty
3. Require human verification for HIGH/CRITICAL urgency interventions
4. Return a labelled deterministic fallback when the selected provider is unavailable

No Bedrock or Ollama model execution has been verified in the current environment. The installed SDK and the provider-selection status endpoint are not evidence that a model ran. Local Ollama execution does not establish use of an AWS service; clarify the event's AWS eligibility requirement with the organizers.

The agent explains existing predictions — it does not fabricate sensor readings or model metrics.

---

## Limitations

- Zone data is synthetic — not from official CMC drainage maps
- Nine state/UT references are present, but official coverage is unverified; only one unverified district and eight Coimbatore demonstration zones are populated
- No verified district boundaries or additional-location observations have been imported
- Heuristic scorer weights are not validated against historical outcomes
- No real-time sensor network integration
- Forecast data from Open-Meteo uses zone centroids (no spatial disaggregation)
- Bedrock requires AWS account/model access and may incur costs; actual execution and event eligibility are unverified
- Open-Meteo availability is external and forecasts are fetched on request; no live rainfall observation feed is integrated

---

## AI Tools Disclosure

- **Kiro (AWS)** — AI-assisted development environment used to scaffold, implement, and review the initial codebase.
- **Antigravity (Google DeepMind)** — Agentic AI pair programming environment used to audit, debug import and timezone issues, run backend/frontend test suites, and prepare submission materials.
- **Copilot SDK in VS Code** — used in the current project review and implementation session.
- Backend checks and the current 59-test suite passed; the frontend production build passed. This does not verify a live model call.

---

## License

The project code is available under the MIT License; see [LICENSE](LICENSE). This license does not replace the separate licenses and attribution requirements for third-party software, map tiles, or external data sources; see the Transparency page.
