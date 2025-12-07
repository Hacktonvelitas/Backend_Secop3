from typing import Optional
from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    email: EmailStr
    nombre_completo: Optional[str] = None
    empresa_nit: Optional[str] = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None
    nombre_completo: Optional[str] = None
    empresa_nit: Optional[str] = None
    is_active: Optional[bool] = None

class UserInDB(UserBase):
    id: int
    password_hash: str
    
    class Config:
        from_attributes = True

class UserResponse(UserBase):
    id: int
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
