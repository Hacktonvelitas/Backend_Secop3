from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.services.auth_service import AuthService
from app.schemas.user import UserCreate, UserOut, Token

router = APIRouter()

@router.post("/login", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    auth_service = AuthService(db)
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    return auth_service.create_token_for_user(user)

@router.post("/register", response_model=UserOut)
def register_user(
    user_in: UserCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    Create new user without the need to be logged in
    """
    auth_service = AuthService(db)
    try:
        user = auth_service.register_user(user_in)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
