"""
Storage abstraction layer.
Current backend: local filesystem.
Future: swap to S3/R2/MinIO by implementing a different backend class
and switching via STORAGE_BACKEND env var.
"""
import hashlib
import logging
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class LocalStorageBackend:
    """Private local filesystem storage. Files not accessible via public URL."""

    def _full_path(self, storage_key: str) -> Path:
        p = Path(settings.STORAGE_LOCAL_PATH) / storage_key
        # Prevent path traversal
        base = Path(settings.STORAGE_LOCAL_PATH).resolve()
        resolved = p.resolve()
        if not str(resolved).startswith(str(base)):
            raise ValueError("Invalid storage key: path traversal detected")
        return resolved

    async def store(self, content: bytes, storage_key: str) -> str:
        path = self._full_path(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        logger.info(f"Stored file: {storage_key} ({len(content)} bytes)")
        return storage_key

    async def retrieve(self, storage_key: str) -> bytes:
        path = self._full_path(storage_key)
        if not path.exists():
            raise FileNotFoundError(f"Document not found in storage: {storage_key}")
        return path.read_bytes()

    async def delete(self, storage_key: str) -> None:
        path = self._full_path(storage_key)
        if path.exists():
            path.unlink()
            logger.info(f"Deleted file: {storage_key}")


# Future: S3StorageBackend, R2StorageBackend, MinIOStorageBackend
# Swap by changing STORAGE_BACKEND env var and this instance

def get_storage_service():
    backend = settings.STORAGE_BACKEND.lower()
    if backend == "local":
        return LocalStorageBackend()
    raise ValueError(f"Unknown storage backend: {backend}")


storage = get_storage_service()


def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def make_storage_key(tenant_id: int, document_public_id: str, filename: str) -> str:
    """Generate a non-guessable storage path."""
    safe_filename = Path(filename).name  # Strip path components
    return f"{tenant_id}/{document_public_id}/{safe_filename}"
