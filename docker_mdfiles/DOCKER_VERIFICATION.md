# Docker Setup Verification Checklist

Use this checklist to verify that all Docker components are properly set up and working.

## File Structure Verification

### Core Docker Files

- [ ] `Dockerfile.backend` exists in project root
- [ ] `Dockerfile.frontend` exists in project root
- [ ] `docker-compose.yml` exists in project root
- [ ] `docker-compose.override.yml` exists in project root
- [ ] `docker-compose.prod.yml` exists in project root

### Configuration Files

- [ ] `.dockerignore` exists in project root
- [ ] `.env.example` exists in project root
- [ ] `.env` created (copy from `.env.example`)

### Backend Files

- [ ] `backend/entrypoint.sh` exists
- [ ] `backend/entrypoint.sh` is executable (or will be when mounted in container)

### Nginx Configuration

- [ ] `nginx/nginx.conf` exists

### Documentation

- [ ] `mdfiles/DOCKER_SETUP.md` exists
- [ ] `DOCKER_QUICKSTART.md` exists in project root
- [ ] `DOCKER_IMPLEMENTATION.md` exists in project root

### CI/CD

- [ ] `.github/workflows/docker-build.yml` exists

### Command Helpers

- [ ] `Makefile` exists in project root
- [ ] `docker-commands.bat` exists in project root
- [ ] `docker-commands.ps1` exists in project root

## Pre-Startup Checks

### Environment Setup

- [ ] `.env` file created from `.env.example`
- [ ] `DENTAI_SECRET_KEY` updated in `.env` (not default value)
- [ ] Database path exists or will be created: `db/runtime/`
- [ ] All required directories exist:
  - [ ] `app/`
  - [ ] `db/`
  - [ ] `alembic/`
  - [ ] `scripts/`
  - [ ] `frontend/`

### Docker Installation

- [ ] Docker is installed (`docker --version` returns version)
- [ ] Docker Compose is installed (`docker-compose --version` returns version)
- [ ] Docker daemon is running
  - [ ] On Windows: Docker Desktop is running
  - [ ] On Mac: Docker Desktop is running
  - [ ] On Linux: Docker service is running (`sudo systemctl status docker`)

### Port Availability

- [ ] Port 3000 is available (frontend)
- [ ] Port 8000 is available (backend)
- [ ] Port 5432 is available (PostgreSQL, if using)
- [ ] Port 8080 is available (Adminer, if using)

## Development Mode Startup

### Start Services

```bash
# Windows
docker-commands.ps1 dev
# or
make dev

# Linux/Mac
make dev

# Direct
docker-compose --profile dev up -d
```

- [ ] Command executes without errors
- [ ] Three containers start:
  - [ ] `dentai-backend` (FastAPI)
  - [ ] `dentai-frontend` (Next.js)
  - [ ] Database volume created: `dentai_db_volume`

### Verify Services Running

```bash
docker-compose ps
```

- [ ] All containers show status "Up"
- [ ] Backend container has port `8000:8000` mapping
- [ ] Frontend container has port `3000:3000` mapping

### Check Container Health

```bash
docker-compose ps
```

- [ ] Backend health status: healthy or no health check indicated
- [ ] Frontend health status: healthy or no health check indicated

### Verify Services Operational

#### Backend API

```bash
curl http://localhost:8000/docs
```

- [ ] Returns HTTP 200
- [ ] Swagger UI loads in browser

```bash
curl http://localhost:8000/redoc
```

- [ ] Returns HTTP 200
- [ ] ReDoc documentation loads

#### Frontend

```bash
curl http://localhost:3000
```

- [ ] Returns HTTP 200
- [ ] HTML content received

Open browser to `http://localhost:3000`

- [ ] Frontend application loads
- [ ] No console errors about backend connectivity

### Database Operations

#### Check Database Initialization

```bash
docker-compose exec backend python scripts/init_db.py
```

- [ ] Command completes without major errors
- [ ] Database file created at `db/runtime/dentai_app.db` (check from host)

#### Verify Migrations

```bash
docker-compose exec backend alembic current
```

