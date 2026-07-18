from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="employee") # admin, manager, employee
    
    # Employee Management parameters
    employee_id = Column(String, unique=True, index=True, nullable=True)
    department = Column(String, nullable=True)
    camera_id = Column(String, nullable=True) # Current default camera source linked
    status = Column(String, default="absent") # active, idle, absent
    is_active = Column(Boolean, default=True)

    # Database relationships
    cameras = relationship("Camera", back_populates="employee", cascade="all, delete-orphan")
    productivity_logs = relationship("ProductivityLog", back_populates="employee", cascade="all, delete-orphan")
    kb_mouse_activities = relationship("KeyboardMouseActivity", back_populates="employee", cascade="all, delete-orphan")
    alert_logs = relationship("AlertLog", back_populates="employee", cascade="all, delete-orphan")
    settings = relationship("NotificationSettings", back_populates="employee", uselist=False, cascade="all, delete-orphan")
