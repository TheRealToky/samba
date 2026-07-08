"""Artifact storage for the training->inference handoff.

Writes joblib artifacts to the shared model dir (a volume locally) and also
pushes them to object storage (MinIO/S3), which is the cloud-faithful handoff
per the deployment diagram. Inference loads from the model dir.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import settings


def save_artifact(name: str, obj: Any) -> str:
    import joblib

    model_dir = Path(settings.model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    path = model_dir / f"{name}.joblib"
    joblib.dump(obj, path)
    _push_to_object_storage(path, f"models/{name}.joblib")
    return str(path)


def _push_to_object_storage(local_path: Path, key: str) -> None:
    try:
        import boto3
        from botocore.client import Config

        s3 = boto3.client(
            "s3",
            endpoint_url=f"http://{settings.minio_endpoint}",
            aws_access_key_id=settings.minio_root_user,
            aws_secret_access_key=settings.minio_root_password,
            config=Config(signature_version="s3v4"),
        )
        s3.upload_file(str(local_path), settings.minio_bucket, key)
        print(f"[storage] pushed {key} to object storage", flush=True)
    except Exception as exc:  # best-effort; the volume is the source of truth locally
        print(f"[storage] object-storage push skipped: {exc}", flush=True)
