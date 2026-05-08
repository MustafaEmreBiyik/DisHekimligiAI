# Docker Setup for DentAI - Complete Index

This directory now contains complete Docker support for the DentAI full-stack application. Below is a guide to all Docker-related files and how to use them.

## 🚀 Quick Start

**Choose your platform:**

### Windows

```powershell
# PowerShell
.\docker-commands.ps1 dev

# Or Batch
docker-commands.bat dev

# Or if you have Make installed (Git Bash/WSL)
make dev
```

### Linux / macOS

```bash
make dev
```

### Any Platform (Direct Docker Compose)

```bash
docker-compose --profile dev up -d
```

Then open:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs

---

## 📚 Documentation Map

### Start Here

1. **[DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md)** (5 min read)
   - 1-minute setup
   - Basic commands
   - Quick troubleshooting

### Complete Reference

2. **[mdfiles/DOCKER_SETUP.md](mdfiles/DOCKER_SETUP.md)** (30 min read)
   - Comprehensive guide
   - All features explained
   - Detailed troubleshooting (25+ scenarios)
   - Advanced configuration
   - Security & performance tips
   - **USE THIS FOR**: Deep understanding and complex setups

### Implementation Details

3. **[DOCKER_IMPLEMENTATION.md](DOCKER_IMPLEMENTATION.md)** (15 min read)
   - What was created and why
   - File-by-file breakdown
   - Architecture overview
   - Performance benchmarks
   - **USE THIS FOR**: Understanding what's included

### Verification

4. **[DOCKER_VERIFICATION.md](DOCKER_VERIFICATION.md)** (After first run)
   - Checklist to verify everything works
   - Cross-platform checks
   - Performance testing
   - **USE THIS FOR**: Confirming successful setup

---

## 📁 File Structure

```
dentai/
│
├── 🐳 DOCKER CORE FILES
├── Dockerfile.backend              # FastAPI container build
├── Dockerfile.frontend             # Next.js container build
├── docker-compose.yml              # Main orchestration
├── docker-compose.override.yml     # Development overrides
├── docker-compose.prod.yml         # Production with Nginx
├── .dockerignore                   # Build exclusions
│
├── ⚙️ CONFIGURATION
├── .env.example                    # Environment template (COPY THIS)
├── .env                            # Your environment (from .env.example)
│
├── 📋 COMMAND SHORTCUTS
├── Makefile                        # For Unix/Mac/Linux
├── docker-commands.ps1             # For Windows PowerShell
├── docker-commands.bat             # For Windows Batch
│
├── 🔧 BACKEND SUPPORT
├── backend/
│   └── entrypoint.sh               # Container startup script
│
├── 🔄 REVERSE PROXY (OPTIONAL)
├── nginx/
│   └── nginx.conf                  # Production reverse proxy
│
├── 📖 DOCUMENTATION
├── DOCKER_QUICKSTART.md            # Quick start guide
├── DOCKER_IMPLEMENTATION.md        # What was created
├── DOCKER_VERIFICATION.md          # Setup verification
├── mdfiles/DOCKER_SETUP.md         # Complete reference
│
├── 🤖 CI/CD (OPTIONAL)
├── .github/
│   └── workflows/
│       └── docker-build.yml        # GitHub Actions workflow
│
└── 🎯 YOUR APPLICATION CODE
    ├── app/                        # FastAPI backend
    ├── frontend/                   # Next.js frontend
    ├── db/
    │   └── runtime/                # Database files
    ├── alembic/                    # Database migrations
    └── scripts/                    # Utility scripts
```

---

## 🎯 Common Tasks

### Setup Development Environment

```bash
# 1. Create environment file
cp .env.example .env

# 2. (Optional) Edit .env to customize
# nano .env

# 3. Start development
make dev

# 4. Wait 30-40 seconds, then open:
# http://localhost:3000 (Frontend)
# http://localhost:8000/docs (Backend API)
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Access Container Shell

```bash
# Backend
docker-compose exec backend bash
# Then: python scripts/init_db.py, alembic status, etc.

# Frontend
docker-compose exec frontend sh
# Then: npm list, npm install, etc.
```

### Reset Database (Development Only)

```bash
# Stop and remove volumes
docker-compose down -v

# Restart
docker-compose --profile dev up -d
```

### Start Production with PostgreSQL

```bash
# 1. Edit .env for production values
cp .env.example .env
# Update: DENTAI_SECRET_KEY, DEVELOPMENT_MODE=false, etc.

# 2. Start production
docker-compose --profile prod --profile postgres up -d

