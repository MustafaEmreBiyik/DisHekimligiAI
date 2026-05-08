@echo off
REM DentAI Docker Commands for Windows
REM Usage: docker\docker-commands.bat [command]
REM Note: Run from project root directory

setlocal enabledelayedexpansion

if "%1"=="" (
    call :show_help
    exit /b 0
)

if "%1"=="help" (
    call :show_help
) else if "%1"=="dev" (
    call :dev_start
) else if "%1"=="dev-logs" (
    call :dev_logs
) else if "%1"=="dev-stop" (
    call :dev_stop
) else if "%1"=="prod" (
    call :prod_start
) else if "%1"=="prod-stop" (
    call :prod_stop
) else if "%1"=="build" (
    call :build_images
) else if "%1"=="logs" (
    call :show_logs
) else if "%1"=="shell-backend" (
    call :shell_backend
) else if "%1"=="shell-frontend" (
    call :shell_frontend
) else if "%1"=="status" (
    call :show_status
) else if "%1"=="clean" (
    call :clean_all
) else if "%1"=="env-setup" (
    call :env_setup
) else (
    echo Unknown command: %1
    call :show_help
    exit /b 1
)

exit /b 0

:show_help
echo DentAI Docker Commands
echo =====================
echo.
echo Development:
echo   docker\docker-commands.bat dev              - Start development environment
echo   docker\docker-commands.bat dev-logs         - Show development logs
echo   docker\docker-commands.bat dev-stop         - Stop development environment
echo.
echo Production:
echo   docker\docker-commands.bat prod             - Start production environment
echo   docker\docker-commands.bat prod-stop        - Stop production environment
echo.
echo Building:
echo   docker\docker-commands.bat build            - Build all Docker images
echo.
echo Utilities:
echo   docker\docker-commands.bat shell-backend    - Access backend shell
echo   docker\docker-commands.bat shell-frontend   - Access frontend shell
echo   docker\docker-commands.bat logs             - Show all logs
echo   docker\docker-commands.bat status           - Show container status
echo   docker\docker-commands.bat env-setup        - Create .env file
echo   docker\docker-commands.bat clean            - Stop and remove all containers/volumes
echo.
goto :eof

:dev_start
echo Starting DentAI development environment...
if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo Please update .env with your values
)
docker-compose -f docker/docker-compose.yml --profile dev up -d
echo.
echo Development environment started!
echo Frontend: http://localhost:3000
echo Backend:  http://localhost:8000/docs
goto :eof

:dev_logs
docker-compose -f docker/docker-compose.yml logs -f
goto :eof

:dev_stop
echo Stopping development environment...
docker-compose -f docker/docker-compose.yml --profile dev down
goto :eof

:prod_start
echo Starting DentAI production environment...
if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo Please update .env with production values!
)
docker-compose -f docker/docker-compose.yml --profile prod --profile postgres up -d
goto :eof

:prod_stop
echo Stopping production environment...
docker-compose -f docker/docker-compose.yml --profile prod --profile postgres down
goto :eof

:build_images
echo Building Docker images...
docker-compose -f docker/docker-compose.yml build
goto :eof

:show_logs
docker-compose -f docker/docker-compose.yml logs -f
goto :eof

:shell_backend
docker-compose -f docker/docker-compose.yml exec backend bash
goto :eof

:shell_frontend
docker-compose -f docker/docker-compose.yml exec frontend sh
goto :eof

:show_status
docker-compose -f docker/docker-compose.yml ps
goto :eof

:clean_all
echo Removing all containers and volumes...
docker-compose -f docker/docker-compose.yml down -v
docker-compose -f docker/docker-compose.yml --profile postgres down -v
docker-compose -f docker/docker-compose.yml --profile prod down -v
echo Clean complete!
goto :eof

:env_setup
if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo Created .env file - please update with your values
) else (
    echo .env already exists
)
goto :eof