- [ ] Shows current migration status
- [ ] No migration errors in previous logs

#### Test Database Connection from Backend

```bash
docker-compose exec backend python -c "from db.database import SessionLocal; s = SessionLocal(); print('DB Connected')"
```

- [ ] Prints "DB Connected"
- [ ] No connection errors

### Backend Shell Access

```bash
docker-compose exec backend bash
```

- [ ] Bash shell prompt appears
- [ ] Can run commands inside container
- [ ] Type `exit` to return

### Frontend Shell Access

```bash
docker-compose exec frontend sh
```

- [ ] Shell prompt appears
- [ ] Can run npm commands
- [ ] Type `exit` to return

### Hot Reload Testing (Development)

1. Edit `app/api/main.py` or any Python file in `app/`
2. Save file
3. Check backend logs: `docker-compose logs -f backend`
   - [ ] Should see file change detected
   - [ ] Auto-reload triggered
   - [ ] No errors in reload

4. Edit `frontend/app/page.tsx` or any React component
5. Save file
6. Check frontend logs: `docker-compose logs -f frontend`
   - [ ] Should see file change detected
   - [ ] HMR (Hot Module Reload) triggered
   - [ ] Changes visible in browser without refresh

### Logging Verification

```bash
docker-compose logs -f
```

- [ ] Logs stream without errors
- [ ] Both backend and frontend logs visible

```bash
docker-compose logs backend
```

- [ ] Backend logs retrievable

```bash
docker-compose logs frontend
```

- [ ] Frontend logs retrievable

## Production Mode Startup

### Prepare Production Environment

1. Copy `.env.example` to `.env.prod` (optional)
2. Update all values in `.env`:
   - [ ] `DENTAI_SECRET_KEY` - strong unique value
   - [ ] `DEVELOPMENT_MODE=false`
   - [ ] `DATABASE_URL=postgresql://...` - PostgreSQL connection
   - [ ] `POSTGRES_USER` - strong password
   - [ ] `POSTGRES_PASSWORD` - strong password

### Start Production Services

```bash
docker-compose --profile prod --profile postgres up -d
```

- [ ] Command executes without errors
- [ ] 5 containers start:
  - [ ] `dentai-backend` (FastAPI)
  - [ ] `dentai-frontend` (Next.js)
  - [ ] `dentai-postgres` (PostgreSQL)
  - [ ] `dentai-adminer` (Database UI)
  - [ ] Plus volumes

### Verify Production Services

```bash
docker-compose ps
```

- [ ] All containers "Up"
- [ ] PostgreSQL container healthy
- [ ] No volumes mounted for code (production optimization)

#### Test Backend Production API

```bash
curl http://localhost:8000/docs
```

- [ ] Returns HTTP 200
- [ ] Swagger UI accessible

#### Test Frontend Production Build

```bash
curl http://localhost:3000
```

- [ ] Returns HTTP 200
- [ ] Optimized production build served

#### Verify Database

```bash
docker-compose exec postgres psql -U dentai -d dentai_db -c "SELECT 1;"
```

- [ ] Returns "1" from PostgreSQL
- [ ] Database connection working

### Adminer Access (Optional)

Open `http://localhost:8080`

- [ ] Adminer interface loads
- [ ] Can log in with PostgreSQL credentials
- [ ] Can view database tables

## Docker Image Verification

### Check Built Images

```bash
docker images | grep dentai
```

- [ ] `dentai-backend` image exists
- [ ] `dentai-frontend` image exists
- [ ] Image sizes reasonable:
  - [ ] Backend: ~500-600MB
  - [ ] Frontend: ~200-300MB

### Inspect Images

```bash
docker inspect dentai-backend
```

- [ ] Shows image configuration
- [ ] Exposed ports: 8000
- [ ] Environment variables listed

```bash
docker inspect dentai-frontend
```

- [ ] Shows image configuration
- [ ] Exposed ports: 3000
- [ ] Environment variables listed

## Cleanup and Reset Testing

### Test Graceful Shutdown

```bash
docker-compose down
```

- [ ] All containers stop
- [ ] No error messages
- [ ] Network removed

