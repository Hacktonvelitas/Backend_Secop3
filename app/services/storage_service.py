import boto3
import logging
from botocore.exceptions import ClientError
from fastapi import UploadFile
from app.core.config import settings
from app.core.encryption import encrypt_data

LOGGER = logging.getLogger("storage_service")

class StorageService:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region
        )
        self.bucket = settings.s3_bucket

    def upload_file(self, file: UploadFile, object_name: str = None, encrypt: bool = True) -> str:
        if object_name is None:
            object_name = file.filename

        try:
            file_content = file.file.read()
            
            if encrypt:
                # Encrypt content before uploading
                file_content = encrypt_data(file_content)
                object_name = f"encrypted/{object_name}"
            
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=object_name,
                Body=file_content,
                ContentType=file.content_type
            )
            
            # Return the S3 URL (or presigned URL if private)
            # For now, returning the key
            return object_name
        except ClientError as e:
            LOGGER.error(f"Error uploading file to S3: {e}")
            return None

    def generate_presigned_url(self, object_name: str, expiration: int = 3600) -> str:
        try:
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': object_name},
                ExpiresIn=expiration
            )
            
            # If using local minio with docker, the host might be 'minio' which is not accessible from host
            # We might need to replace it with localhost or the public endpoint
            if settings.s3_public_endpoint:
                 # Simple replacement logic (naive)
                 # Assuming response starts with internal endpoint
                 if settings.s3_endpoint in response:
                     response = response.replace(settings.s3_endpoint, settings.s3_public_endpoint)
            
            return response
        except ClientError as e:
            LOGGER.error(f"Error generating presigned URL: {e}")
            return None
