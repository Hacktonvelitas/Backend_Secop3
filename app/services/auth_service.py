from typing import Optional
from sqlalchemy.orm import Session
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserCreate, Token
from app.core.security import verify_password, encode_jwt
from app.models.user import Usuario

from app.repositories.empresa_repo import EmpresaRepository

class AuthService:
    def __init__(self, session: Session):
        self.session = session
        self.user_repo = UserRepository(session)
        self.empresa_repo = EmpresaRepository(session)

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
        
        if user_in.empresa_nit:
            if not self.empresa_repo.get_by_nit(user_in.empresa_nit):
                raise ValueError(f"Empresa with NIT {user_in.empresa_nit} does not exist")
        
        user = self.user_repo.create(user_in)
        self.session.commit()
        return user

    def create_token_for_user(self, user: Usuario) -> Token:
        access_token = encode_jwt(payload={"sub": str(user.id)}, minutes=60)
        return Token(access_token=access_token, token_type="bearer")
