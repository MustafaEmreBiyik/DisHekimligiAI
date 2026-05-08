# Quick Start Guide - DentAI Docker

## 1-Minute Setup

```bash
# Create environment file
cp .env.example .env

# Start development
docker-compose --profile dev up -d

# Wait 30-40 seconds for services to start, then:
# Frontend: http://localhost:3000
# Backend Docs: http://localhost:8000/docs
```

## Docker Desktop Setup (Windows/Mac)

1. Install Docker Desktop from https://www.docker.com/products/docker-desktop
2. Start Docker Desktop
3. Open PowerShell/Terminal and run:
   ```bash
   cd d:\Projects\dentai
   docker-compose --profile dev up -d
   ```

## Linux Setup

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add to docker group (optional, to avoid sudo)
sudo usermod -aG docker $USER
newgrp docker

# Start DentAI
cd /path/to/dentai
docker-compose --profile dev up -d
```

## Verify Everything is Running

```bash
# Check containers
docker-compose ps

# Check backend
curl http://localhost:8000/docs

# Check frontend
curl http://localhost:3000
```

## Common Commands

```bash
# View all logs
docker-compose logs -f

# View backend logs only
docker-compose logs -f backend

# Access backend terminal
docker-compose exec backend bash

# Stop everything
docker-compose down

# Reset database (development)
docker-compose down -v
docker-compose --profile dev up -d

# Start with PostgreSQL
docker-compose --profile postgres-dev up -d
```

## Using Make Commands (Unix/Linux/Mac/Windows with Git Bash)

```bash
make help          # Show all commands
make dev           # Start development
make dev-logs      # View logs
make shell-backend # Access backend shell
make clean         # Stop and clean
```

## Troubleshooting

### Port Already in Use

```bash
# Windows PowerShell
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess

# macOS/Linux
lsof -i :8000

# Then either change port in docker-compose.yml or kill the process
```

### Backend Won't Start

```bash
# Check logs
docker-compose logs backend

# Manually initialize database
docker-compose exec backend python scripts/init_db.py

# Restart
docker-compose restart backend
```

### Frontend Can't Connect to Backend

```bash
# Verify backend is running
curl http://localhost:8000/docs

# Check frontend logs
docker-compose logs frontend

# Restart frontend
docker-compose restart frontend
```

### Docker Won't Start on Windows

1. Enable Hyper-V in Windows Features
2. Or use Docker Desktop with WSL 2 backend
3. Restart Docker Desktop
4. Run: `docker-compose --profile dev up -d`

## Environment Variables

Edit `.env` to customize:

```env
# Change secret key for production
DENTAI_SECRET_KEY=your-secure-key

# Change database
DATABASE_URL=sqlite:///db/runtime/dentai_app.db

# Add API keys
GEMINI_API_KEY=your-key
HUGGINGFACE_API_KEY=your-key

# Enable development mode
DEVELOPMENT_MODE=true
```

## What's Running?

- **Frontend** (http://localhost:3000): Next.js app
- **Backend** (http://localhost:8000): FastAPI with Swagger docs at /docs
- **Database**: SQLite at db/runtime/dentai_app.db (development)

## Next Steps

1. Open frontend: http://localhost:3000
2. Check API docs: http://localhost:8000/docs
3. Edit code - changes reload automatically in dev mode
4. See [mdfiles/DOCKER_SETUP.md](mdfiles/DOCKER_SETUP.md) for advanced setup

## Production Deployment

```bash
# Create production .env
cp .env.example .env
# Edit .env with production values

# Start with PostgreSQL
docker-compose --profile prod --profile postgres up -d

# Or with Nginx reverse proxy
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile prod-nginx up -d
```

---

**Need help?** See [mdfiles/DOCKER_SETUP.md](mdfiles/DOCKER_SETUP.md) for comprehensive documentation.
