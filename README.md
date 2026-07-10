# SAMBA — System for the Administration of Malagasy Biodiversity Assessment

A platform for tracking deforestation, climate trends, and biodiversity loss in
Madagascar. It integrates satellite imagery, climate datasets, and community
biodiversity observations to detect environmental risk and surface it through
APIs, dashboards, and reports — built to the SRS + UML diagrams.

**Status: Phases 1–6 complete.** Ingestion → processing → ML → alerts → API →
dashboard → load-balanced deployment all run end-to-end on sample data (no
external credentials required).

---

## Architecture (maps to the SRS deployment diagram)

One backend image (`samba-backend`, built from `./api`) runs in four roles via
different commands; the frontend and infra are separate.

| Compose service | Deployment-diagram node | Cloud analogue |
|---|---|---|
| `postgis` | PostgreSQL + PostGIS | Cloud SQL / RDS |
| `minio` | Object storage | GCS / S3 |
| `redis` | Message queue | Pub/Sub / SQS |
| `api` (×N) | Backend API behind the web servers | Cloud Run / ECS |
| `lb` | Load balancer | Cloud LB / ALB |
| `worker` | Data-processing workers | Cloud Run jobs / ECS tasks |
| `inference` | ML inference server | CPU inference service |
| `training` | ML training server (GPU) | Vertex AI / SageMaker |
| `web` | Dashboard | Static hosting + CDN |

See [DEPLOYMENT.md](DEPLOYMENT.md) for the full cloud mapping and NFR coverage.

### Repository layout

```
samba/
├── api/                     # single backend image (api/worker/inference/training)
│   └── app/
│       ├── models/          # the 11 class-diagram entities (+ Region)
│       ├── core/            # security (Argon2/JWT), roles, RBAC
│       ├── ingestion/       # provider adapters (GEE / GBIF+iNaturalist / NASA POWER) + sample mode
│       ├── processing/      # cleaning + spatial-temporal alignment
│       ├── ml/              # change-point, SDM, SARIMA + training orchestrator + registry
│       ├── inference/       # inference server app
│       ├── services/        # service layer shaped after the diagram's methods
│       ├── api/routes/      # REST endpoints (FR-1…FR-7)
│       ├── workers/         # RQ worker + tasks
│       └── tests/           # 17 tests (unit + integration)
├── web/                     # React + TS + Vite dashboard (MapLibre + Recharts)
├── infra/nginx/             # load-balancer config
├── docker-compose.yml       # base stack
├── docker-compose.lb.yml    # load-balanced overlay (api replicas + nginx LB)
└── DEPLOYMENT.md
```

---

## Quick start

**Prerequisites:** Docker Desktop (Compose v2).

```bash
cp .env.example .env        # set a real JWT_SECRET before any non-local use
docker compose up -d --build
```

The `api` service runs migrations on startup (PostGIS + all tables + spatial
indexes + region seed). Then:

| URL | What |
|---|---|
| http://localhost:8080 | **Dashboard** (login: `ds@example.com` / `password123` once created) |
| http://localhost:8000/docs | API docs (Swagger) |
| http://localhost:8000/health/db | DB + PostGIS readiness |
| http://localhost:9002/health | Inference server |
| http://localhost:9001 | MinIO console |

### Load the system with data (sample mode, no credentials)

```bash
# 1. create a data-scientist user
docker compose exec api python -c "from app.db import SessionLocal; from app.services.user_service import UserService; from app.core.roles import RoleEnum; db=SessionLocal(); UserService(db).create_user('Data Sci','ds@example.com','password123',RoleEnum.DATA_SCIENTIST)"

# 2. log in and ingest (inline for a quick demo)
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login -d 'username=ds@example.com&password=password123' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -s -X POST localhost:8000/api/v1/ingestion/run -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"start":"2022-01-01","end":"2024-12-31","run_async":false}'

# 3. train models (detects deforestation, fits SDM + climate forecasts, generates alerts)
docker compose --profile training run --rm training
curl -s -X POST localhost:9002/reload   # inference picks up the new SDM
```

Then open the dashboard — the map shows deforestation risk, Trends shows the
NDVI decline + climate forecast, Alerts lists the generated warnings, and
Reports exports CSV/PDF.

### Tests

```bash
docker compose exec api pytest -q      # 17 passed
```

### Load-balanced (3 API replicas behind nginx)

```bash
docker compose -f docker-compose.yml -f docker-compose.lb.yml up -d --scale api=3
for i in $(seq 1 6); do curl -s localhost:8000/health | python -c "import sys,json;print(json.load(sys.stdin)['instance'])"; done
```

---

## Data providers (locked)

Google Earth Engine (satellite NDVI), GBIF + iNaturalist (species), NASA POWER
(climate). Default `INGESTION_MODE=sample` uses deterministic synthetic data.
Set `INGESTION_MODE=live` + a GEE service-account key to pull real data (see
DEPLOYMENT.md §7). GBIF/iNaturalist/NASA POWER need no keys.

## Roles (RBAC — FR-6.2)

`data_scientist`, `environmental_researcher`, `ngo_policymaker`,
`student_public` (default), `administrator` (passes every check).

---

## Assumptions & simplifications (flagged)

1. **`SpeciesObservation.location` is a POINT**, not a POLYGON as the class
   diagram draws it — real GBIF/iNaturalist occurrences are points.
2. **`Region` is a pragmatic addition** (not in the class diagram) with
   approximate bounding-box polygons for 8 Madagascar regions — swap in real
   administrative boundaries later; nothing else depends on the box shape.
3. **Additions beyond the diagram** (all annotated in code): `created_at`;
   `PredictionResult.payload`; alert `alert_type`/`region_id`/`notified`;
   `region_id` FKs on datasets; `Report.user_id/params/object_key`.
4. **Single backend image** for api/worker/inference/training (a common pattern);
   split per-service in cloud if you want independent deploy cadences.
5. **The SDM is a weak baseline** on synthetic data (`cv_accuracy` ≈ base rate)
   because the sample richness doesn't depend on covariates — the train→store→
   serve pipeline is what's demonstrated; real covariate-driven data will make it
   discriminate. Per-species Maxent/RF SDMs are a later extension.
6. **Deep learning deferred**: deforestation uses classical change-point
   detection (Pettitt), not an LSTM/CNN — noted as the future swap. `torch` is
   intentionally not installed to keep the image light.
7. **CORS is open** (`*`) for dev; pin to the web origin in production.

---

## Roadmap

- [x] **Phase 1 — Foundation:** Compose, 11 data models + migrations, auth, RBAC, health checks.
- [x] **Phase 2 — Ingestion & processing:** GEE / GBIF+iNaturalist / NASA POWER adapters (sample+live), queue + workers, cleaning, spatial-temporal alignment.
- [x] **Phase 3 — ML:** deforestation change-point detection, SDM, SARIMA forecasting; training + inference decoupled.
- [x] **Phase 4 — Alerts, API, RBAC:** alert generation from ML outputs, full FR endpoints, reports (CSV/PDF).
- [x] **Phase 5 — Frontend:** map, heatmap, trend dashboards, alert feed, report export.
- [x] **Phase 6 — Hardening:** 17 tests, load-balanced multi-instance API, deployment docs.
