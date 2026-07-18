from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class KeyboardMouseActivity(Base):
    __tablename__ = "kb_mouse_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    keyboard_strokes = Column(Integer, default=0)
    mouse_clicks = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    employee = relationship("User", back_populates="kb_mouse_activities")

class ProductivityLog(Base):
    __tablename__ = "productivity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True)
    
    # 0 to 100 focal metrics score
    score = Column(Integer, nullable=False)
    
    # Detailed flags supporting score calculations
    is_present = Column(Boolean, default=True)
    looking_at_monitor = Column(Boolean, default=True)
    sleeping = Column(Boolean, default=False)
    phone_detected = Column(Boolean, default=False)
    keyboard_active = Column(Boolean, default=False)
    mouse_active = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    employee = relationship("User", back_populates="productivity_logs")
    camera = relationship("Camera", back_populates="productivity_logs")
