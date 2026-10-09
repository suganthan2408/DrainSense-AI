# DrainSense AI

**Urban waterlogging risk and drainage intervention prioritisation — Coimbatore, Tamil Nadu**

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
→ AWS Strands Agent reasoning → Outcome recording → Model evaluation
```

Key features:
- **Intervention Priority Queue** — zones ranked by risk score × confidence × urgency
- **Evidence-linked recommendations** — each intervention cites the specific factors behind it
- **AWS Strands Agent** — generates natural-language explanations using Claude via Amazon Bedrock
- **Prediction + Outcome tracking** — records whether waterlogging occurred after each prediction
- **Model evaluation** — precision, recall, F1 computed once enough verified outcomes exist
- **Transparent data labelling** — synthetic data is clearly marked; heuristic scores are not misrepresented as flood probabilities

**Target user:** Municipal drainage inspector or local disaster-response coordinator in Coimbatore.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, Django 4.2, Django REST Framework 3.14 |
| Database | SQLite (dev) / PostgreSQL (production) |
| ML | scikit-learn 1.9, heuristic scorer + evaluation pipeline |
| Frontend | React 18, Leaflet + OpenStreetMap, recharts |
| AWS | Strands Agents SDK 1.59 (open-source), AWS Bedrock (Claude 3.5 Haiku) |
| Forecast data | Open-Meteo API (free, CC BY 4.0, no key required) |
| Version control | Git + GitHub |

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
                               │ Amazon Bedrock   │
                               │ Claude 3.5 Haiku │
                               └──────────────────┘
          ┌──────────────────────────┐
          │ Open-Meteo Forecast API  │
          │ (live, free, no key)     │
          └──────────────────────────┘
```

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### 1. Clone and configure
```bash
git clone https://github.com/YOUR_USERNAME/drainsense-ai.git
cd drainsense-ai
cp .env.example .env
# Edit .env with your settings
```

### 2. Backend
```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_zones
python manage.py seed_observations
python manage.py runserver
```

Backend serves at: http://localhost:8000  
API docs: http://localhost:8000/api/schema/swagger-ui/

### 3. Frontend
```bash
cd frontend
npm install --legacy-peer-deps
npm start
```

Frontend serves at: http://localhost:3000

### 4. AWS Strands Agent (optional)

To enable real AWS Bedrock calls, add to `.env`:
```
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_DEFAULT_REGION=us-east-1
```

Ensure Bedrock Claude 3.5 Haiku model access is enabled in your AWS account.  
Without credentials, the agent falls back to a deterministic structured explanation.

---

## Running Tests

```bash
cd backend
python manage.py test tests --verbosity=2
```

**34 tests** covering:
- Heuristic scorer component functions (rainfall intensity, elevation, drainage, etc.)
- Weight sum validation
- Integration: `score_zone()` end-to-end
- API: zones, assessments, interventions, outcomes, agent status

---

## Data Sources

| Source | Type | License | Use |
|--------|------|---------|-----|
| Open-Meteo | Live forecast API | CC BY 4.0 | Rainfall forecasts (real, live) |
| SRTM 30m DEM | Reference | NASA public | Informed elevation estimates |
| IMD rainfall classification | Reference | Public | Heuristic threshold calibration |
| Zone attributes | **Synthetic demonstration** | N/A | Geographic zones (NOT official CMC data) |
| Rainfall observations | **Synthetic demonstration** | N/A | Seeded for demonstration |

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

The `agent/strands_agent.py` module uses the **AWS Strands Agents SDK** (open-source, PyPI: `strands-agents`) with AWS Bedrock (Claude 3.5 Haiku) to:
1. Receive structured, validated zone + assessment data
2. Return a JSON explanation: risk summary, contributing factors, recommended action, uncertainty
3. Require human verification for HIGH/CRITICAL urgency interventions
4. Fall back deterministically when AWS is unavailable

The agent explains existing predictions — it does not fabricate sensor readings or model metrics.

---

## Limitations

- Zone data is synthetic — not from official CMC drainage maps
- Heuristic scorer weights are not validated against historical outcomes
- No real-time sensor network integration
- Forecast data from Open-Meteo uses zone centroids (no spatial disaggregation)
- AWS Bedrock requires account access and will incur costs

---

## AI Tools Disclosure

- **Kiro (AWS)** — AI-assisted development environment used to scaffold, implement, and review the codebase
- All generated code was reviewed, tested (34 tests), and verified by the team

---

## License

MIT License. See [LICENSE](LICENSE).

Third-party licenses: see Transparency page in the application.
