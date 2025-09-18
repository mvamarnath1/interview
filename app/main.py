from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid
import asyncio
from datetime import datetime, timedelta
import os
import tempfile
import json
from dotenv import load_dotenv
import google.generativeai as genai
import numpy as np
import wave
import hashlib
import random
import string
# Vosk imports
from vosk import Model, KaldiRecognizer
import soundfile as sf
from .database import get_db, create_tables, Session as SessionModel, Message, QuestionCache, UserProgress

# Load environment variables
load_dotenv()

# Initialize AI services
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Ultra-fast response cache for common interview questions
RESPONSE_CACHE = {
    "tell me about yourself": "Share background, skills, achievements briefly",
    "what are your strengths": "Be specific with examples",
    "what are your weaknesses": "Show growth mindset",
    "why do you want this job": "Connect skills to role",
    "where do you see yourself": "Show ambition and commitment",
    "why should we hire you": "Highlight unique value proposition",
    "describe a challenge": "Use STAR method",
    "questions for us": "Ask about growth opportunities",
    "salary expectations": "Research market rates first",
    "what motivates you": "Connect to role requirements"
}

# Initialize the FastAPI app
app = FastAPI(title="Interview Assistant")

# Create database tables on startup
create_tables()

# Add CORS middleware for future API calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and setup templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# In-memory storage for active WebSocket connections (keep for real-time features)
# Structure: active_connections[session_id] = {"mobile": WebSocket, "desktop": WebSocket}
active_connections = {}

# Helper functions for Phase 1 improvements
def generate_pin_code() -> str:
    """Generate a unique 6-digit PIN code."""
    return ''.join(random.choices(string.digits, k=6))

def hash_question(question: str) -> str:
    """Create a hash for question similarity matching."""
    # Normalize question: lowercase, remove punctuation, sort words
    normalized = ''.join(c.lower() for c in question if c.isalnum() or c.isspace())
    words = sorted(normalized.split())
    normalized_text = ' '.join(words)
    return hashlib.md5(normalized_text.encode()).hexdigest()

def categorize_question(question: str) -> str:
    """Categorize question type for progress tracking."""
    question_lower = question.lower()
    
    behavioral_keywords = ['tell me about', 'describe a time', 'experience', 'challenge', 'conflict', 'teamwork', 'leadership']
    technical_keywords = ['algorithm', 'code', 'technical', 'system design', 'database', 'programming']
    
    for keyword in behavioral_keywords:
        if keyword in question_lower:
            return 'behavioral'
    
    for keyword in technical_keywords:
        if keyword in question_lower:
            return 'technical'
    
    return 'general'

def is_mobile_device(user_agent: str) -> bool:
	"""Detect if the request is from a mobile device based on User-Agent."""
	mobile_indicators = [
		'Mobile', 'Android', 'iPhone', 'iPad', 'iPod', 'BlackBerry', 
		'Windows Phone', 'Opera Mini', 'IEMobile', 'Mobile Safari'
	]
	return any(indicator in user_agent for indicator in mobile_indicators)

def get_base_url():
	"""Get the correct base URL for the current environment."""
	# Check if running in GitHub Codespaces
	codespace_name = os.getenv("CODESPACE_NAME")
	if codespace_name:
		return f"https://{codespace_name}-8000.app.github.dev"
	
	# Check for other common environment variables
	github_workspace = os.getenv("GITHUB_WORKSPACE")
	if github_workspace:
		# Fallback for GitHub environments
		return "https://localhost:8000"  # This should be customized based on your setup
	
	# Default to localhost for local development
	return "http://localhost:8000"

@app.get("/", response_class=HTMLResponse)
async def get_control_panel(request: Request):
	"""Serve the main control panel page or redirect mobile users."""
	user_agent = request.headers.get("user-agent", "")
	
	# If mobile device, redirect to mobile landing page
	if is_mobile_device(user_agent):
		return templates.TemplateResponse("mobile_landing.html", {"request": request})
	
	# Desktop users get the control panel
	return templates.TemplateResponse("index.html", {"request": request})

