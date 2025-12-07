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
            # Validate against companies table
            company = self.empresa_repo.get_vector_data(user_in.empresa_nit)
            if not company:
                raise ValueError(f"Empresa with NIT {user_in.empresa_nit} does not exist in companies registry")
            
            # Generate embeddings for company fields if they exist and are missing embeddings
            # We do this here to ensure the company is "ready" for matching
            from app.services.embedding_service import EmbeddingService
            embedding_service = EmbeddingService()
            
            updates = {}
            
            # Helper to update embedding if field exists and embedding is missing
            def update_if_needed(field_val, current_embedding, field_name):
                if field_val and not current_embedding:
                    emb = embedding_service.generate_embedding(field_val)
                    if emb:
                        updates[field_name] = emb

            update_if_needed(company.razon_social, company.razon_social_embedding, "razon_social_embedding")
            update_if_needed(company.ciiu1, company.ciiu1_embedding, "ciiu1_embedding")
            update_if_needed(company.ciiu2, company.ciiu2_embedding, "ciiu2_embedding")
            update_if_needed(company.ciiu3, company.ciiu3_embedding, "ciiu3_embedding")
            update_if_needed(company.ciiu4, company.ciiu4_embedding, "ciiu4_embedding")
            
            if updates:
                # We need a method in repo to update company directly, or use session here
                for k, v in updates.items():
                    setattr(company, k, v)
                self.session.add(company)
                self.session.flush()

        user = self.user_repo.create(user_in)
        self.session.commit()
        return user

    def create_token_for_user(self, user: Usuario) -> Token:
        access_token = encode_jwt(payload={"sub": str(user.id)}, minutes=60)
        return Token(access_token=access_token, token_type="bearer")
