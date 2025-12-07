from typing import Optional
from sqlalchemy.orm import Session
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserCreate, Token
from app.core.security import verify_password, create_access_token
from app.models.user import Usuario

class AuthService:
    def __init__(self, session: Session):
        self.session = session
        self.user_repo = UserRepository(session)

    def authenticate_user(self, email: str, password: str) -> Optional[Usuario]:
        user = self.user_repo.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def register_user(self, user_in: UserCreate) -> Usuario:
        if self.user_repo.get_by_email(user_in.email):
            raise ValueError("Email already registered")
        
        user = self.user_repo.create(user_in)
        self.session.commit()
        return user

    def create_token_for_user(self, user: Usuario) -> Token:
        access_token = create_access_token(subject=user.id)
        return Token(access_token=access_token, token_type="bearer")