@app.get("/desktop", response_class=HTMLResponse)
async def get_desktop_panel(request: Request):
	"""Force desktop control panel (bypass mobile detection)."""
	return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/config")
async def get_config():
	"""Get configuration including the correct base URL."""
	return {
		"base_url": get_base_url(),
		"join_url": f"{get_base_url()}/join"
	}

@app.get("/api/sessions")
async def get_active_sessions(db: Session = Depends(get_db)):
	"""Get list of active sessions for mobile users to join."""
	# Get sessions that haven't expired
	active_sessions = db.query(SessionModel).filter(
		SessionModel.expires_at > datetime.utcnow()
	).order_by(desc(SessionModel.created_at)).limit(10).all()
	
	return [
		{
			"session_id": session.session_id,
			"user_name": session.user_name,
			"pin_code": session.pin_code,  # Show PIN for easy joining
			"is_active": session.is_active,
			"created_at": session.created_at.isoformat(),
			"expires_at": session.expires_at.isoformat()
		}
		for session in active_sessions
	]

@app.get("/health")
async def health_check():
	"""Health check endpoint for Docker and monitoring."""
	return {
		"status": "healthy",
		"timestamp": datetime.utcnow().isoformat(),
		"version": "1.0.0",
		"features": ["context-aware-ai", "pin-codes", "response-scoring", "dynamic-caching"]
	}

@app.post("/create_session")
async def create_session(user_name: str = Form(...), db: Session = Depends(get_db)):
	"""Create a new session with PIN code for mobile access."""
	# Generate a unique session ID and PIN code
	session_id = str(uuid.uuid4())
	pin_code = generate_pin_code()
	
	# Ensure PIN is unique
	while db.query(SessionModel).filter(SessionModel.pin_code == pin_code).first():
		pin_code = generate_pin_code()
    
	# Store the session in database
	db_session = SessionModel(
		session_id=session_id,
		pin_code=pin_code,
		user_name=user_name,
		is_active=False,
		expires_at=datetime.utcnow() + timedelta(hours=1)
	)
	db.add(db_session)
	db.commit()
	db.refresh(db_session)
    
	return {
		"session_id": session_id,
		"pin_code": pin_code
	}

@app.post("/join_by_pin")
async def join_by_pin(pin_code: str = Form(...), db: Session = Depends(get_db)):
	"""Join session using PIN code."""
	db_session = db.query(SessionModel).filter(SessionModel.pin_code == pin_code).first()
	
	if not db_session:
		raise HTTPException(status_code=404, detail="Invalid PIN code")
	
	if db_session.expires_at < datetime.utcnow():
		raise HTTPException(status_code=410, detail="Session expired")
	
	# Update session to indicate mobile client is joining
	db_session.updated_at = datetime.utcnow()
	db.commit()
	
	return {
		"session_id": db_session.session_id,
		"user_name": db_session.user_name
	}

