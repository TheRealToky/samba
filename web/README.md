# Web frontend

React + TypeScript + Vite. Serves both the public marketing site and the
authenticated dashboard from the same bundle (nginx SPA fallback in prod, vite
dev server on :5173 with `/api` proxied to the backend on :8000).

## Routes

| Path | Access | Page |
| --- | --- | --- |
| `/` | public | `pages/Landing.tsx` — marketing site, reads the public read-only endpoints |
| `/login` | public | `pages/Login.tsx` |
| `/dashboard` | protected | Overview |
| `/biodiversity`, `/climate`, `/map`, `/alerts`, `/reports` | protected | app pages |

## Regenerating the landing-page map

`src/lib/madagascar.ts` is generated: simplified region polygons from PostGIS,
projected equirectangular and fitted to an SVG viewBox, so the hero map renders
without shipping the 700 KB `/regions/geojson` payload. Regenerate it when the
region set changes:

```bash
docker compose exec -T postgis psql -U samba -d samba -At -c "SELECT json_agg(r)::text FROM (SELECT code, name, biome, round(ST_X(ST_PointOnSurface(geom))::numeric,3) AS cx, round(ST_Y(ST_PointOnSurface(geom))::numeric,3) AS cy, ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom, 0.035), 3) AS g FROM regions ORDER BY name) r;" > regions.json && python web/scripts/build_map.py regions.json web/src/lib/madagascar.ts
```

## Notes

- The whole UI is styled by `src/styles.css` (app shell + design tokens) plus
  `src/landing.css` (public site only, everything namespaced under `.lp-`).
- Icons are inline SVG in `src/components/icons.tsx` — no icon package.
- After changing `src/`, rebuild the container to see it on :8080:
  `docker compose build web && docker compose up -d web`.
