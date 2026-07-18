from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Toggle setups
    desktop_enabled = Column(Boolean, default=True)
    email_enabled = Column(Boolean, default=True)
    email_recipient = Column(String, nullable=True) # Send e-mail warnings to this target
    fcm_enabled = Column(Boolean, default=False)
    fcm_token = Column(String, nullable=True) # FCM registration tokens

    employee = relationship("User", back_populates="settings")

class AlertLog(Base):
    __tablename__ = "alert_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    type = Column(String, nullable=False) # e.g. "idle", "phone", "system"
    channel = Column(String, nullable=False) # e.g. "desktop", "email", "fcm"
    timestamp = Column(DateTime, default=datetime.utcnow)

    employee = relationship("User", back_populates="alert_logs")
