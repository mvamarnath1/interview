import os
from sqlalchemy import create_engine, Column, String, DateTime, Text, Boolean, Integer, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import uuid
from datetime import datetime

# Database configuration with environment variable support
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./interview_assistant.db")

# Configure engine based on database type
if "sqlite" in DATABASE_URL:
    # SQLite configuration for development
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=os.getenv("DEBUG", "false").lower() == "true"
    )
elif "postgresql" in DATABASE_URL:
    # PostgreSQL configuration for production
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=os.getenv("DEBUG", "false").lower() == "true"
    )
else:
    # Fallback generic configuration
    engine = create_engine(
        DATABASE_URL,
        echo=os.getenv("DEBUG", "false").lower() == "true"
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, unique=True, nullable=False, index=True)
    pin_code = Column(String(6), unique=True, nullable=False, index=True)  # NEW: 6-digit PIN
    user_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False, index=True)
    message_type = Column(String, nullable=False)  # 'question', 'answer', 'system'
    content = Column(Text, nullable=False)
    sender = Column(String, nullable=False)  # 'desktop', 'mobile', 'system'
    timestamp = Column(DateTime, default=datetime.utcnow)
    # NEW: AI scoring and feedback
    ai_score = Column(Float, nullable=True)  # 1-10 confidence score
    ai_feedback = Column(Text, nullable=True)  # AI feedback text

class QuestionCache(Base):
    __tablename__ = "question_cache"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False, index=True)
    question_hash = Column(String, nullable=False, index=True)  # Hash of normalized question
    question_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=False)
    usage_count = Column(Integer, default=1)
    last_used = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserProgress(Base):
    __tablename__ = "user_progress"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False, index=True)
    question_category = Column(String, nullable=False)  # 'behavioral', 'technical', 'general'
    avg_score = Column(Float, nullable=False)
    total_questions = Column(Integer, default=1)
    improvement_trend = Column(Float, default=0.0)  # Weekly improvement %
    last_updated = Column(DateTime, default=datetime.utcnow)

# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()