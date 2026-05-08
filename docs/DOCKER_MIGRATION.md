# Docker Folder Organization - Migration Guide

## What Changed

Docker configuration files have been organized into a dedicated `docker/` folder to keep the project root clean and organized.

## New Structure

```
project-root/
├── docker/                          # ← All Docker files here
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── docker-compose.yml
│   ├── docker-compose.override.yml
│   ├── docker-compose.prod.yml
│   ├── docker-commands.ps1          # PowerShell helper (run from root: .\docker\docker-commands.ps1)
│   ├── docker-commands.bat          # Batch helper (run from root: docker\docker-commands.bat)
│   └── .dockerignore
│
├── Makefile                         # ← Updated to use -f docker/docker-compose.yml
├── README.md                        # ← Updated with new paths
├── DEVELOPER_QUICK_REFERENCE.md     # ← Updated with new paths
└── ... other files
```

## How to Use

### Development

All commands remain the same for most users - just use `make dev`:

```bash
make dev
```

For direct Docker Compose commands, specify the docker-compose file:

```bash
docker-compose -f docker/docker-compose.yml --profile dev up -d
```

### PowerShell (Windows)

```powershell
.\docker\docker-commands.ps1 dev
```

### Batch (Windows)

```cmd
docker\docker-commands.bat dev
```

## What Stayed the Same

- ✅ All `make` commands work exactly as before
- ✅ Functionality is identical
- ✅ Volumes and networking unchanged
- ✅ Environment configuration unchanged

## Migration Notes

- Old root-level Docker files are now in `docker/` folder
- Makefile automatically updated with `-f docker/docker-compose.yml`
- Documentation updated with new paths
- No action required for existing projects - continue using `make dev`

## Benefits

- 🎯 **Cleaner project root** - Less clutter
- 🗂️ **Better organization** - Docker configs grouped together
- 📚 **Easier navigation** - Scripts and configs in one place
- 🚀 **Scalable** - Easy to add CI/CD or other infrastructure files

---

**Start developing:** `make dev`