### Test Full Cleanup

```bash
docker-compose down -v
```

- [ ] Containers stopped
- [ ] Volumes removed
- [ ] No orphaned containers

### Test Restart

```bash
docker-compose --profile dev up -d
```

- [ ] Containers start fresh
- [ ] All services operational
- [ ] Database reinitializes if needed

## Cross-Platform Verification

### Windows

- [ ] Docker Desktop running
- [ ] PowerShell command works:
  ```powershell
  .\docker-commands.ps1 dev
  ```
- [ ] Batch command works:
  ```cmd
  docker-commands.bat dev
  ```
- [ ] Volumes mount correctly for hot reload

### Mac/Linux

- [ ] Docker daemon running
- [ ] Make command works:
  ```bash
  make dev
  ```
- [ ] Bash script executable and runs
- [ ] File permissions preserved in containers

## Documentation Review

- [ ] `DOCKER_QUICKSTART.md` is accurate for your setup
- [ ] `mdfiles/DOCKER_SETUP.md` has all needed information
- [ ] `DOCKER_IMPLEMENTATION.md` documents all created files
- [ ] Troubleshooting section matches any issues encountered

## Performance Check

### Backend Startup Time

- [ ] Measured: ~10-20 seconds from `docker-compose up` to healthy
- [ ] DB initialization included in time
- [ ] Alembic migrations completed

### Frontend Build Time

- [ ] First build: ~2-3 minutes
- [ ] Subsequent builds (with cache): ~1-2 minutes
- [ ] Reasonable for CI/CD pipeline

### Runtime Performance

- [ ] API requests responsive (<500ms)
- [ ] Frontend loads quickly
- [ ] No container resource warnings

## Security Verification

- [ ] `.env` not committed to Git (check `.gitignore`)
- [ ] `.env.example` IS committed with safe defaults
- [ ] Secrets not in Docker images
- [ ] Database password changed from defaults
- [ ] PostgreSQL port not exposed externally
- [ ] API keys not logged in container output

## Optional Features Testing

### PostgreSQL for Development

```bash
docker-compose --profile postgres-dev up -d
```

- [ ] PostgreSQL starts alongside SQLite
- [ ] Can switch DATABASE_URL to use PostgreSQL
- [ ] Adminer accessible at port 8080

### Nginx Reverse Proxy

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile prod-nginx up -d
```

- [ ] Nginx container starts on port 80
- [ ] Frontend accessible at http://localhost
- [ ] API accessible at http://localhost/api/
- [ ] Documentation at http://localhost/docs

### GitHub Actions (CI/CD)

- [ ] `.github/workflows/docker-build.yml` exists
- [ ] Workflow triggers on git push (manually verify)
- [ ] Images build in GitHub Actions
- [ ] (Optional) Images pushed to registry

## Final Sign-Off

- [ ] All file structure verified
- [ ] Development mode operational
- [ ] Production mode tested
- [ ] Hot reload working
- [ ] Database migrations functioning
- [ ] Documentation complete
- [ ] Cross-platform compatibility confirmed
- [ ] Security best practices followed
- [ ] Performance acceptable
- [ ] Ready for team deployment

---

## Troubleshooting Quick Links

If any check fails, see:

- **Container won't start**: See `mdfiles/DOCKER_SETUP.md` → "Troubleshooting" → "Backend Container Won't Start"
- **Port already in use**: See `mdfiles/DOCKER_SETUP.md` → "Troubleshooting" → "Port Already in Use"
- **Database issues**: See `mdfiles/DOCKER_SETUP.md` → "Database Management"
- **Frontend can't reach backend**: See `mdfiles/DOCKER_SETUP.md` → "Troubleshooting" → "Frontend Can't Connect to Backend"
- **Hot reload not working**: See `mdfiles/DOCKER_SETUP.md` → "Troubleshooting" → "Hot Reload Not Working"

---

**Verification Date**: ******\_\_\_******
**Verified By**: ******\_\_\_******
**Status**: ✅ Pass / ❌ Fail

**Notes**: ******************************\_\_\_\_******************************
