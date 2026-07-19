from typing import Optional
from pydantic import BaseModel, Field, field_validator

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    role: Optional[str] = "employee"
    employee_id: Optional[str] = None
    department: Optional[str] = None
    camera_id: Optional[str] = None
    status: Optional[str] = "absent"

    @field_validator("employee_id", "department", "camera_id", mode="before")
    @classmethod
    def clean_empty_strings(cls, v):
        if isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped if v_stripped else None
        return v

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[Optional[str]] = None
    role: Optional[str] = None
    employee_id: Optional[str] = None
    department: Optional[str] = None
    camera_id: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("employee_id", "department", "camera_id", mode="before")
    @classmethod
    def clean_empty_strings(cls, v):
        if isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped if v_stripped else None
        return v

class UserResponse(UserBase):
    id: int
    role: str
    employee_id: Optional[str] = None
    department: Optional[str] = None
    camera_id: Optional[str] = None
    status: str
    is_active: bool

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None
