from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False) # "usb" or "rtsp"
    source = Column(String, nullable=False) # e.g. "0" or RTSP link
    status = Column(String, default="disconnected") # "connected", "disconnected", "error"
    
    # Linked employee
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Database relationships
    employee = relationship("User", back_populates="cameras")
    productivity_logs = relationship("ProductivityLog", back_populates="camera")
