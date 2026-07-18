from typing import Optional
from pydantic import BaseModel

class CameraBase(BaseModel):
    name: str
    type: str # "usb" or "rtsp"
    source: str
    user_id: Optional[int] = None

class CameraCreate(CameraBase):
    pass

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    user_id: Optional[int] = None

class CameraResponse(CameraBase):
    id: int
    status: str

    class Config:
        from_attributes = True
