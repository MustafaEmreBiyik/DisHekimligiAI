#!/bin/bash
set -e

echo "DentAI Backend Startup"
echo "====================="

# Add /app to PYTHONPATH so Python can find the app module
export PYTHONPATH="/app:$PYTHONPATH"

# Determine if development mode based on environment variable
DEV_MODE=${DEVELOPMENT_MODE:-false}
WORKERS=${WORKERS:-4}

# Keep Docker/runtime DATABASE_URL and backend DENTAI_DATABASE_URL in sync.
if [ -z "$DATABASE_URL" ] && [ -n "$DENTAI_DATABASE_URL" ]; then
    DATABASE_URL="$DENTAI_DATABASE_URL"
fi
if [ -z "$DENTAI_DATABASE_URL" ] && [ -n "$DATABASE_URL" ]; then
    DENTAI_DATABASE_URL="$DATABASE_URL"
fi
if [ -z "$DATABASE_URL" ] && [ -z "$DENTAI_DATABASE_URL" ]; then
    DATABASE_URL="sqlite:///db/runtime/dentai_app.db"
    DENTAI_DATABASE_URL="$DATABASE_URL"
fi

export DATABASE_URL
export DENTAI_DATABASE_URL

redact_database_url() {
    python - "$1" <<'PY'
from urllib.parse import urlsplit, urlunsplit
import sys

url = sys.argv[1]
parts = urlsplit(url)
if parts.password is None:
    print(url)
    raise SystemExit(0)

username = parts.username or ""
host = parts.hostname or ""
port = f":{parts.port}" if parts.port else ""
userinfo = f"{username}:***" if username else "***"
netloc = f"{userinfo}@{host}{port}"
print(urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment)))
PY
}

database_host() {
    python - "$1" <<'PY'
from urllib.parse import urlsplit
import sys

print(urlsplit(sys.argv[1]).hostname or "")
PY
}

database_port() {
    python - "$1" <<'PY'
from urllib.parse import urlsplit
import sys

print(urlsplit(sys.argv[1]).port or 5432)
PY
}

echo "Database URL: $(redact_database_url "$DATABASE_URL")"
echo "Development Mode: $DEV_MODE"

# Function to wait for database
wait_for_db() {
    echo "Waiting for database to be ready..."
    
    if [[ "$DATABASE_URL" == postgresql* ]]; then
        DB_HOST=$(database_host "$DATABASE_URL")
        DB_PORT=$(database_port "$DATABASE_URL")

        case "$DB_HOST" in
            postgres|localhost|127.0.0.1)
                SHOULD_WAIT_FOR_TCP=1
                ;;
            *)
                SHOULD_WAIT_FOR_TCP=0
                ;;
        esac

        if [ "$SHOULD_WAIT_FOR_TCP" != "1" ]; then
            echo "Remote PostgreSQL host detected ($DB_HOST). Skipping raw TCP wait."
            return 0
        fi

        echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
        
        for i in {1..30}; do
            if nc -z "$DB_HOST" "$DB_PORT" 2>/dev/null; then
                echo "PostgreSQL is up!"
                return 0
            fi
            echo "PostgreSQL unavailable, attempt $i/30. Waiting..."
            sleep 2
        done
        
        echo "Warning: Could not verify PostgreSQL connection, proceeding anyway..."
    else
        echo "Using SQLite - no wait needed"
    fi
}

# Wait for database
wait_for_db

# Run Alembic migrations
echo "Running database migrations..."
alembic upgrade head

# Validate runtime schema after migrations
echo "Validating database schema..."
python scripts/init_db.py

echo "Starting FastAPI application..."
echo "==============================="

# Start uvicorn with or without reload based on DEV_MODE
if [ "$DEV_MODE" = "true" ] || [ "$DEV_MODE" = "1" ]; then
    echo "Starting in development mode with auto-reload..."
    exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
else
    echo "Starting in production mode with $WORKERS workers..."
    exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --workers "$WORKERS"
fi
