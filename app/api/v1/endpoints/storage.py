from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.storage_service import StorageService

router = APIRouter()

@router.post("/upload")
def upload_file(
    file: UploadFile = File(...),
    encrypt: bool = True
):
    """
    Upload a file to S3 (MinIO). Encrypts by default.
    """
    service = StorageService()
    object_name = service.upload_file(file, encrypt=encrypt)
    
    if not object_name:
        raise HTTPException(status_code=500, detail="Failed to upload file")
        
    return {"filename": file.filename, "s3_key": object_name, "encrypted": encrypt}

@router.get("/url/{object_name:path}")
def get_file_url(object_name: str):
    """
    Get a presigned URL for a file.
    """
    service = StorageService()
    url = service.generate_presigned_url(object_name)
    
    if not url:
        raise HTTPException(status_code=404, detail="File not found or error generating URL")
        
    return {"url": url}
