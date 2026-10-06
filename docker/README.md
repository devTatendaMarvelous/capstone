# Docker

`docker-compose.yml` at the repository root starts three services:

| Service | Image | Port | Role |
| --- | --- | --- | --- |
| `db` | `postgres:16` | 5432 | Application database |
| `backend` | `backend/Dockerfile` | 8000 | Migrate, `seed_demo`, then gunicorn |
| `frontend` | `frontend/Dockerfile` | 8080 | Built React app behind nginx |

Nginx proxies `/api/` and `/admin/` to the backend. The saved model directory `backend/ml_models` and the clean CSV `data-science/data/processed` are mounted read-only. The API loads that joblib file. It does not train during startup or during a prediction.

From the repository root:

```bash
docker compose up --build
```

Then open http://localhost:8080. API docs are at http://localhost:8000/api/docs/.

The Compose database password is `smartcrop` and the demo user password is `password`. Both are local development defaults. Replace them before any shared deployment, and replace `DJANGO_SECRET_KEY`.

SQLite remains available when you run Django on the host without `DATABASE_URL`. Compose always sets a Postgres URL.
