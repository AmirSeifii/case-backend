## Case Backend (Django REST API)

### Prerequisites
- Python 3.10+
- pip

### Setup
```bash
cd case-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create and migrate the database
python manage.py migrate

# (Optional) Seed demo data
python manage.py loaddata || true
python manage.py runserver  # will create db.sqlite3 if missing
python manage.py seed_data  # creates restaurants, customers, orders, items
```

Notes
- The DB path can be overridden with `DJANGO_DB_PATH` env var.
- CORS is enabled for `http://localhost:3000` by default.

### Running
```bash
python manage.py runserver 0.0.0.0:8000
```
API root at `http://localhost:8000/api/`.

### Useful endpoints
- Orders list: `GET /api/orders/`
- Pending: `GET /api/orders/pending/?restaurant_id=1`
- Active: `GET /api/orders/active/?restaurant_id=1`
- Order details: `GET /api/orders/{id}/`
- Accept: `POST /api/orders/{id}/accept_preparation/`
- Reject: `POST /api/orders/{id}/reject_preparation/` with `{ "reason": "..." }`
- Delay: `POST /api/orders/{id}/mark_delayed/` with `{ "delay_minutes": 10, "reason": "..." }`
- Cancel: `POST /api/orders/{id}/mark_cancelled/` with `{ "reason": "..." }`
- Done: `POST /api/orders/{id}/mark_done/`
- Delivered: `POST /api/orders/{id}/mark_delivered/`
- Kyte webhook: `POST /api/kyte/events/`
- Simulate create: `POST /api/orders/simulate_create/` with `{ "restaurant_id": 1 }`
- Simulate cancel: `POST /api/orders/simulate_cancel/` with `{ "restaurant_id": 1 }`
- Generate random orders: `POST /api/orders/simulate/` with `{ "count": 5 }`

For the full API details, see `API_GUIDE.md`.

### Environment
Create a `.env` if needed and export variables before running:
```bash
export DJANGO_DB_PATH="$(pwd)/db.sqlite3"
```

### Production (gunicorn)
```bash
gunicorn backend.wsgi:application --bind 0.0.0.0:8000 --workers 2
```


