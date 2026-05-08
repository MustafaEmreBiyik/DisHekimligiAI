# Developer Quick Reference

Quick commands and tips for DentAI development.

## 🚀 Start Development (Choose One)

```bash
# Using Make (Linux/macOS/Windows Git Bash)
make dev

# Using PowerShell (Windows)
.\docker\docker-commands.ps1 dev

# Using Batch (Windows)
docker\docker-commands.bat dev

# Direct Docker Compose (All platforms)
docker-compose -f docker/docker-compose.yml --profile dev up -d
```

## 📋 Essential Commands

| Task           | Command                                                           |
| -------------- | ----------------------------------------------------------------- |
| Start dev      | `make dev`                                                        |
| Stop dev       | `make dev-stop`                                                   |
| View logs      | `docker-compose -f docker/docker-compose.yml logs -f`             |
| Backend logs   | `docker-compose -f docker/docker-compose.yml logs -f backend`     |
| Frontend logs  | `docker-compose -f docker/docker-compose.yml logs -f frontend`    |
| Backend shell  | `docker-compose -f docker/docker-compose.yml exec backend bash`   |
| Frontend shell | `docker-compose -f docker/docker-compose.yml exec frontend sh`    |
| Run tests      | `docker-compose -f docker/docker-compose.yml exec backend pytest` |
| Check status   | `docker-compose -f docker/docker-compose.yml ps`                  |
| Full reset     | `docker-compose -f docker/docker-compose.yml down -v`             |

## 🔗 Access Points (After Starting App)

| Service  | URL                                | Purpose                |
| -------- | ---------------------------------- | ---------------------- |
| Frontend | http://localhost:3000              | React UI               |
| API Docs | http://localhost:8000/docs         | Swagger UI for testing |
| ReDoc    | http://localhost:8000/redoc        | Alternative API docs   |
| OpenAPI  | http://localhost:8000/openapi.json | API schema             |

## 📁 Where to Make Changes

| Change Type         | Location                      | Auto-Reload?     |
| ------------------- | ----------------------------- | ---------------- |
| Python API          | `dentai/app/api/`             | ✅ Yes           |
| Services            | `dentai/app/services/`        | ✅ Yes           |
| DB Models           | `dentai/app/db/`              | ✅ Yes           |
| React Components    | `dentai/frontend/app/`        | ✅ Yes (HMR)     |
| Frontend Components | `dentai/frontend/components/` | ✅ Yes (HMR)     |
| Database Migrations | `dentai/alembic/versions/`    | Requires restart |

## 🐛 Quick Debugging

```bash
# Backend has import error?
docker-compose -f docker/docker-compose.yml exec backend python -c "from app.api.main import app"

# Frontend build failing?
docker-compose -f docker/docker-compose.yml exec frontend npm run build

# Database issue?
docker-compose -f docker/docker-compose.yml exec backend alembic current

# Port already in use?
# On Windows:
Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
# On Mac/Linux:
lsof -i :8000
```

## 🧪 Testing

```bash
# Run all tests
docker-compose -f docker/docker-compose.yml exec backend pytest

# Run specific test
docker-compose -f docker/docker-compose.yml exec backend pytest tests/unit/test_file.py::test_function

# Run with coverage
docker-compose -f docker/docker-compose.yml exec backend pytest --cov=app tests/

# View test output
docker-compose -f docker/docker-compose.yml exec backend pytest -v
```

## 💾 Database Tasks

```bash
# Create migration
docker-compose -f docker/docker-compose.yml exec backend alembic revision --autogenerate -m "Description"

# Apply migrations
docker-compose -f docker/docker-compose.yml exec backend alembic upgrade head

# Check current migration
docker-compose -f docker/docker-compose.yml exec backend alembic current

# View migration history
docker-compose -f docker/docker-compose.yml exec backend alembic history

# Rollback last migration
docker-compose -f docker/docker-compose.yml exec backend alembic downgrade -1

# Reset database (dev only)
docker-compose -f docker/docker-compose.yml down -v
docker-compose -f docker/docker-compose.yml --profile dev up -d
```

## 📝 Commit Workflow

```bash
# Create branch
git checkout -b feature/my-feature

# Make changes (they auto-reload!)

# Test your changes
docker-compose -f docker/docker-compose.yml exec backend pytest

# Commit changes
git add .
git commit -m "feat(backend): Add new feature"

# Push branch
git push origin feature/my-feature

# Open Pull Request on GitHub
```

