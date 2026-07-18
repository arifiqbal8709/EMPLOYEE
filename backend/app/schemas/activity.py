from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class KeyboardMouseActivityBase(BaseModel):
    user_id: int
    keyboard_strokes: int
    mouse_clicks: int

class KeyboardMouseActivityCreate(KeyboardMouseActivityBase):
    pass

class KeyboardMouseActivityResponse(KeyboardMouseActivityBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

class ProductivityLogBase(BaseModel):
    user_id: int
    camera_id: Optional[int] = None
    score: int
    is_present: bool
    looking_at_monitor: bool
    sleeping: bool
    phone_detected: bool
    keyboard_active: bool
    mouse_active: bool

class ProductivityLogCreate(ProductivityLogBase):
    pass

class ProductivityLogResponse(ProductivityLogBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True
