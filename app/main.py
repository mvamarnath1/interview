from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uuid
import qrcode
from io import BytesIO
import base64
import asyncio
from datetime import datetime, timedelta

# Initialize the FastAPI app
app = FastAPI(title="Interview Assistant")

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

# In-memory storage for sessions and connections
sessions = {}
# Structure: active_connections[session_id] = {"mobile": WebSocket, "desktop": WebSocket}
active_connections = {}

@app.get("/", response_class=HTMLResponse)
async def get_control_panel(request: Request):
	"""Serve the main control panel page."""
	return templates.TemplateResponse("index.html", {"request": request})

@app.post("/create_session")
async def create_session(user_name: str = Form(...)):
	"""Create a new session and generate a QR code."""
	# Generate a unique session ID
	session_id = str(uuid.uuid4())
    
	# Create URL for the mobile client to connect to
	# For now, we use localhost. In Docker, this will be the container's hostname.
	# This is the biggest challenge. We need the phone to be able to access the server.
	# Option 1: Use Ngrok to tunnel (easier for dev). 
	# Option 2: Ensure phone and laptop are on same network and use laptop's IP.
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
    
	# Store the session with expiration
	sessions[session_id] = {
		"user_name": user_name,
		"session_id": session_id,
		"is_active": False,
		"created_at": datetime.now(),
		"expires_at": datetime.now() + timedelta(hours=1)
	}
    
	return {
		"session_id": session_id,
		"qr_code_data": f"data:image/png;base64,{img_str}",
		"join_url": join_url
	}


@app.websocket("/ws/{session_id}/{client_type}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, client_type: str):
	"""Handle WebSocket connections for both desktop and mobile clients."""
	# Check if session exists
	if session_id not in sessions:
		try:
			await websocket.close(code=1008, reason="Session not found")
		except:
			pass
		return
    
	# Accept the connection
	await websocket.accept()
    
	# Initialize the session entry in active_connections if it doesn't exist
	if session_id not in active_connections:
		active_connections[session_id] = {"mobile": None, "desktop": None}
    
	# Store the connection based on its type (desktop or mobile)
	if client_type == "mobile":
		active_connections[session_id]["mobile"] = websocket
		# Send a welcome message to the mobile phone
		await websocket.send_text("Connected. Waiting for session to start...")
        
		# NOTIFY THE DESKTOP CLIENT THAT A MOBILE PHONE HAS CONNECTED
		desktop_connection = active_connections[session_id].get("desktop")
		if desktop_connection:
			try:
				await desktop_connection.send_text("mobile_connected")
			except Exception as e:
				print(f"Could not notify desktop of mobile connection: {e}")
                
	elif client_type == "desktop":
		active_connections[session_id]["desktop"] = websocket
		# Check if mobile is already connected and notify desktop immediately
		if active_connections[session_id].get("mobile"):
			try:
				await websocket.send_text("mobile_connected")
			except Exception as e:
				print(f"Could not notify new desktop connection of existing mobile: {e}")
    
	try:
		while True:
			# Keep the connection open.
			data = await websocket.receive_text()
			# You can handle messages from the client here if needed.
			# For example, if the desktop sends a "start" command, relay it to mobile.
			print(f"Received from {client_type}: {data}")
            
	except WebSocketDisconnect:
		print(f"WebSocket disconnected: {client_type}")
		# Clean up on disconnect
		if session_id in active_connections:
			if active_connections[session_id].get("mobile") == websocket:
				active_connections[session_id]["mobile"] = None
				# Notify desktop that mobile disconnected
				desktop_conn = active_connections[session_id].get("desktop")
				if desktop_conn:
					await desktop_conn.send_text("mobile_disconnected")
			elif active_connections[session_id].get("desktop") == websocket:
				active_connections[session_id]["desktop"] = None
	finally:
		# Cleanup if the connection wasn't already handled above
		if session_id in active_connections:
			if active_connections[session_id].get("mobile") == websocket:
				active_connections[session_id]["mobile"] = None
			elif active_connections[session_id].get("desktop") == websocket:
				active_connections[session_id]["desktop"] = None

@app.get("/mobile", response_class=HTMLResponse)
async def get_mobile_client(request: Request, session_id: str):
	"""Serve the mobile client page."""
	# Verify the session exists
	if session_id not in sessions:
		return HTMLResponse(content="<h1>Session not found!</h1>", status_code=404)
        
	return templates.TemplateResponse(
		"mobile.html",
		{
			"request": request,
			"session_id": session_id,
			"user_name": sessions[session_id]["user_name"]
		}
	)

# Session cleanup to prevent memory leaks
async def cleanup_sessions():
	"""Clean up expired sessions to prevent memory leaks."""
	while True:
		await asyncio.sleep(3600)  # Run every hour
		now = datetime.now()
		expired_sessions = [
			session_id for session_id, session in sessions.items()
			if session["expires_at"] < now
		]
		for session_id in expired_sessions:
			if session_id in sessions:
				del sessions[session_id]
			if session_id in active_connections:
				del active_connections[session_id]
		
		if expired_sessions:
			print(f"Cleaned up {len(expired_sessions)} expired sessions")

# Start cleanup task when app starts
@app.on_event("startup")
async def startup_event():
	asyncio.create_task(cleanup_sessions())
	print("Interview Assistant started with session cleanup enabled")

if __name__ == "__main__":
	import uvicorn
	uvicorn.run(app, host="0.0.0.0", port=8000) # host="0.0.0.0" is crucial for Docker & network access