## 🔍 Common Issues & Fixes

### Container won't start

```bash
docker-compose -f docker/docker-compose.yml logs backend
# Review error, usually missing dependencies or import error
```

### Hot reload not working

```bash
docker-compose -f docker/docker-compose.yml down
docker-compose -f docker/docker-compose.yml --profile dev up -d
# Volumes should auto-mount
```

### Backend can't find app module

```bash
# Verify volumes are mounted:
docker-compose -f docker/docker-compose.yml exec backend mount | grep app
# If missing, restart: docker-compose -f docker/docker-compose.yml restart backend
```

### Port 8000 or 3000 already in use

```bash
# Kill existing process or use different port
# Edit docker/docker-compose.yml ports: - "8001:8000"
```

### Frontend can't reach backend

```bash
# Verify backend is running:
curl http://localhost:8000/docs
# Check NEXT_PUBLIC_API_URL in logs:
docker-compose -f docker/docker-compose.yml logs frontend | grep -i api
```

## 🛠️ Useful Environment Variables

In `.env`:

```env
# JWT Secret (change for production!)
DENTAI_SECRET_KEY=your-secret-key

# API Keys (optional)
GEMINI_API_KEY=your-key
HUGGINGFACE_API_KEY=your-key

# Database (default is SQLite for dev)
DATABASE_URL=sqlite:///db/runtime/dentai_app.db

# Development Mode (enables hot reload)
DEVELOPMENT_MODE=true
```

## 📚 Documentation Links

- 🚀 Full Setup: [GETTING_STARTED.md](../GETTING_STARTED.md)
- 🐳 Docker Guide: [DOCKER_SETUP.md](../mdfiles/DOCKER_SETUP.md)
- 🤝 Contributing: [CONTRIBUTING.md](../CONTRIBUTING.md)
- 📖 Project Architecture: [PROJECT_ARCHITECTURE.md](../mdfiles/PROJECT_ARCHITECTURE.md)

## 💡 Pro Tips

1. **Use `make dev` instead of docker-compose** - Simpler and faster
2. **Keep Docker running** - All changes auto-reload while containers are running
3. **Check logs first** - `docker-compose -f docker/docker-compose.yml logs -f` shows most errors
4. **Use shell access** - `docker-compose -f docker/docker-compose.yml exec backend bash` for debugging
5. **Create migrations early** - DB changes require container restart
6. **Test locally before push** - Run tests with `pytest` before committing
7. **Clear browser cache** - If frontend changes don't appear, hard refresh
8. **Read API docs** - http://localhost:8000/docs has full API reference
9. **Docker files organized** - All Docker configs are in `docker/` folder for cleaner structure

## 🎯 Typical Development Session

```bash
# 1. Start work
make dev
# Wait for startup

# 2. Access app
open http://localhost:3000
# or visit in browser

# 3. Make changes
# Edit dentai/app/ → auto-reloads backend
# Edit dentai/frontend/ → auto-reloads in browser

# 4. Run tests
docker-compose -f docker/docker-compose.yml exec backend pytest

# 5. View logs if issues
docker-compose -f docker/docker-compose.yml logs -f

# 6. Commit changes
git add .
git commit -m "feat(component): Description"

# 7. End of day
make dev-stop
```

## 🔧 Useful Shortcuts

### Create bash alias (Linux/macOS)

```bash
echo "alias dd='docker-compose'" >> ~/.bashrc
# Then use: dd logs, dd ps, dd exec backend bash
```

### Windows Terminal Profile

Add to `$PROFILE`:

```powershell
function dev { docker-compose -f docker/docker-compose.yml --profile dev up -d }
function devlogs { docker-compose -f docker/docker-compose.yml logs -f }
function devstop { docker-compose -f docker/docker-compose.yml --profile dev down }
```

## ❓ Still Need Help?

1. Check logs: `docker-compose -f docker/docker-compose.yml logs`
2. Read [GETTING_STARTED.md](../GETTING_STARTED.md)
3. Check [DOCKER_SETUP.md](../mdfiles/DOCKER_SETUP.md) troubleshooting
4. Ask team or create issue

---

**Happy coding!** 🚀
