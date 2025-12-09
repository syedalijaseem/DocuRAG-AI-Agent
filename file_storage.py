"""File storage abstraction for S3.

This module provides functions for uploading and downloading files to/from AWS S3.
Configured via environment variables.
"""
import os
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
import uuid


def get_s3_client():
    """Get a configured S3 client."""
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION', 'us-east-2')
    )


def get_bucket_name() -> str:
    """Get the S3 bucket name from environment."""
    bucket = os.getenv('AWS_S3_BUCKET')
    if not bucket:
        raise ValueError("AWS_S3_BUCKET environment variable not set")
    return bucket


def upload_file(file_content: bytes, original_filename: str, prefix: str = "") -> dict:
    """Upload a file to S3.
    
    Args:
        file_content: The file content as bytes
        original_filename: Original filename for extension detection
        prefix: Optional folder prefix (e.g., "chats/chat_123/" or "projects/proj_456/")
    
    Returns:
        dict with s3_key, bucket, and url
    """
    s3 = get_s3_client()
    bucket = get_bucket_name()
    
    # Generate unique key to avoid collisions
    ext = Path(original_filename).suffix
    unique_id = uuid.uuid4().hex[:8]
    filename_base = Path(original_filename).stem
    s3_key = f"{prefix}{filename_base}_{unique_id}{ext}"
    
    try:
        s3.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=file_content,
            ContentType='application/pdf'  # Adjust based on file type
        )
        
        return {
            "s3_key": s3_key,
            "bucket": bucket,
            "url": f"s3://{bucket}/{s3_key}",
            "filename": original_filename
        }
    except ClientError as e:
        raise RuntimeError(f"Failed to upload to S3: {e}")


def download_file(s3_key: str) -> bytes:
    """Download a file from S3.
    
    Args:
        s3_key: The S3 object key
    
    Returns:
        File content as bytes
    """
    s3 = get_s3_client()
    bucket = get_bucket_name()
    
    try:
        response = s3.get_object(Bucket=bucket, Key=s3_key)
        return response['Body'].read()
    except ClientError as e:
        raise RuntimeError(f"Failed to download from S3: {e}")


def download_to_temp(s3_key: str) -> str:
    """Download a file from S3 to a temporary local path.
    
    Useful for processing files that need local access (like PDF parsing).
    
    Args:
        s3_key: The S3 object key
    
    Returns:
        Path to the temporary file
    """
    import tempfile
    
    content = download_file(s3_key)
    
    # Get original extension from s3_key
    ext = Path(s3_key).suffix
    
    # Create temp file
    fd, temp_path = tempfile.mkstemp(suffix=ext)
    with os.fdopen(fd, 'wb') as f:
        f.write(content)
    
    return temp_path


def delete_file(s3_key: str) -> bool:
    """Delete a file from S3.
    
    Args:
        s3_key: The S3 object key
    
    Returns:
        True if deleted successfully
    """
    s3 = get_s3_client()
    bucket = get_bucket_name()
    
    try:
        s3.delete_object(Bucket=bucket, Key=s3_key)
        return True
    except ClientError as e:
        raise RuntimeError(f"Failed to delete from S3: {e}")


def list_files(prefix: str = "") -> list[dict]:
    """List files in S3 with a given prefix.
    
    Args:
        prefix: The S3 key prefix (e.g., "chats/chat_123/")
    
    Returns:
        List of dicts with key, size, and last_modified
    """
    s3 = get_s3_client()
    bucket = get_bucket_name()
    
    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        
        files = []
        for obj in response.get('Contents', []):
            files.append({
                "key": obj['Key'],
                "size": obj['Size'],
                "last_modified": obj['LastModified'].isoformat()
            })
        return files
    except ClientError as e:
        raise RuntimeError(f"Failed to list S3 objects: {e}")
