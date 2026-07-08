# SAMBA — Deployment Guide (local → cloud)

This maps the local Docker Compose stack onto managed cloud infrastructure (GCP
or AWS) without rearchitecting, and covers the non-functional requirements
(security, scalability, availability).

## 1. Service → cloud mapping

| Compose service | Deployment-diagram node | GCP | AWS |
|---|---|---|---|
| `postgis` | PostgreSQL + PostGIS | Cloud SQL for PostgreSQL (+PostGIS) | RDS PostgreSQL (+PostGIS) |
| `minio` | Object storage | Cloud Storage (GCS) | S3 |
| `redis` | Message queue | Memorystore / Pub/Sub | ElastiCache / SQS |
| `api` (×3) | Backend API + web servers | Cloud Run / GKE (N replicas) | ECS/Fargate / EKS |
| `lb` | Load balancer | Cloud Load Balancing | ALB |
| `worker` | Data-processing workers | Cloud Run jobs / GKE | ECS tasks / EKS |
| `inference` | ML inference server | Cloud Run / GKE (CPU) | ECS / EKS |
| `training` | ML training server (GPU) | Vertex AI / GKE GPU node | SageMaker / EKS GPU |
| `web` | Dashboard | Cloud Storage + CDN / Cloud Run | S3 + CloudFront |

The code is written against **interfaces** (S3-compatible object storage, a
Redis/RQ queue behind a `get_queue()` accessor, provider adapters behind clean
contracts), so swapping MinIO→GCS or Redis→Pub/Sub is a config/adapter change,
not a rewrite (NFR-6, NFR-7).

## 2. Running the load-balanced stack locally

```bash
docker compose -f docker-compose.yml -f docker-compose.lb.yml up -d --scale api=3
# verify traffic spreads across replicas:
for i in $(seq 1 6); do curl -s localhost:8000/health | jq -r .instance; done
```

`infra/nginx/lb.conf` round-robins across replicas via the Docker DNS resolver;
in cloud this is a managed L7 load balancer instead.

## 3. Security (NFR-1)

- **TLS/HTTPS everywhere**: terminate TLS at the cloud load balancer (managed
  certs). Internal service-to-service traffic runs on the private network.
- **Auth**: Argon2 password hashing + JWT bearer tokens. Set a strong
  `JWT_SECRET` from the secret manager (never the `.env.example` default):
  `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
- **Secrets**: `JWT_SECRET`, DB credentials, `MINIO/S3` keys, and the **GEE
  service-account JSON** come from Secret Manager / SSM — mount the GEE key at
  `GEE_SERVICE_ACCOUNT_JSON` and set `GEE_PROJECT`. Never bake secrets into images.

## 4. Scalability (NFR-3)

- **API**: stateless — scale horizontally behind the LB (`--scale api=N` / set
  replica count). No sticky sessions needed (JWT is stateless).
- **Workers**: scale by running more `worker` instances; RQ distributes jobs.
- **Inference**: stateless model server — scale horizontally; it loads artifacts
  from object storage on startup (`POST /reload` after a new training run).
- **Training**: on-demand GPU job, decoupled from inference.

## 5. Database migrations in production

Locally the `api` entrypoint runs `alembic upgrade head`. With multiple replicas,
run migrations as a **separate one-shot job/init container** before rolling out
API replicas, rather than racing on each replica start:

```bash
docker compose run --rm api alembic upgrade head
```

## 6. Availability & graceful degradation (NFR-5)

- Every service has a **health check** (`/health`, `/health/db`, DB `pg_isready`,
  Redis `ping`, MinIO `mc ready`). Wire these to the platform's liveness/readiness
  probes; target >95% uptime.
- **Graceful degradation**: dashboards read from PostgreSQL, which is decoupled
  from live external providers. If GEE/GBIF/NASA POWER are down, **ingestion**
  fails but the API keeps serving the last-ingested (cached) data. A biodiversity
  source failing doesn't sink the others (the composite provider isolates faults).

## 7. Going live on real data

Default is `INGESTION_MODE=sample` (deterministic synthetic data, no creds). To
pull real data:

1. Set `INGESTION_MODE=live`.
2. Provide the GEE service-account key + project (satellite).
3. GBIF, iNaturalist, and NASA POWER need no keys.
4. Trigger ingestion: `POST /api/v1/ingestion/run` (data-scientist role), then
   `POST /api/v1/ml/train` to retrain and refresh alerts.

## 8. Recommended production hardening (beyond this build)

- Pin CORS to the web origin (currently `*` for dev).
- Add rate limiting + request logging at the LB.
- Move report/artifact buckets to lifecycle-managed storage.
- Add Prometheus/OpenTelemetry metrics and centralized logs.
- Per-service images in cloud (split the single backend image) if you want
  independent build/deploy cadences.
