@echo off
REM Interview Assistant - Docker Startup Script for Windows
REM This script sets up and starts the Interview Assistant with all Phase 1 features

echo 🎤 Interview Assistant - Phase 1 Setup
echo ======================================

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not running. Please start Docker Desktop and try again.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo ⚠️  .env file not found. Creating from template...
    copy .env.example .env >nul
    echo ✅ Created .env file. Please edit it with your OpenAI API key:
    echo    OPENAI_API_KEY=your_actual_api_key_here
    echo.
    pause
)

REM Check if OpenAI API key is set
findstr /B "OPENAI_API_KEY=sk-" .env >nul
if %errorlevel% neq 0 (
    echo ⚠️  OpenAI API key not configured properly in .env file
    echo    Please set: OPENAI_API_KEY=your_actual_api_key_here
    echo.
    pause
)

echo 🐳 Starting Docker services...

REM Stop any existing containers
docker-compose down >nul 2>&1

REM Build and start services
echo 📦 Building application...
docker-compose build --no-cache

echo 🚀 Starting services (PostgreSQL + Redis + App)...
docker-compose up -d

REM Wait for services to be ready
echo ⏳ Waiting for services to be ready...
timeout /t 10 /nobreak >nul

REM Check health
echo 🏥 Checking service health...

REM Check PostgreSQL
docker-compose exec -T postgres pg_isready -U interview_user >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ PostgreSQL: Ready
) else (
    echo ❌ PostgreSQL: Not ready
)

REM Check Redis
docker-compose exec -T redis redis-cli ping >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Redis: Ready
) else (
    echo ❌ Redis: Not ready
)

REM Check Application
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Application: Ready
) else (
    echo ❌ Application: Not ready (might still be starting...)
)

echo.
echo 🎉 Interview Assistant is starting!
echo ======================================
echo.
echo 📋 Access Points:
echo    Desktop Control Panel: http://localhost:8000
echo    Mobile PIN Entry:      http://localhost:8000/join
echo    Health Check:          http://localhost:8000/health
echo.
echo 📱 Phase 1 Features Available:
echo    ✅ Context-aware AI responses
echo    ✅ PIN code system (6-digit codes)
echo    ✅ Response scoring (1-10 scale)
echo    ✅ Dynamic caching with Redis
echo    ✅ PostgreSQL database
echo.
echo 📊 Monitoring:
echo    View logs: docker-compose logs -f app
echo    Stop:      docker-compose down
echo    Restart:   docker-compose restart
echo.

REM Show real-time logs
echo 📝 Showing application logs (Ctrl+C to exit):
echo ==============================================
docker-compose logs -f app