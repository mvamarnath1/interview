from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid
import qrcode
from io import BytesIO
import base64
import asyncio
from datetime import datetime, timedelta
import os
import tempfile
import json
from dotenv import load_dotenv
import google.generativeai as genai
import numpy as np
import wave
# Vosk imports
from vosk import Model, KaldiRecognizer
import soundfile as sf
from .database import get_db, create_tables, Session as SessionModel, Message

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

@app.get("/", response_class=HTMLResponse)
async def get_control_panel(request: Request):
	"""Serve the main control panel page."""
	return templates.TemplateResponse("index.html", {"request": request})

@app.post("/create_session")
async def create_session(user_name: str = Form(...), db: Session = Depends(get_db)):
	"""Create a new session and generate a QR code."""
	# Generate a unique session ID
	session_id = str(uuid.uuid4())
    
	# Create URL for the mobile client to connect to
	join_url = f"http://localhost:8000/mobile?session_id={session_id}"
    
	# Generate QR Code
	qr = qrcode.QRCode(version=1, box_size=10, border=5)
	qr.add_data(join_url)
	qr.make(fit=True)
	img = qr.make_image(fill_color="black", back_color="white")
    
	# Save QR code to a bytes buffer and encode it in base64 for HTML
	buffered = BytesIO()
	img.save(buffered, format="PNG")
	img_str = base64.b64encode(buffered.getvalue()).decode()
    
	# Store the session in database
	db_session = SessionModel(
		session_id=session_id,
		user_name=user_name,
		is_active=False,
		expires_at=datetime.utcnow() + timedelta(hours=1)
	)
	db.add(db_session)
	db.commit()
	db.refresh(db_session)
    
	return {
		"session_id": session_id,
		"qr_code_data": f"data:image/png;base64,{img_str}",
		"join_url": join_url
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
								ai_response = await generate_ai_response(transcription)
								
								# Send AI response to mobile device (ultra-minimal JSON)
								if mobile_ws:
									try:
										# Compressed JSON format for millisecond transfer
										compact_response = f'{{"t":"r","q":"{transcription[:50]}","a":"{ai_response}"}}'
										await mobile_ws.send_text(compact_response)
									except:
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
if not os.path.exists(VOSK_MODEL_PATH):
	raise Exception(f"Please download the model from https://alphacephei.com/vosk/models and unpack as '{VOSK_MODEL_PATH}' in the current folder.")
vosk_model = Model(VOSK_MODEL_PATH)

async def transcribe_audio(audio_data: bytes) -> str:
	"""Transcribe audio using Vosk (local, open-source) with streaming optimization"""
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

async def generate_ai_response(transcription: str) -> str:
	"""Generate AI response with millisecond caching + Google Gemini fallback"""
	try:
		# Instant cache lookup for millisecond responses
		transcription_lower = transcription.lower().strip()
		
		# Check for exact or partial matches in cache
		for cached_question, cached_response in RESPONSE_CACHE.items():
			if cached_question in transcription_lower:
				print(f"Cache hit for: {transcription_lower}")
				return cached_response
		
		# Fallback to Gemini for uncached questions
		model = genai.GenerativeModel('gemini-pro')
		
		# Ultra-optimized prompt for millisecond responses (5-8 words max)
		prompt = f"""Q: "{transcription}"
A: """
		
		# Maximum speed settings
		generation_config = genai.types.GenerationConfig(
			max_output_tokens=15,   # Ultra-limited for 5-8 word responses
			temperature=0.1,        # Very low for instant, focused answers
			top_p=0.8,             # Focused sampling for speed
			top_k=10               # Reduced choices for faster generation
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
