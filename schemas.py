from pydantic import BaseModel, EmailStr
from typing import Optional, List

# --- ESQUEMAS DE USUARIO ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "fan"

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    bio: Optional[str] = None
    role: str
    status: str
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut

# --- NUEVOS: ESQUEMAS DE PÁGINAS (HUBS) ---
class CreatorPageCreate(BaseModel):
    name: str
    description: Optional[str] = None

class CreatorPageOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    banner_url: Optional[str] = None
    total_raised: int

    class Config:
        from_attributes = True

# --- NUEVOS: ESQUEMAS DE POSTS ---
class PostOut(BaseModel):
    id: int
    title: str
    content_url: str
    uploader_id: int
    page_id: int

    class Config:
        from_attributes = True