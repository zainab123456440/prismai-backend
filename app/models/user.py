from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional

# --- Request Models (what frontend sends) ---

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str

    @field_validator('password')
    @classmethod
    def truncate_password(cls, v: str) -> str:
        # Bcrypt (used by Supabase) has a 72-byte limit
        # We encode to bytes, slice, then decode back to string
        return v.encode('utf-8')[:72].decode('utf-8', 'ignore')

class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator('password')
    @classmethod
    def truncate_password(cls, v: str) -> str:
        return v.encode('utf-8')[:72].decode('utf-8', 'ignore')

# --- Response Models (what backend returns) ---

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# --- Internal Model (used inside the app) ---

class CurrentUser(BaseModel):
    id: str
    email: str
    full_name: str