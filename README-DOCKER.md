# Interview Assistant - Phase 1 Production Setup

## 🚀 Quick Start with Docker

### Prerequisites
- Docker and Docker Compose installed
- OpenAI API key (for context-aware AI responses)

### 1. Clone and Setup
```bash
git clone <your-repo>
cd interview-assistant
cp .env.example .env
```

### 2. Configure Environment
Edit `.env` file and add your OpenAI API key:
```bash
OPENAI_API_KEY=your_actual_openai_api_key_here
```

### 3. Start All Services
```bash
# Start PostgreSQL, Redis, and the application
docker-compose up -d

# View logs
docker-compose logs -f app
```

### 4. Access Application
- **Desktop Control Panel**: http://localhost:8000
- **Mobile PIN Entry**: http://localhost:8000/join
- **Health Check**: http://localhost:8000/health

## 📱 Phase 1 Features

### ✅ Context-Aware AI Responses
- Uses conversation history for better responses
- OpenAI GPT-3.5-turbo integration
- Dynamic question caching for performance

### ✅ PIN Code System
- 6-digit PIN codes alongside QR codes
- Easy mobile access via `/join` page
- Secure session management

### ✅ Response Scoring (1-10)
- AI confidence scoring for each response
- Visual feedback with color coding
- Performance tracking and analytics

### ✅ Dynamic Caching
- User-specific question caching
- Redis-powered session management
- Optimized for millisecond responses

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Desktop PC    │────│   Mobile Phone  │
│  (Interviewer)  │    │  (Candidate)    │
└─────────────────┘    └─────────────────┘
         │                       │
         └───────────┬───────────┘
                     │
         ┌─────────────────────────────┐
         │     FastAPI Application     │
         │  • Context-aware AI         │
         │  • PIN code system          │
         │  • Response scoring         │
         │  • WebSocket real-time      │
         └─────────────────────────────┘
                     │
         ┌─────────────────────────────┐
         │      PostgreSQL DB         │
         │  • Sessions & Messages      │
         │  • Question Cache           │
         │  • User Progress            │
         └─────────────────────────────┘
                     │
         ┌─────────────────────────────┐
         │        Redis Cache          │
         │  • Session management       │
         │  • Dynamic caching          │
         └─────────────────────────────┘
```

## 🛠️ Development

### Run Locally (SQLite)
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment for development
export DATABASE_URL=sqlite:///./interview_assistant.db
export OPENAI_API_KEY=your_key_here

# Run application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Database Migrations
```bash
# Create migration
alembic revision --autogenerate -m "Add new feature"

# Apply migrations
alembic upgrade head
```

## 🔧 Configuration

### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for AI responses | Required |
| `DATABASE_URL` | Database connection string | SQLite |
| `REDIS_URL` | Redis connection for caching | None |
| `AI_MODEL` | OpenAI model for responses | gpt-3.5-turbo |
| `MAX_CONTEXT_MESSAGES` | Context history limit | 10 |
| `CACHE_TTL_SECONDS` | Cache expiration time | 3600 |

### Docker Services
- **postgres**: PostgreSQL 15 database
- **redis**: Redis 7 cache
- **app**: FastAPI application
- **nginx**: Reverse proxy (production profile)

## 📊 Monitoring

### Health Checks
```bash
# Application health
curl http://localhost:8000/health

# Database health
docker-compose exec postgres pg_isready

# Redis health
docker-compose exec redis redis-cli ping
```

### Logs
```bash
# Application logs
docker-compose logs app

# Database logs
docker-compose logs postgres

# All services
docker-compose logs
```

## 🚦 Usage Flow

### Desktop (Interviewer)
1. Open http://localhost:8000
2. Enter name and create session
3. Share PIN code or QR code with candidate
4. Ask questions - AI provides context-aware prompts

### Mobile (Candidate)
1. Go to http://localhost:8000/join
2. Enter 6-digit PIN code
3. Receive real-time prompts and feedback
4. Get scored responses with visual feedback

## 🔒 Security

- Session-based authentication
- PIN code expiration (24 hours)
- PostgreSQL with connection pooling
- Environment-based configuration
- Health check endpoints

## 📈 Performance

- **Sub-second responses** with caching
- **WebSocket real-time** communication
- **Connection pooling** for database
- **Redis caching** for session data
- **Optimized Docker** containers

## 🛟 Troubleshooting

### Common Issues

1. **OpenAI API Key Error**
   ```bash
   # Check environment
   docker-compose exec app env | grep OPENAI
   ```

2. **Database Connection**
   ```bash
   # Check PostgreSQL
   docker-compose exec postgres psql -U interview_user -d interview_assistant -c "SELECT 1;"
   ```

3. **Cache Issues**
   ```bash
   # Flush Redis cache
   docker-compose exec redis redis-cli FLUSHALL
   ```

### Reset Everything
```bash
# Stop and remove all data
docker-compose down -v

# Rebuild and restart
docker-compose up --build -d
```

## 📋 Next Steps (Phase 2)

- [ ] Advanced analytics dashboard
- [ ] Multi-language support
- [ ] Voice-to-text integration
- [ ] Interview recording and playback
- [ ] Custom question templates
- [ ] Team collaboration features