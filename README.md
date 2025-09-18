# 🎤 Interview Assistant

A comprehensive real-time interview assistant with audio recording, AI-powered transcription, and intelligent interview suggestions using FastAPI, WebSocket, OpenAI Whisper, and Google Gemini.

## ✨ Features

### Phase 1 - Core Features ✅
- **Real-time Communication**: WebSocket-based connection between desktop control panel and mobile phone
- **QR Code Generation**: Easy connection via QR code scanning
- **Session Management**: Create, manage, and track interview sessions
- **Modern Dark UI**: Responsive design with dark theme
- **Database Integration**: SQLite for development, PostgreSQL support for production
- **Admin Panel**: Session history, message tracking, and cleanup functionality

### Phase 2 - AI Features ✅
- **🎙️ Audio Recording**: System audio capture using sounddevice
- **📝 Speech-to-Text**: OpenAI Whisper API integration for real-time transcription
- **🤖 AI Interview Assistant**: Google Gemini AI for intelligent interview suggestions
- **❓ Question Generation**: Context-aware interview questions based on job role and company
- **🔍 Response Analysis**: Real-time analysis of candidate responses with scoring
- **💡 Interview Tips**: AI-powered suggestions for interviewers
- **📊 Interview Summary**: Comprehensive interview summaries and recommendations

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- OpenAI API key (for transcription)
- Google AI API key (for AI features)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd interview-assistant
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
# Copy the example file
cp .env.example .env

# Edit .env file and add your API keys:
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
```

4. **Start the application**
```bash
python -m app.main
```

5. **Open in browser**
Navigate to `http://localhost:8000`

## 🔧 Configuration

### API Keys

#### OpenAI API Key (for Whisper transcription)
1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Add it to your `.env` file as `OPENAI_API_KEY`

#### Google AI API Key (for Gemini AI)
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Add it to your `.env` file as `GOOGLE_API_KEY`

### Database Configuration

**Development (Default)**: SQLite database stored locally
```env
DATABASE_URL=sqlite:///./interview_assistant.db
```

**Production**: PostgreSQL with Docker
```bash
# Start PostgreSQL container
docker-compose up -d

# Use PostgreSQL
DATABASE_URL=postgresql://username:password@localhost/interview_assistant
```

## 📱 How to Use

### 1. Create Interview Session
1. Open the control panel at `http://localhost:8000`
2. Enter your name and click "Create New Session"
3. A QR code will be generated for mobile connection

### 2. Connect Mobile Device
1. Scan the QR code with your phone
2. Or manually navigate to the provided URL
3. The mobile client will connect to the desktop control panel

### 3. Set Interview Context (Phase 2)
1. Fill in job role, company name, and interview type
2. Add key topics/skills to focus on
3. Click "Set Context" to enable AI features

### 4. Start Audio Recording (Phase 2)
1. Click "Start Recording" to begin audio capture
2. The system will record ambient audio from your computer
3. Click "Stop Recording" to end and auto-transcribe

### 5. Use AI Features (Phase 2)
- **Generate Questions**: Get context-aware interview questions
- **Get Tips**: Receive interviewer tips for different phases
- **Auto-Analysis**: Responses are automatically analyzed for scoring and follow-ups
- **Summarize**: Generate comprehensive interview summary at the end

## 🏗️ Architecture

```
interview-assistant/
├── app/
│   ├── main.py              # FastAPI application and routes
│   ├── database.py          # SQLAlchemy models and database config
│   ├── audio/               # Audio processing modules
│   │   ├── capture.py       # Audio recording with sounddevice
│   │   └── transcriber.py   # OpenAI Whisper integration
│   ├── ai/                  # AI processing modules
│   │   └── gemini.py        # Google Gemini AI integration
│   ├── templates/           # Jinja2 HTML templates
│   │   ├── index.html       # Desktop control panel
│   │   ├── mobile.html      # Mobile client interface
│   │   └── admin.html       # Admin panel
│   └── static/              # Static assets
│       └── css/
│           └── style.css    # Modern dark theme styles
├── requirements.txt         # Python dependencies
├── docker-compose.yml       # PostgreSQL container
├── Dockerfile              # Application container
├── .env.example            # Environment variables template
└── README.md               # This file
```

## 🔌 API Endpoints

### Core Endpoints
- `GET /` - Control panel interface
- `POST /create_session` - Create new interview session
- `GET /mobile?session_id={id}` - Mobile client interface
- `WS /ws/{session_id}/{client_type}` - WebSocket connection

### Audio Endpoints (Phase 2)
- `POST /audio/start_recording/{session_id}` - Start audio recording
- `POST /audio/stop_recording/{session_id}` - Stop recording and transcribe
- `POST /audio/transcribe` - Upload and transcribe audio file

### AI Endpoints (Phase 2)
- `POST /ai/set_context/{session_id}` - Set interview context
- `POST /ai/generate_questions/{session_id}` - Generate interview questions
- `POST /ai/analyze_response/{session_id}` - Analyze candidate response
- `GET /ai/interview_tips/{session_id}` - Get interviewer tips
- `GET /ai/summarize_interview/{session_id}` - Generate interview summary

### Admin Endpoints
- `GET /admin` - Admin panel interface
- `GET /admin/session/{session_id}/history` - Session message history
- `DELETE /admin/session/{session_id}` - Delete session and cleanup

## 🛠️ Technologies

### Backend
- **FastAPI**: Modern async web framework
- **SQLAlchemy**: ORM for database operations
- **WebSockets**: Real-time bidirectional communication
- **sounddevice**: Cross-platform audio recording
- **OpenAI API**: Whisper speech-to-text transcription
- **Google Generative AI**: Gemini AI for interview assistance

### Frontend
- **Jinja2**: Template engine for dynamic HTML
- **Modern CSS**: Dark theme with CSS variables and responsive design
- **WebSocket API**: Real-time communication with backend
- **HTML5**: Semantic markup and accessibility

### Database
- **SQLite**: Development database (default)
- **PostgreSQL**: Production database with Docker

## 🚀 Deployment

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up -d

# Application will be available at http://localhost:8000
```

### Manual Deployment
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY="your-key"
export GOOGLE_API_KEY="your-key"

# Run application
python -m app.main
```

## 🔧 Development

### Running in Development Mode
```bash
# Install development dependencies
pip install -r requirements.txt

# Set debug environment
export DEBUG=1

# Run with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing Audio Features
1. Ensure microphone permissions are granted
2. Test with different audio input devices
3. Verify transcription accuracy with clear speech
4. Check AI responses with proper context setup

## 🐛 Troubleshooting

### Common Issues

**Audio recording not working:**
- Check microphone permissions
- Verify sounddevice installation: `pip install sounddevice`
- List available audio devices in Python:
```python
import sounddevice as sd
print(sd.query_devices())
```

**AI features disabled:**
- Verify API keys are set in `.env` file
- Check API key validity and quotas
- Ensure internet connection for API calls

**WebSocket connection issues:**
- Check firewall settings
- Verify port 8000 is available
- Try refreshing the browser page

**Database errors:**
- Delete existing database file: `rm interview_assistant.db`
- Restart the application to recreate tables

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit a pull request

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the API documentation
3. Create an issue on GitHub with detailed error logs

---

**Made with ❤️ for better interviews**