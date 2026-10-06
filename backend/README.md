# SmartCrop API

Django REST API for maize yield estimates in Macheke, Mashonaland East. A prediction loads `ml_models/smartcrop_model.joblib`. It does not train a model.

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

SQLite is the local default so the API runs without PostgreSQL. Set `DATABASE_URL=postgres://user:password@localhost:5432/smartcrop` to use PostgreSQL. Docker Compose does that.

`seed_demo` creates `admin`, `researcher`, `analyst`, and `farmer`. The password is `SMARTCROP_DEMO_PASSWORD` or `password` when that variable is unset. Change it before any shared deployment.

## API

- Docs: http://127.0.0.1:8000/api/docs/
- ReDoc: http://127.0.0.1:8000/api/redoc/
- Schema: http://127.0.0.1:8000/api/schema/
- Admin: http://127.0.0.1:8000/admin/

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/token/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"farmer","password":"password"}'
```

Use the access token as `Authorization: Bearer …` on `/api/v1/predictions/`.

## Tests

```bash
pytest
```