# 3. View status
docker-compose ps
```

### With Nginx Reverse Proxy

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile prod-nginx up -d
```

---

## 🛠️ Command Reference

### Using Make (Unix/Mac/Linux/Windows with Git Bash)

```bash
make help              # Show all commands
make dev              # Start development
make prod             # Start production
make build            # Build images
make dev-logs         # View dev logs
make shell-backend    # Access backend shell
make clean            # Remove everything
```

### Using Windows Scripts

```powershell
# PowerShell
.\docker-commands.ps1 dev
.\docker-commands.ps1 prod
.\docker-commands.ps1 shell-backend

# Batch
docker-commands.bat dev
docker-commands.bat prod
```

### Using Docker Compose Directly

```bash
# Development (SQLite, hot reload)
docker-compose --profile dev up -d
docker-compose --profile dev logs -f
docker-compose --profile dev down

# Production (PostgreSQL)
docker-compose --profile prod --profile postgres up -d
docker-compose --profile prod --profile postgres down

# With Nginx
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile prod-nginx up -d
```

---

## 🔍 Architecture

```
┌─────────────────────────────────────────────────┐
│  Docker Compose Network: dentai-network        │
│  (Bridge network for inter-service communication)
│                                                 │
│  ┌─────────────────────────────────────────┐  │
│  │         FRONTEND (Next.js)              │  │
│  │         Port: 3000                      │  │
│  │         - React 19 UI                   │  │
│  │         - Hot reload in dev             │  │
│  └─────────────────────────────────────────┘  │
│                    ↓ HTTP                       │
│  ┌─────────────────────────────────────────┐  │
│  │         BACKEND (FastAPI)               │  │
│  │         Port: 8000                      │  │
│  │         - SQLAlchemy ORM                │  │
│  │         - Alembic migrations            │  │
│  │         - Hot reload in dev             │  │
│  └─────────────────────────────────────────┘  │
│                    ↓ SQL                       │
│  ┌─────────────────────────────────────────┐  │
│  │  DATABASE                               │  │
│  │  - SQLite (dev): db/runtime/            │  │
│  │  - PostgreSQL (prod): postgres service  │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
│  (Optional)                                    │
│  ┌─────────────────────────────────────────┐  │
│  │  ADMINER (Database UI)                  │  │
│  │  Port: 8080                             │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
└─────────────────────────────────────────────────┘

Production with Nginx Reverse Proxy:
┌─────────────────────────────────────────┐
│  NGINX (Reverse Proxy)                  │
│  Port: 80 (or 443 with SSL)             │
│  Routes:                                │
│  - / → Frontend                         │
│  - /api → Backend                       │
│  - /docs → Backend API docs             │
└─────────────────────────────────────────┘
```

---

## ✅ Environment Setup

### Required Variables (.env)

```env
# Backend
DENTAI_SECRET_KEY=<your-secret-key>
DENTAI_ACCESS_TOKEN_EXPIRE_MINUTES=1440
GEMINI_API_KEY=<your-key>
HUGGINGFACE_API_KEY=<your-key>
DATABASE_URL=sqlite:///db/runtime/dentai_app.db

# Frontend
NEXT_PUBLIC_API_URL=http://backend:8000

# Development
DEVELOPMENT_MODE=false

# PostgreSQL (if using)
POSTGRES_USER=dentai
POSTGRES_PASSWORD=<secure-password>
POSTGRES_DB=dentai_db
```

Generate a secure JWT secret:

```bash
# macOS/Linux
openssl rand -hex 32

# Windows PowerShell
[System.Convert]::ToHexString([System.Security.Cryptography.RNGCryptoServiceProvider]::new().GetBytes(32))
```

---

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Find what's using the port
lsof -i :8000          # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Change port in docker-compose.yml:
ports:
  - "8001:8000"
```

### Container Won't Start

```bash
# Check logs
docker-compose logs backend

# Manually initialize
docker-compose exec backend python scripts/init_db.py

# Restart
docker-compose restart backend
```

### Frontend Can't Reach Backend

```bash
# Verify backend is running
curl http://localhost:8000/docs

# Check frontend logs
docker-compose logs frontend

# Verify NEXT_PUBLIC_API_URL
# Should be http://backend:8000 (internal) not http://localhost:8000
```

### Database Errors

```bash
# Reset database (dev only)
docker-compose down -v
docker-compose --profile dev up -d

# Check migrations
docker-compose exec backend alembic current

