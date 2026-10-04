"""Object storage: local directory (default) or S3-compatible (MinIO in docker compose)."""

from __future__ import annotations

from pathlib import Path

from .settings import get_settings


class LocalStorage:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if self.root.resolve() not in p.parents:
            raise ValueError("invalid storage key")
        return p

    def put(self, key: str, data: bytes, content_type: str | None = None) -> str:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return key

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()


class S3Storage:
    def __init__(self, endpoint: str | None, bucket: str, access: str, secret: str):
        import boto3

        self.bucket = bucket
        self.s3 = boto3.client("s3", endpoint_url=endpoint, aws_access_key_id=access,
                               aws_secret_access_key=secret)
        try:
            self.s3.head_bucket(Bucket=bucket)
        except Exception:  # noqa: BLE001 - create on first use
            self.s3.create_bucket(Bucket=bucket)

    def put(self, key: str, data: bytes, content_type: str | None = None) -> str:
        extra = {"ContentType": content_type} if content_type else {}
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=data, **extra)
        return key

    def get(self, key: str) -> bytes:
        return self.s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def exists(self, key: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:  # noqa: BLE001
            return False


_storage = None


def get_storage():
    global _storage
    if _storage is None:
        s = get_settings()
        if s.storage_backend == "s3":
            _storage = S3Storage(s.s3_endpoint_url, s.s3_bucket,
                                 s.s3_access_key.get_secret_value(),
                                 s.s3_secret_key.get_secret_value())
        else:
            _storage = LocalStorage(s.storage_dir)
    return _storage


def reset_storage() -> None:
    global _storage
    _storage = None