@app.websocket("/ws/{session_id}/{client_type}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, client_type: str):
	"""Handle WebSocket connections for both desktop and mobile clients."""
	# Check if session exists in database
	db = next(get_db())
	db_session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
	
	if not db_session:
		try:
			await websocket.close(code=1008, reason="Session not found")
		except:
			pass
		finally:
			db.close()
		return
    
	# Accept the connection
	await websocket.accept()
	
	# Update session as active
	db_session.is_active = True
	db_session.updated_at = datetime.utcnow()
	db.commit()
    
	# Initialize the session entry in active_connections if it doesn't exist
	if session_id not in active_connections:
		active_connections[session_id] = {"mobile": None, "desktop": None}
    
	# Store the WebSocket connection
	active_connections[session_id][client_type] = websocket
    
	# Log connection message
	message = Message(
		session_id=session_id,
		message_type='system',
		content=f'{client_type} connected',
		sender='system'
	)
	db.add(message)
	db.commit()
    
	# Notify other clients
	if client_type == "mobile":
		desktop_ws = active_connections[session_id].get("desktop")
		if desktop_ws:
			try:
				await desktop_ws.send_text("mobile_connected")
			except:
				pass
	elif client_type == "desktop":
		mobile_ws = active_connections[session_id].get("mobile")
		if mobile_ws:
			try:
				await mobile_ws.send_text("desktop_connected")
			except:
				pass
    
	try:
		while True:
			# Handle both text and binary messages
			try:
				# Try to receive text first
				data = await websocket.receive_text()
				
				# Check if it's JSON (for special messages)
				try:
					json_data = json.loads(data)
					if json_data.get("type") == "audio_chunk":
						# Send immediate "processing" feedback to mobile (minimal JSON)
						mobile_ws = active_connections.get(session_id, {}).get("mobile")
						if mobile_ws:
							try:
								# Ultra-minimal JSON for speed
								await mobile_ws.send_text('{"t":"p"}')  # type: processing
							except:
								pass
						
						# Handle audio data sent as base64
						audio_data = base64.b64decode(json_data.get("data", ""))
						
						# Process audio (fast transcription)
						transcription = await transcribe_audio(audio_data)
						if transcription.strip() and len(transcription.strip()) > 5:  # Only process meaningful audio
							# Quick check if this sounds like a question
							is_question = any(word in transcription.lower() for word in [
								'?', 'what', 'how', 'why', 'when', 'where', 'who', 'which', 
								'can you', 'could you', 'would you', 'do you', 'are you',
								'tell me', 'explain', 'describe', 'talk about'
							])
							
							if is_question or len(transcription.strip()) > 20:  # Process questions or longer statements
								# Save question to database
								question_msg = Message(
									session_id=session_id,
									message_type="question",
									content=transcription,
									sender="desktop"
								)
								db.add(question_msg)
								db.commit()
								
								# Generate context-aware AI response with scoring
								ai_result = await generate_ai_response_with_context(transcription, session_id, db)
								
								# Save AI response to database
								response_msg = Message(
									session_id=session_id,
									message_type="answer",
									content=ai_result["response"],
									sender="ai",
									ai_score=ai_result["score"],
									ai_feedback=ai_result["feedback"]
								)
								db.add(response_msg)
								db.commit()
								
								# Send enhanced AI response to mobile device
								if mobile_ws:
									try:
										# Enhanced JSON with scoring
										enhanced_response = {
											"t": "r",  # type: response
											"q": transcription[:50],
											"a": ai_result["response"],
											"s": ai_result["score"],  # score
											"f": ai_result["feedback"][:100],  # feedback (truncated)
											"src": ai_result["source"]  # cache source
										}
										await mobile_ws.send_text(json.dumps(enhanced_response))
									except Exception as e:
										print(f"WebSocket send error: {e}")
										pass
						continue
				except json.JSONDecodeError:
					# Regular text message, continue with normal flow
					pass
				
				# Store regular message in database
				message = Message(
					session_id=session_id,
					message_type='prompt',
					content=data,
					sender=client_type
				)
				db.add(message)
				db.commit()
				
				# Broadcast to other client
				other_client = "mobile" if client_type == "desktop" else "desktop"
				other_ws = active_connections.get(session_id, {}).get(other_client)
				if other_ws:
					try:
						await other_ws.send_text(data)
					except:
						pass
						
			except Exception as e:
				print(f"WebSocket message error: {e}")
				break
                    
	except WebSocketDisconnect:
		pass
	finally:
		# Cleanup connection
		if session_id in active_connections:
			if active_connections[session_id].get(client_type) == websocket:
				active_connections[session_id][client_type] = None
		
		# Log disconnection
		disconnect_message = Message(
			session_id=session_id,
			message_type='system',
			content=f'{client_type} disconnected',
			sender='system'
		)
		db.add(disconnect_message)
		db.commit()
		
		# Notify other clients
		if client_type == "mobile":
			desktop_ws = active_connections.get(session_id, {}).get("desktop")
			if desktop_ws:
				try:
					await desktop_ws.send_text("mobile_disconnected")
				except:
					pass
		
		db.close()

@app.get("/join", response_class=HTMLResponse)
async def get_pin_entry_page(request: Request):
	"""Serve the PIN entry page for mobile users."""
	return templates.TemplateResponse("pin_entry.html", {"request": request})

@app.get("/mobile", response_class=HTMLResponse)
async def get_mobile_client(request: Request, session_id: str, db: Session = Depends(get_db)):
	"""Serve the mobile client page."""
	# Verify the session exists
	db_session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
	if not db_session:
		return HTMLResponse(content="<h1>Session not found!</h1>", status_code=404)
        
	return templates.TemplateResponse(
		"mobile.html",
		{
			"request": request,
			"session_id": session_id,
			"user_name": db_session.user_name
		}
	)

# Session cleanup to prevent memory leaks
async def cleanup_sessions():
	"""Clean up expired sessions to prevent memory leaks."""
	while True:
		await asyncio.sleep(3600)  # Run every hour
		db = next(get_db())
		now = datetime.utcnow()
		expired_sessions = db.query(SessionModel).filter(SessionModel.expires_at < now).all()
		
		for session in expired_sessions:
			# Remove from active connections
			if session.session_id in active_connections:
				del active_connections[session.session_id]
			# Delete from database
			db.delete(session)
		
		db.commit()
		db.close()
		
		if expired_sessions:
			print(f"Cleaned up {len(expired_sessions)} expired sessions")

VOSK_MODEL_PATH = "vosk-model-small-en-us-0.15"  # Adjust if your model folder is different
vosk_model = None
if os.path.exists(VOSK_MODEL_PATH):
	try:
		vosk_model = Model(VOSK_MODEL_PATH)
		print(f"Vosk model loaded from {VOSK_MODEL_PATH}")
	except Exception as e:
		print(f"Warning: Could not load Vosk model: {e}")
		vosk_model = None
else:
	print(f"Warning: Vosk model not found at {VOSK_MODEL_PATH}. Speech recognition will not be available.")

async def transcribe_audio(audio_data: bytes) -> str:
	"""Transcribe audio using Vosk (local, open-source) with streaming optimization"""
	if vosk_model is None:
		return "Speech recognition not available - Vosk model not loaded"
	
	try:
		# Create recognizer with smaller buffer for faster processing
		rec = KaldiRecognizer(vosk_model, 16000)
		rec.SetWords(True)  # Enable word-level timestamps for faster partial results
		
		# Convert bytes to numpy array for direct processing
		audio_np = np.frombuffer(audio_data, dtype=np.float32)
		
		# Process audio in smaller chunks for immediate results
		chunk_size = 1600  # 100ms chunks at 16kHz
		transcript_parts = []
		
		for i in range(0, len(audio_np), chunk_size):
			chunk = audio_np[i:i + chunk_size]
			
			# Convert to int16 PCM format
			chunk_int16 = (chunk * 32767).astype(np.int16).tobytes()
			
			if rec.AcceptWaveform(chunk_int16):
				result = json.loads(rec.Result())
				if result.get("text"):
					transcript_parts.append(result["text"])
			else:
				# Get partial results for real-time feedback
				partial = json.loads(rec.PartialResult())
				if partial.get("partial"):
					# Return partial results immediately for millisecond response
					return partial["partial"]
		
		# Get final result
		final_result = json.loads(rec.FinalResult())
		if final_result.get("text"):
			transcript_parts.append(final_result["text"])
		
		return " ".join(transcript_parts).strip()
	except Exception as e:
		print(f"Transcription error: {e}")
		return ""

async def get_conversation_context(session_id: str, db: Session) -> str:
	"""Get recent conversation history for context awareness."""
	recent_messages = db.query(Message).filter(
		Message.session_id == session_id,
		Message.message_type.in_(['question', 'answer'])
	).order_by(Message.timestamp.desc()).limit(6).all()
	
	if not recent_messages:
		return ""
	
	context_parts = []
	for msg in reversed(recent_messages):  # Reverse to get chronological order
		role = "Q" if msg.message_type == "question" else "A"
		context_parts.append(f"{role}: {msg.content[:100]}")  # Limit length
	
	return "\n".join(context_parts)

async def check_dynamic_cache(session_id: str, question_hash: str, db: Session) -> str:
	"""Check user-specific dynamic cache."""
	cached = db.query(QuestionCache).filter(
		QuestionCache.session_id == session_id,
		QuestionCache.question_hash == question_hash
	).first()
	
	if cached:
		# Update usage stats
		cached.usage_count += 1
		cached.last_used = datetime.utcnow()
		db.commit()
		return cached.response_text
	
	return None

async def generate_ai_response_with_context(transcription: str, session_id: str, db: Session) -> dict:
	"""Generate AI response with context awareness and scoring."""
	try:
		transcription_lower = transcription.lower().strip()
		question_hash = hash_question(transcription)
		
		# 1. Check static cache first (fastest)
		for cached_question, cached_response in RESPONSE_CACHE.items():
			if cached_question in transcription_lower:
				return {
					"response": cached_response,
					"score": 9.0,
					"feedback": "Quick cached response",
					"source": "static_cache"
				}
		
		# 2. Check dynamic user cache
		dynamic_response = await check_dynamic_cache(session_id, question_hash, db)
		if dynamic_response:
			return {
				"response": dynamic_response,
				"score": 8.5,
				"feedback": "Personalized cached response",
				"source": "dynamic_cache"
			}
		
		# 3. Generate new response with context
		context = await get_conversation_context(session_id, db)
		
		model = genai.GenerativeModel('gemini-pro')
		
		# Context-aware prompt with scoring
		if context:
			prompt = f"""Previous conversation:
{context}

Current question: "{transcription}"

Provide a brief 5-8 word coaching tip and rate the question quality 1-10.
Format: RESPONSE: [tip] | SCORE: [number] | FEEDBACK: [reason]"""
		else:
			prompt = f"""Interview question: "{transcription}"

Provide a brief 5-8 word coaching tip and rate the question quality 1-10.
Format: RESPONSE: [tip] | SCORE: [number] | FEEDBACK: [reason]"""
		
		generation_config = genai.types.GenerationConfig(
			max_output_tokens=50,
			temperature=0.2,
			top_p=0.8,
			top_k=15
		)
		
		response = model.generate_content(prompt, generation_config=generation_config)
		response_text = response.text.strip()
		
		# Parse structured response
		try:
			parts = response_text.split(" | ")
			ai_response = parts[0].replace("RESPONSE: ", "").strip()
			score = float(parts[1].replace("SCORE: ", "").strip())
			feedback = parts[2].replace("FEEDBACK: ", "").strip()
		except:
			# Fallback if parsing fails
			ai_response = response_text[:50] if response_text else "Focus on key points"
			score = 7.0
			feedback = "Generated response"
		
		# Cache the response for future use
		cache_entry = QuestionCache(
			session_id=session_id,
			question_hash=question_hash,
			question_text=transcription,
			response_text=ai_response,
			usage_count=1,
			last_used=datetime.utcnow()
		)
		db.add(cache_entry)
		db.commit()
		
		return {
			"response": ai_response,
			"score": min(10.0, max(1.0, score)),  # Ensure score is 1-10
			"feedback": feedback,
			"source": "ai_generated"
		}
		
	except Exception as e:
		print(f"AI response error: {e}")
		return {
			"response": "Be specific and confident!",
			"score": 5.0,
			"feedback": "Default response due to error",
			"source": "error_fallback"
		}

# Legacy function for backward compatibility
async def generate_ai_response(transcription: str) -> str:
	"""Legacy function - generates simple response without context."""
	try:
		transcription_lower = transcription.lower().strip()
		
		for cached_question, cached_response in RESPONSE_CACHE.items():
			if cached_question in transcription_lower:
				return cached_response
		
		model = genai.GenerativeModel('gemini-pro')
		prompt = f"""Q: "{transcription}"\nA: """
		
		generation_config = genai.types.GenerationConfig(
			max_output_tokens=15,
			temperature=0.1,
			top_p=0.8,
			top_k=10
		)
		
		response = model.generate_content(prompt, generation_config=generation_config)
		return response.text.strip()
	except Exception as e:
		print(f"AI response error: {e}")
		return "Be specific and confident!"

# Start cleanup task when app starts
@app.on_event("startup")
async def startup_event():
	asyncio.create_task(cleanup_sessions())
	print("Interview Assistant started with session cleanup enabled")

if __name__ == "__main__":
	import uvicorn
	uvicorn.run(app, host="0.0.0.0", port=8000)