# View migration history
docker-compose exec backend alembic history
```

**For more detailed troubleshooting**, see [mdfiles/DOCKER_SETUP.md](mdfiles/DOCKER_SETUP.md#troubleshooting)

---

## 📊 Development vs Production

| Aspect        | Development           | Production             |
| ------------- | --------------------- | ---------------------- |
| Database      | SQLite                | PostgreSQL             |
| Port 8000     | Exposed               | Internal (via Nginx)   |
| Port 3000     | Exposed               | Internal (via Nginx)   |
| Hot Reload    | ✅ Yes                | ❌ No                  |
| Volume Mounts | ✅ Yes                | ❌ No                  |
| Workers       | 1                     | 4+                     |
| CORS          | localhost:3000        | Your domain            |
| Environment   | DEVELOPMENT_MODE=true | DEVELOPMENT_MODE=false |

---

## 🔒 Security Checklist

- [ ] `.env` file created and never committed
- [ ] `.env.example` committed with safe defaults
- [ ] Unique JWT secret generated and stored in `.env`
- [ ] API keys added to `.env` (not hardcoded)
- [ ] Database passwords changed from defaults
- [ ] PostgreSQL port not exposed externally (production)
- [ ] HTTPS configured (optional, nginx config ready)
- [ ] Secrets not logged in container output
- [ ] `.dockerignore` prevents accidental file inclusion

---

## 📈 Performance Tips

### Development

- Hot reload enabled by default
- Source files mounted as volumes
- SQLite fast enough for local development
- Disable unused services with profiles

### Production

- Multi-stage Docker builds (optimized)
- 4+ worker processes in Uvicorn
- PostgreSQL for data persistence
- Nginx reverse proxy for frontend assets
- Consider CDN for static files
- Set resource limits in docker-compose

---

## 🚢 Deployment Options

### Local Docker

```bash
docker-compose --profile prod --profile postgres up -d
```

### Cloud Platforms

- **AWS ECS**: Use docker-compose to build, push to ECR
- **DigitalOcean**: Deploy docker-compose to App Platform
- **Heroku**: Convert Dockerfile to buildpacks
- **Kubernetes**: Generate k8s manifests from docker-compose
- **Railway**: Connect GitHub repo for automatic deployment
- **Render**: Deploy from Dockerfile directly

See `.github/workflows/docker-build.yml` for CI/CD example.

---

## 📞 Getting Help

1. **Quick Question?** → Read [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md)
2. **Need Full Guide?** → Read [mdfiles/DOCKER_SETUP.md](mdfiles/DOCKER_SETUP.md)
3. **Specific Issue?** → See [DOCKER_SETUP.md#troubleshooting](mdfiles/DOCKER_SETUP.md#troubleshooting)
4. **Verify Setup?** → Use [DOCKER_VERIFICATION.md](DOCKER_VERIFICATION.md)
5. **Want Details?** → Read [DOCKER_IMPLEMENTATION.md](DOCKER_IMPLEMENTATION.md)

---

## 📋 Checklist for First Run

- [ ] Docker and Docker Compose installed
- [ ] `.env` created from `.env.example`
- [ ] `DENTAI_SECRET_KEY` updated (not default)
- [ ] Run: `docker-compose --profile dev up -d`
- [ ] Wait 30-40 seconds for services to start
- [ ] Open: http://localhost:3000 (Frontend)
- [ ] Open: http://localhost:8000/docs (Backend API)
- [ ] Edit a file in `app/` or `frontend/` and verify hot reload
- [ ] Run: `docker-compose down` to stop
- [ ] Run verification: [DOCKER_VERIFICATION.md](DOCKER_VERIFICATION.md)

---

## 🎓 Learning Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Next.js Docker Guide](https://nextjs.org/docs/deployment/docker)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [Alembic Migrations](https://alembic.sqlalchemy.org/)

---

## 📝 Quick Reference Card

```bash
# Common Commands
make dev                          # Start development
make prod                         # Start production
docker-compose logs -f            # View all logs
docker-compose exec backend bash  # Backend shell
docker-compose down -v            # Stop & remove volumes
docker-compose ps                 # Show containers
docker images                     # Show built images

# For Windows
.\docker-commands.ps1 dev         # Start development
docker-commands.bat prod          # Start production

# Direct Docker Compose
docker-compose --profile dev up -d           # Dev mode
docker-compose --profile prod --profile postgres up -d  # Prod mode
```

---

**Version**: 1.0  
**Last Updated**: May 2026  
**Status**: ✅ Ready for Development & Production

**Next Step**: Run `make dev` or `.\docker-commands.ps1 dev` to get started! 🚀
