# SAMBA — two app servers behind a load balancer

Deploying SAMBA onto `web-01` / `web-02` **alongside** the two applications
already running there, without changing either of them.

## Topology

```
                          ┌───────────────────────┐
        samba.<domain> ──▶│  lb-01  (HAProxy)     │
        <existing host> ─▶│  one *:80 frontend,   │
                          │  Host-header ACL      │
                          └───────┬───────┬───────┘
                                  │       │
                 ┌────────────────┘       └────────────────┐
                 ▼                                          ▼
        ┌──────────────────┐                       ┌──────────────────┐
        │ web-01  :80      │                       │ web-02  :80      │
        │  nginx vhosts:   │                       │  nginx vhosts:   │
        │   rwanda (default)│                      │   rwanda (default)│
        │   samba  ─┐      │                       │   samba  ─┐      │
        │  :8080 static     │                      │  :8080 static     │
        └───────────┼──────┘                       └───────────┼──────┘
                    ▼ 127.0.0.1:8090                           ▼ 127.0.0.1:8090
        ┌──────────────────────────┐               ┌──────────────────────────┐
        │ docker: web, api, worker,│               │ docker: web, api, worker,│
        │ inference                │               │ inference                │
        │ + postgis, redis, minio  │◀──private────▶│ (stateless only)         │
        └──────────────────────────┘   network     └──────────────────────────┘
              data tier (shared)
```

`web-01` carries the data tier. `web-02` is stateless and points at it — so both
replicas read and write the *same* database. The API is stateless (JWT, no
sticky sessions), so round-robin is safe.

## Port map on the app servers

| Port | Owner | Status |
|---|---|---|
| 80 | nginx — `rwanda-risk-alert` (catch-all) + new `samba` vhost (named) | shared by hostname, existing behaviour preserved |
| 8000 | the `rwanda-risk-alert` upstream | **untouched** — SAMBA's API publishes no host port |
| 8080 | nginx — pre-existing static site | **untouched** |
| 8090 | SAMBA dashboard container | new, `127.0.0.1` only |
| 5432 / 6379 / 9000 | PostGIS / Redis / MinIO | **web-01 only**, private IP only |

The three collisions with the stock `docker-compose.yml` (`8000`, `8080`, and
the `:80` catch-all) are all resolved by the overlays and the named vhost.
Nothing in `/etc/nginx/nginx.conf`, `sites-enabled/default`, or
`sites-enabled/rwanda-risk-alert` is edited.

---

## 0. Before you start

On **both** app servers, confirm the ports SAMBA wants are actually free:

```bash
sudo ss -ltnp | grep -E ':(8090|5432|6379|9000|9001)\b' || echo "all free"
```

Firewall / security groups:

- `lb-01` → `web-01:80`, `web-02:80`
- `web-02` → `web-01:5432`, `web-01:6379`, `web-01:9000` (private network only)
- Nothing else reaches 5432 / 6379 / 9000 — Redis has no authentication.

Point `samba.<domain>` at `lb-01`'s public IP.

---

## 1. web-01 — data tier + app

```bash
git clone <repo> /opt/samba && cd /opt/samba
cp .env.example .env
```

Edit `.env`:

```bash
POSTGRES_PASSWORD=<strong value>
MINIO_ROOT_PASSWORD=<strong value>
JWT_SECRET=<paste output of the command below>
DATABASE_URL=postgresql+psycopg://samba:<strong value>@postgis:5432/samba
DATA_BIND_IP=<web-01 private IP>
SAMBA_WEB_PORT=8090
```

Generate the JWT secret — do not ship the `.env.example` default:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Bring it up (this server runs migrations):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.data.yml up -d --build
```

Verify locally before moving on:

```bash
curl -s localhost:8090/healthz
```

---

## 2. web-02 — app only

Same clone and `.env`, but pointed at web-01 and with no local data tier:

```bash
DATABASE_URL=postgresql+psycopg://samba:<strong value>@<web-01 private IP>:5432/samba
REDIS_URL=redis://<web-01 private IP>:6379/0
MINIO_ENDPOINT=<web-01 private IP>:9000
SAMBA_WEB_PORT=8090
```

`JWT_SECRET`, `POSTGRES_*` and `MINIO_ROOT_*` must be **identical** to web-01 —
a different `JWT_SECRET` means tokens issued by one replica are rejected by the
other, which looks like random logouts.

Start it only after web-01 is healthy, so migrations have already been applied:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.apponly.yml up -d --build
curl -s localhost:8090/healthz
```

---

## 3. nginx vhost — both app servers

```bash
sudo cp /opt/samba/infra/nginx/samba.conf /etc/nginx/sites-available/samba
sudo sed -i 's/samba\.example\.com/samba.<domain>/' /etc/nginx/sites-available/samba
sudo ln -s /etc/nginx/sites-available/samba /etc/nginx/sites-enabled/samba
sudo nginx -t && sudo systemctl reload nginx
```

`nginx -t` before reload is the safety net for the other two sites. Reload (not
restart) keeps existing connections alive.

Confirm the pre-existing apps still behave exactly as before:

```bash
curl -sI localhost:8080/ | head -1                      # static site
curl -sI -H 'Host: anything-else' localhost/ | head -1   # still rwanda-risk-alert
curl -sI -H 'Host: samba.<domain>' localhost/ | head -1   # now SAMBA
```

---

## 4. HAProxy — lb-01

Back up first, since this is the one file on lb-01 being edited:

```bash
sudo cp /etc/haproxy/haproxy.cfg /etc/haproxy/haproxy.cfg.bak
```

Apply both parts of `infra/haproxy/samba.cfg` — two lines added to the existing
`*:80` frontend, and one new `backend samba-backend` block. Leave the existing
`default_backend` alone; that is what keeps the current app's traffic on its
current path.

```bash
sudo haproxy -c -f /etc/haproxy/haproxy.cfg && sudo systemctl reload haproxy
```

---

## 5. Verify

Round-robin across both servers — `X-Served-By` should alternate:

```bash
for i in $(seq 1 6); do curl -sI http://samba.<domain>/ | grep -i x-served-by; done
```

Same through to the API — `instance` is the API container's hostname:

```bash
for i in $(seq 1 6); do curl -s http://samba.<domain>/healthz | jq -r .instance; done
```

Shared database — a user registered through one replica must log in through the
other. Then confirm failover: stop docker on web-02, check HAProxy marks it DOWN
and the site stays up.

The existing app must still answer on its own hostname throughout.

---

## Rollback

```bash
# lb-01
sudo cp /etc/haproxy/haproxy.cfg.bak /etc/haproxy/haproxy.cfg && sudo systemctl reload haproxy
# both app servers
sudo rm /etc/nginx/sites-enabled/samba && sudo nginx -t && sudo systemctl reload nginx
cd /opt/samba && docker compose -f docker-compose.yml -f docker-compose.prod.yml down
```

Nothing above modifies the pre-existing configs, so rollback is purely removal.

---

## Known gaps

- **No TLS.** Traffic is plain HTTP end to end. Terminate certs at HAProxy
  (Let's Encrypt) before this is genuinely public.
- **web-01 is a single point of failure for data.** Losing it takes the whole
  app down, not just one replica. `DEPLOYMENT.md` §1 has the managed-service
  mapping (RDS / ElastiCache / S3) that removes this.
- **No backups configured** for the `pgdata` volume.
- **CORS is still `*`** (`api/app/main.py`) — worth pinning to the SAMBA origin.
- After a training run, `POST /reload` must be sent to **both** inference
  containers; each has its own local `modelstore` volume.
