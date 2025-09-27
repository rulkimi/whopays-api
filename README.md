## WhoPays API

FastAPI backend for managing users, friends, receipts, items, and AI-assisted parsing using Google Gemini. Persistence is via PostgreSQL, file storage via MinIO, and migrations via Alembic.

### Tech stack
- FastAPI, Pydantic
- SQLAlchemy, Alembic, PostgreSQL
- MinIO (S3-compatible object storage)
- Google Gemini (`google-genai`)
- Uvicorn

### Prerequisites
- Python 3.13
- Docker and Docker Compose (recommended for PostgreSQL and MinIO)
- PowerShell (Windows) or a POSIX shell

### 1) Clone and configure environment
Rename the `.env.example` file to `.env` and fill in the values.

### 2) Start infrastructure (PostgreSQL + MinIO)
Using Docker Compose from the repo root:

```bash
docker compose up -d
```

This brings up:
- PostgreSQL 16 (port `${DB_PORT}:5432`, defaults to 5432)
- MinIO (API on `${MINIO_API_PORT}`, Console on `${MINIO_CONSOLE_PORT}`)

MinIO Console is available at `http://localhost:${MINIO_CONSOLE_PORT}` (default creds: `minioadmin` / `minioadmin`).

### 3) Run the API locally (recommended during development)

PowerShell (Windows):
```powershell
py -3.13 -m venv .venv
./venv/Scripts/Activate.ps1
pip install -r requirements.txt

# Apply database migrations
alembic upgrade head

# Start FastAPI
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Bash (macOS/Linux):
```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

alembic upgrade head

uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open API docs: http://localhost:8000/docs

### 4) Run the API in Docker (optional)
If you prefer to run the application in a container (infra still via Docker Compose):

```bash
docker build -t whopays-api .
docker run --rm \
  --name whopays-api \
  --env-file .env \
  -e PORT=8000 \
  -p 8000:8000 \
  --network host \
  whopays-api
```

Notes
- The image entrypoint runs `alembic upgrade head` and then starts Uvicorn on `${PORT}`.
- On non-Linux hosts without `--network host`, ensure the DB/MinIO are reachable via hostnames/IPs from inside the container (e.g., `host.docker.internal`). Adjust `DB_HOST`/`MINIO_ENDPOINT` accordingly in `.env`.

### Database migrations (Alembic)
The Alembic environment reads `DATABASE_URL` from settings. Common commands:

```bash
# Generate a new revision after model changes
alembic revision -m "describe change" --autogenerate

# Apply latest migrations
alembic upgrade head

# Downgrade one revision
alembic downgrade -1
```

### Configuration reference
The app loads settings from `.env` via `pydantic-settings` (`app/core/config.py`). Key variables:
- `DB_DRIVER`, `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT` → compose the database URL
- `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` → JWT auth
- `GOOGLE_GEMINI_API_KEY` → Gemini client
- `MINIO_ENDPOINT`, `MINIO_PUBLIC_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`, `MINIO_SECURE` → MinIO client
- `MINIO_API_PORT`, `MINIO_CONSOLE_PORT` → local port mappings for Docker Compose
- `PORT` → Uvicorn port used by the Docker image

On startup, the MinIO dependency ensures the bucket exists.

### Project layout (high level)
```
app/
  api/               # Routers and dependencies
  core/              # Settings and security
  db/                # SQLAlchemy models, sessions, Base
  gemini/            # Gemini client, prompts, services
  schemas/           # Pydantic schemas
  services/          # Domain services (files, receipts, friends, etc.)
alembic/             # Migration environment and versions
Dockerfile           # App image (runs migrations + Uvicorn)
docker-compose.yml   # Postgres + MinIO services
requirements.txt     # Python dependencies
main.py              # FastAPI app entry
```

### Useful URLs
- API docs: http://localhost:8000/docs
- MinIO API: http://localhost:9000
- MinIO Console: http://localhost:9001

### Troubleshooting
- Cannot connect to DB: ensure Docker Compose is up and `.env` DB values are correct.
- MinIO errors: verify `MINIO_ENDPOINT` and `MINIO_SECURE` match your setup; ensure bucket name matches `MINIO_BUCKET`.
- Gemini errors: verify `GOOGLE_GEMINI_API_KEY` is valid and present in `.env`.


