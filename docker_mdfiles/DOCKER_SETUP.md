# DentAI Docker Setup Guide

Complete Docker and Docker Compose configuration for the DentAI full-stack application. This guide covers development and production setups.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Environment Setup](#environment-setup)
5. [Development Mode](#development-mode)
6. [Production Mode](#production-mode)
7. [Database Management](#database-management)
8. [Troubleshooting](#troubleshooting)
9. [Advanced Configuration](#advanced-configuration)

---

## Quick Start

### Development (SQLite + Hot Reload)

```bash
# 1. Create environment file
make env-setup

# 2. Start development environment
make dev

# 3. Access services
# Frontend: http://localhost:3000
# Backend API docs: http://localhost:8000/docs
# Backend ReDoc: http://localhost:8000/redoc

# 4. View logs
make dev-logs

# 5. Stop services
make dev-stop
```

### Production (PostgreSQL)

```bash
# 1. Create and configure .env
make env-setup
# Edit .env with production values

# 2. Start production environment
make prod

# 3. Access services
# Frontend: http://localhost:3000
# Backend API docs: http://localhost:8000/docs

# 4. Stop services
make prod-stop
```

---

## Architecture

### Services

```
┌─────────────────────────────────────────┐
│         dentai-network (bridge)         │
│                                         │
│  ┌──────────────┐  ┌──────────────┐  │
│  │   Frontend   │  │   Backend    │  │
│  │ (Next.js)    │→ │ (FastAPI)    │  │
│  │  :3000       │  │  :8000       │  │
│  └──────────────┘  └──────────────┘  │
│                          ↓            │
│                    ┌──────────────┐   │
│                    │  PostgreSQL  │   │
│                    │  :5432       │   │
│                    └──────────────┘   │
│                                       │
└─────────────────────────────────────────┘
```

### Components

- **Frontend (Next.js 16)**
  - React 19 UI application
  - Port: 3000
  - Communicates with backend via `NEXT_PUBLIC_API_URL`
  - Built with Tailwind CSS and TypeScript

- **Backend (FastAPI)**
  - Python 3.11 REST API
  - Port: 8000
  - Uvicorn ASGI server
  - SQLAlchemy ORM with Alembic migrations
  - CORS configured for frontend

- **Database (PostgreSQL - optional)**
  - PostgreSQL 15 Alpine
  - Port: 5432 (internal, not exposed by default)
  - SQLite for development (file-based)
  - Adminer for database management (optional)

---

## Prerequisites

### Required

- Docker 20.10+
- Docker Compose 2.0+

### Optional

- Make (for convenient commands)
- Git
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend development)

### Installation

**Windows (using Chocolatey):**

```powershell
choco install docker-desktop make
```

**macOS:**

```bash
brew install docker docker-compose make
```

**Linux (Ubuntu/Debian):**

```bash
sudo apt-get install docker.io docker-compose make
# Add user to docker group:
sudo usermod -aG docker $USER
```

---

## Environment Setup

### 1. Create .env File

```bash
# Create .env from template
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` with your settings:

```env
# Backend
DENTAI_SECRET_KEY=your-secret-key-here
DENTAI_ACCESS_TOKEN_EXPIRE_MINUTES=1440
GEMINI_API_KEY=your-gemini-api-key
HUGGINGFACE_API_KEY=your-huggingface-api-key

# Frontend
NEXT_PUBLIC_API_URL=http://backend:8000

# Database
DATABASE_URL=sqlite:///db/runtime/dentai_app.db

# Development
DEVELOPMENT_MODE=false
```

### 3. Required Secret Keys

Generate a secure JWT secret:

**macOS/Linux:**

```bash
openssl rand -hex 32
```

**Windows PowerShell:**

```powershell
[System.Convert]::ToHexString([System.Security.Cryptography.RNGCryptoServiceProvider]::new().GetBytes(32))
```

Update `DENTAI_SECRET_KEY` in `.env` with the generated value.

---

## Development Mode

### Start Development Environment

```bash
make dev
```

Or without Make:

```bash
docker-compose --profile dev up -d
```

### Services Started

- **Backend**: http://localhost:8000 (hot reload enabled)
- **Frontend**: http://localhost:3000 (HMR enabled)
- **Database**: SQLite at `db/runtime/dentai_app.db`

### Features

✅ Hot reload on code changes
✅ Live editing of app/, db/, alembic/, scripts/ folders
✅ Full debugging capability
✅ Direct access to logs

### View Development Logs

```bash
# All services
make dev-logs

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Access Backend Container

```bash
make shell-backend
# Or: docker-compose exec backend /bin/bash

# Useful commands:
python scripts/init_db.py          # Initialize database
alembic current                     # Check current migration
alembic upgrade head                # Apply pending migrations
```

### Database Management (Development)

SQLite database is stored at `db/runtime/dentai_app.db` and persists in the `dentai_db_volume`.

To reset database:

```bash
docker-compose down -v
docker-compose --profile dev up -d
```

---

## Production Mode

### Start Production Environment

```bash
# Update .env with production values first!
make prod
```

Or without Make:

```bash
docker-compose --profile prod --profile postgres up -d
```

### Production .env Configuration

```env
# CRITICAL: Change these for production!
DENTAI_SECRET_KEY=<generate-secure-key>
DENTAI_ACCESS_TOKEN_EXPIRE_MINUTES=60

# Database (use PostgreSQL)
DATABASE_URL=postgresql://dentai:password@postgres:5432/dentai_db
POSTGRES_USER=dentai
POSTGRES_PASSWORD=<secure-password>
POSTGRES_DB=dentai_db

# API Keys (from production environment)
GEMINI_API_KEY=<production-key>
HUGGINGFACE_API_KEY=<production-key>

# Frontend
NEXT_PUBLIC_API_URL=https://yourdomain.com/api

# Disable development mode
DEVELOPMENT_MODE=false

# Enable PostgreSQL
COMPOSE_PROFILES=postgres,prod
```

### Services Started

- **Backend**: http://localhost:8000 (4 workers, no reload)
- **Frontend**: http://localhost:3000 (optimized build)
- **PostgreSQL**: Internal service (not exposed)

### Production Features

✅ Multi-worker Uvicorn for better concurrency
✅ Optimized Next.js build
✅ PostgreSQL for data persistence
✅ Health checks for all services
✅ Automatic database migrations

### Monitor Production Services

```bash
# View running containers
make status

# View logs
make prod-logs

# View specific service logs
docker-compose logs -f backend
```

---

## Database Management

### Development (SQLite)

Database file: `db/runtime/dentai_app.db`

```bash
# Reset database
rm db/runtime/dentai_app.db
docker-compose restart backend

# Access from backend container
sqlite3 db/runtime/dentai_app.db
```

### Production (PostgreSQL)

#### Using Adminer (Web UI)

```bash
# Start Adminer container
docker-compose up -d adminer

# Access at http://localhost:8080
# Server: postgres (or service name)
# Username: dentai (from POSTGRES_USER)
# Password: (from POSTGRES_PASSWORD)
# Database: dentai_db (from POSTGRES_DB)
```

#### Using psql CLI

```bash
# Connect to PostgreSQL container
docker-compose exec postgres psql -U dentai -d dentai_db

# Useful commands:
\dt                    # List tables
\d table_name          # Describe table
SELECT * FROM table;   # Query data
\q                     # Quit
```

### Database Migrations

Alembic migrations run automatically on backend startup. To manually manage migrations:

```bash
# Check current migration
docker-compose exec backend alembic current

# View migration history
docker-compose exec backend alembic history

# Upgrade to specific migration
docker-compose exec backend alembic upgrade <revision>

# Downgrade migration
docker-compose exec backend alembic downgrade -1
```

### Backup PostgreSQL

```bash
# Create backup
docker-compose exec postgres pg_dump -U dentai dentai_db > backup.sql

# Restore from backup
docker-compose exec -T postgres psql -U dentai dentai_db < backup.sql
```

---

## Troubleshooting

### Backend Container Won't Start

**Check logs:**

```bash
docker-compose logs backend
```

**Common issues:**

1. **Port 8000 already in use**

   ```bash
   # Check what's using port 8000
   lsof -i :8000  # macOS/Linux
   netstat -ano | findstr :8000  # Windows

   # Change port in docker-compose.yml
   ports:
     - "8001:8000"  # Map to different port
   ```

2. **Database initialization fails**

   ```bash
   # Manually initialize
   docker-compose exec backend python scripts/init_db.py
   docker-compose restart backend
   ```

3. **Permission denied on entrypoint.sh**
   ```bash
   # On Windows, this is usually not an issue
   # On Mac/Linux, ensure execute permission:
   chmod +x backend/entrypoint.sh
   docker-compose rebuild backend
   ```

### Frontend Can't Connect to Backend

**Verify backend is running:**

```bash
curl http://localhost:8000/docs
```

**Check frontend logs:**

```bash
docker-compose logs frontend
```

**Update NEXT_PUBLIC_API_URL:**

- For local development: `http://backend:8000`
- For external access: `http://localhost:8000`

### PostgreSQL Connection Issues

**Verify PostgreSQL is running:**

```bash
docker-compose --profile postgres ps
```

**Check PostgreSQL logs:**

```bash
docker-compose --profile postgres logs postgres
```

**Verify environment variables:**

```bash
docker-compose exec postgres printenv | grep POSTGRES
```

### Database Migrations Fail

**Check migration status:**

```bash
docker-compose exec backend alembic current
docker-compose exec backend alembic history
```

**Manually reset migrations (development only):**

```bash
docker-compose exec backend alembic downgrade base
docker-compose exec backend alembic upgrade head
```

### Hot Reload Not Working (Development)

**Verify docker-compose.override.yml exists:**

```bash
ls -la docker-compose.override.yml
```

**Ensure volumes are mounted:**

```bash
docker-compose exec backend mount | grep "/app"
```

**Restart with override file:**

```bash
docker-compose down
docker-compose --profile dev up -d
```

### API Documentation Not Loading

**Verify backend health check:**

```bash
curl -v http://localhost:8000/docs
```

**Check CORS configuration:**

```bash
curl -v -H "Origin: http://localhost:3000" http://localhost:8000/docs
```

---

## Advanced Configuration

### Custom Ports

Edit `docker-compose.yml`:

```yaml
services:
  backend:
    ports:
      - "8001:8000" # Map port 8001 to container's 8000

  frontend:
    ports:
      - "3001:3000" # Map port 3001 to container's 3000
```

### Enable PostgreSQL for Development

```bash
# Start with PostgreSQL
docker-compose --profile postgres-dev up -d

# Or update docker-compose.override.yml to always include postgres
```

### Use External PostgreSQL

Update `.env`:

```env
DATABASE_URL=postgresql://user:password@external-host:5432/database
```

Don't start postgres service:

```bash
docker-compose --profile dev up -d
```

### Build Custom Images

```bash
# Build specific image
docker-compose build backend --no-cache
docker-compose build frontend --no-cache

# Build all images
docker-compose build --no-cache
```

### Push Images to Registry

```bash
# Tag images
docker tag dentai-backend your-registry/dentai-backend:latest
docker tag dentai-frontend your-registry/dentai-frontend:latest

# Push to registry
docker push your-registry/dentai-backend:latest
docker push your-registry/dentai-frontend:latest
```

### Health Checks Configuration

Modify in `docker-compose.yml`:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/docs"]
  interval: 30s # Check every 30 seconds
  timeout: 10s # Wait up to 10 seconds
  retries: 3 # Fail after 3 failed checks
  start_period: 40s # Grace period before first check
```

### Resource Limits

Add to `docker-compose.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 2G
        reservations:
          cpus: "1"
          memory: 1G
```

---

## Command Reference

### Using Make

```bash
make help              # Show all commands
make dev              # Start development
make prod             # Start production
make build            # Build all images
make dev-logs         # View development logs
make shell-backend    # Access backend shell
make clean            # Remove all containers/volumes
make env-setup        # Create .env file
```

### Direct Docker Compose Commands

```bash
# Development
docker-compose --profile dev up -d
docker-compose --profile dev logs -f
docker-compose --profile dev down

# Production with PostgreSQL
docker-compose --profile prod --profile postgres up -d
docker-compose --profile prod --profile postgres logs -f

# PostgreSQL only
docker-compose --profile postgres up -d

# All services
docker-compose up -d
docker-compose logs -f
docker-compose down -v
```

### Docker Build Commands

```bash
# Build backend image
docker build -f Dockerfile.backend -t dentai-backend:latest .

# Build frontend image
docker build -f Dockerfile.frontend -t dentai-frontend:latest .

# Build with custom arguments
docker build -f Dockerfile.frontend \
  --build-arg NEXT_PUBLIC_API_URL=https://api.example.com \
  -t dentai-frontend:latest .
```

---

## Performance Tips

### Development

- Use volumes for hot reload instead of copying files
- Disable health checks during debugging
- Use `-d` flag to run containers in background

### Production

- Use multi-stage builds (already configured)
- Set appropriate resource limits
- Use PostgreSQL instead of SQLite
- Use reverse proxy (nginx) for static files
- Enable caching headers for frontend assets

### General

- Use Docker images instead of binding to localhost
- Leverage service health checks
- Monitor resource usage with `docker stats`
- Use `.dockerignore` to reduce build context

---

## Security Considerations

### Secrets Management

**DO NOT:**

- Commit `.env` file with secrets
- Use default passwords in production
- Expose database ports externally
- Run containers as root

**DO:**

- Use `.env.example` template
- Rotate secrets regularly
- Use secrets management service (AWS Secrets Manager, HashiCorp Vault)
- Run containers with minimal privileges
- Use environment variables for sensitive data

### Network Security

```yaml
# Internal only (no external access)
postgres:
  # No ports exposed

# External access
frontend:
  ports:
    - "3000:3000"

backend:
  ports:
    - "8000:8000"
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Push Docker Images

on:
  push:
    branches: [main]
    tags: ["v*"]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build backend
        run: docker build -f Dockerfile.backend -t dentai-backend:${{ github.sha }} .

      - name: Build frontend
        run: docker build -f Dockerfile.frontend -t dentai-frontend:${{ github.sha }} .

      - name: Push to registry
        env:
          REGISTRY: ghcr.io
        run: |
          docker tag dentai-backend:${{ github.sha }} ${{ env.REGISTRY }}/dentai-backend:latest
          docker push ${{ env.REGISTRY }}/dentai-backend:latest
```

---

## Next Steps

1. **Create `.env` file**: `make env-setup`
2. **Start development**: `make dev`
3. **Verify services**: `make health`
4. **View logs**: `make dev-logs`
5. **Deploy**: Follow production setup for your hosting platform

---

## Support

For issues or questions:

1. Check [Troubleshooting](#troubleshooting) section
2. Review container logs: `docker-compose logs -f`
3. Verify `.env` configuration
4. Check Docker and Docker Compose versions

---

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Next.js Docker Guide](https://nextjs.org/docs/deployment/docker)
- [SQLAlchemy Alembic](https://alembic.sqlalchemy.org/)
