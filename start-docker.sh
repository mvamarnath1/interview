#!/bin/bash

# Interview Assistant - Docker Startup Script
# This script sets up and starts the Interview Assistant with all Phase 1 features

set -e

echo "🎤 Interview Assistant - Phase 1 Setup"
echo "======================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.example .env
    echo "✅ Created .env file. Please edit it with your OpenAI API key:"
    echo "   OPENAI_API_KEY=your_actual_api_key_here"
    echo ""
    read -p "Press Enter to continue after editing .env file..."
fi

# Check if OpenAI API key is set
if ! grep -q "^OPENAI_API_KEY=sk-" .env; then
    echo "⚠️  OpenAI API key not configured properly in .env file"
    echo "   Please set: OPENAI_API_KEY=your_actual_api_key_here"
    echo ""
    read -p "Press Enter to continue anyway (AI features will be limited)..."
fi

echo "🐳 Starting Docker services..."

# Stop any existing containers
docker-compose down 2>/dev/null || true

# Build and start services
echo "📦 Building application..."
docker-compose build --no-cache

echo "🚀 Starting services (PostgreSQL + Redis + App)..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check health
echo "🏥 Checking service health..."

# Check PostgreSQL
if docker-compose exec -T postgres pg_isready -U interview_user > /dev/null 2>&1; then
    echo "✅ PostgreSQL: Ready"
else
    echo "❌ PostgreSQL: Not ready"
fi

# Check Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis: Ready"
else
    echo "❌ Redis: Not ready"
fi

# Check Application
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Application: Ready"
else
    echo "❌ Application: Not ready (might still be starting...)"
fi

echo ""
echo "🎉 Interview Assistant is starting!"
echo "======================================"
echo ""
echo "📋 Access Points:"
echo "   Desktop Control Panel: http://localhost:8000"
echo "   Mobile PIN Entry:      http://localhost:8000/join"
echo "   Health Check:          http://localhost:8000/health"
echo ""
echo "📱 Phase 1 Features Available:"
echo "   ✅ Context-aware AI responses"
echo "   ✅ PIN code system (6-digit codes)"
echo "   ✅ Response scoring (1-10 scale)"
echo "   ✅ Dynamic caching with Redis"
echo "   ✅ PostgreSQL database"
echo ""
echo "📊 Monitoring:"
echo "   View logs: docker-compose logs -f app"
echo "   Stop:      docker-compose down"
echo "   Restart:   docker-compose restart"
echo ""

# Show real-time logs
echo "📝 Showing application logs (Ctrl+C to exit):"
echo "=============================================="
docker-compose logs -f app