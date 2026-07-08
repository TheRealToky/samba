"""S3-compatible object storage access (MinIO locally -> GCS/S3 in cloud)."""
from __future__ import annotations

from functools import lru_cache

from app.config import settings


@lru_cache(maxsize=1)
def _client():
    import boto3
    from botocore.client import Config

    return boto3.client(
        "s3",
        endpoint_url=f"http://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_root_user,
        aws_secret_access_key=settings.minio_root_password,
        config=Config(signature_version="s3v4"),
    )


def put_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    _client().put_object(Bucket=settings.minio_bucket, Key=key, Body=data, ContentType=content_type)
    return key


def get_bytes(key: str) -> bytes:
    obj = _client().get_object(Bucket=settings.minio_bucket, Key=key)
    return obj["Body"].read()
