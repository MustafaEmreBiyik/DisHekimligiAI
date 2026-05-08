# DentAI Docker Commands for PowerShell
# Usage: .\docker-commands.ps1 -Command dev
# Note: Run from project root directory

param(
    [Parameter(Position = 0)]
    [ValidateSet('help', 'dev', 'dev-logs', 'dev-stop', 'prod', 'prod-stop', 'build', 'logs', 'shell-backend', 'shell-frontend', 'status', 'clean', 'env-setup')]
    [string]$Command = 'help'
)

function Show-Help {
    @"
DentAI Docker Commands
=====================

Development:
  .\docker\docker-commands.ps1 dev              - Start development environment
  .\docker\docker-commands.ps1 dev-logs         - Show development logs
  .\docker\docker-commands.ps1 dev-stop         - Stop development environment

Production:
  .\docker\docker-commands.ps1 prod             - Start production environment
  .\docker\docker-commands.ps1 prod-stop        - Stop production environment

Building:
  .\docker\docker-commands.ps1 build            - Build all Docker images

Utilities:
  .\docker\docker-commands.ps1 shell-backend    - Access backend shell
  .\docker\docker-commands.ps1 shell-frontend   - Access frontend shell
  .\docker\docker-commands.ps1 logs             - Show all logs
  .\docker\docker-commands.ps1 status           - Show container status
  .\docker\docker-commands.ps1 env-setup        - Create .env file
  .\docker\docker-commands.ps1 clean            - Stop and remove all containers/volumes
"@
}

function Dev-Start {
    Write-Host "Starting DentAI development environment..." -ForegroundColor Green
    
    if (-not (Test-Path '.env')) {
        Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
        Copy-Item '.env.example' '.env'
        Write-Host "Please update .env with your values" -ForegroundColor Yellow
    }
    
    & docker-compose -f docker/docker-compose.yml --profile dev up -d
    Write-Host "`nDevelopment environment started!" -ForegroundColor Green
    Write-Host "Frontend: http://localhost:3000" -ForegroundColor Cyan
    Write-Host "Backend:  http://localhost:8000/docs" -ForegroundColor Cyan
}

function Dev-Logs {
    & docker-compose -f docker/docker-compose.yml logs -f
}

function Dev-Stop {
    Write-Host "Stopping development environment..." -ForegroundColor Yellow
    & docker-compose -f docker/docker-compose.yml --profile dev down
}

function Prod-Start {
    Write-Host "Starting DentAI production environment..." -ForegroundColor Green
    
    if (-not (Test-Path '.env')) {
        Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
        Copy-Item '.env.example' '.env'
        Write-Host "Please update .env with production values!" -ForegroundColor Red
    }
    
    & docker-compose -f docker/docker-compose.yml --profile prod --profile postgres up -d
}

function Prod-Stop {
    Write-Host "Stopping production environment..." -ForegroundColor Yellow
    & docker-compose -f docker/docker-compose.yml --profile prod --profile postgres down
}

function Build-Images {
    Write-Host "Building Docker images..." -ForegroundColor Green
    & docker-compose -f docker/docker-compose.yml build
}

function Show-Logs {
    & docker-compose -f docker/docker-compose.yml logs -f
}

function Shell-Backend {
    Write-Host "Connecting to backend shell..." -ForegroundColor Green
    & docker-compose -f docker/docker-compose.yml exec backend bash
}

function Shell-Frontend {
    Write-Host "Connecting to frontend shell..." -ForegroundColor Green
    & docker-compose -f docker/docker-compose.yml exec frontend sh
}

function Show-Status {
    & docker-compose -f docker/docker-compose.yml ps
}

function Clean-All {
    Write-Host "Removing all containers and volumes..." -ForegroundColor Red
    & docker-compose -f docker/docker-compose.yml down -v
    & docker-compose -f docker/docker-compose.yml --profile postgres down -v
    & docker-compose -f docker/docker-compose.yml --profile prod down -v
    Write-Host "Clean complete!" -ForegroundColor Green
}

function Env-Setup {
    if (-not (Test-Path '.env')) {
        Write-Host "Creating .env from .env.example..." -ForegroundColor Green
        Copy-Item '.env.example' '.env'
        Write-Host "Created .env file - please update with your values" -ForegroundColor Yellow
    } else {
        Write-Host ".env already exists" -ForegroundColor Yellow
    }
}

# Execute the requested command
switch ($Command) {
    'help' { Show-Help }
    'dev' { Dev-Start }
    'dev-logs' { Dev-Logs }
    'dev-stop' { Dev-Stop }
    'prod' { Prod-Start }
    'prod-stop' { Prod-Stop }
    'build' { Build-Images }
    'logs' { Show-Logs }
    'shell-backend' { Shell-Backend }
    'shell-frontend' { Shell-Frontend }
    'status' { Show-Status }
    'clean' { Clean-All }
    'env-setup' { Env-Setup }
    default { Show-Help }
}
