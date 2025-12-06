from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- DB/Redis ---
    database_url: str = Field(..., alias="DATABASE_URL")

    # --- S3/MinIO ---
    s3_endpoint: str  = Field("http://localhost:9000", alias="S3_ENDPOINT")    
    s3_public_endpoint: str | None = Field(None, alias="S3_PUBLIC_ENDPOINT")
    s3_region: str    = Field("us-east-1", alias="S3_REGION")
    s3_bucket: str    = Field("market-images", alias="S3_BUCKET")
    s3_access_key: str = Field(..., alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(..., alias="S3_SECRET_KEY")

    # --- Auth/JWT ---
    jwt_secret: str = Field("dev-secret-change-me", alias="JWT_SECRET")
    jwt_alg: str = Field("HS256", alias="JWT_ALG")
    jwt_access_min: int = Field(30, alias="JWT_ACCESS_MIN")
    jwt_refresh_days: int = Field(30, alias="JWT_REFRESH_DAYS")

    # --- App ---
    app_env: str = Field("dev", alias="APP_ENV")

    @property
    def s3_presign_endpoint(self) -> str:
        return self.s3_public_endpoint or self.s3_endpoint

settings = Settings()