from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class NotificationSettingsBase(BaseModel):
    desktop_enabled: Optional[bool] = True
    email_enabled: Optional[bool] = True
    email_recipient: Optional[str] = None
    fcm_enabled: Optional[bool] = False
    fcm_token: Optional[str] = None

class NotificationSettingsUpdate(BaseModel):
    desktop_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    email_recipient: Optional[str] = None
    fcm_enabled: Optional[bool] = None
    fcm_token: Optional[str] = None

class NotificationSettingsResponse(NotificationSettingsBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True

class AlertLogBase(BaseModel):
    user_id: int
    title: str
    message: str
    type: str # "idle", "phone", "system"
    channel: str # "desktop", "email", "fcm"

class AlertLogCreate(AlertLogBase):
    pass

class AlertLogResponse(AlertLogBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True
