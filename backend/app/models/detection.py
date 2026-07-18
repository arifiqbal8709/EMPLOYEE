from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON
from backend.app.core.database import Base

class CameraDetection(Base):
    __tablename__ = "camera_detections"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    detections_json = Column(JSON, nullable=False)
