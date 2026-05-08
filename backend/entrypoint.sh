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

echo "Database URL: $DATABASE_URL"
echo "Development Mode: $DEV_MODE"

# Function to wait for database
wait_for_db() {
    echo "Waiting for database to be ready..."
    
    if [[ "$DATABASE_URL" == postgresql* ]]; then
        # PostgreSQL connection string parsing
        # Extract host and port from connection string
        # Format: postgresql://user:password@host:port/database
        
        DB_HOST=$(echo "$DATABASE_URL" | sed -n 's|.*@\([^:/]*\).*|\1|p')
        DB_PORT=$(echo "$DATABASE_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
        DB_PORT=${DB_PORT:-5432}
        
        echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
        
        # Wait using nc (netcat) if available, otherwise just sleep
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

# Initialize database if needed
echo "Initializing database schema..."
python scripts/init_db.py || true

# Run Alembic migrations
echo "Running database migrations..."
alembic upgrade head || true

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
