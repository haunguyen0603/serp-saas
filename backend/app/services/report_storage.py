import asyncio
from pathlib import Path
from typing import Protocol

from app.core.config import Settings


class ReportArtifactStorage(Protocol):
    async def write(self, key: str, data: bytes) -> None: ...

    async def read(self, key: str) -> bytes | None: ...

    async def delete(self, key: str) -> None: ...


class LocalReportArtifactStorage:
    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if self.root not in candidate.parents:
            raise ValueError("Invalid report storage key")
        return candidate

    async def write(self, key: str, data: bytes) -> None:
        path = self._path(key)

        def persist() -> None:
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_bytes(data)
            temporary.chmod(0o600)
            temporary.replace(path)

        await asyncio.to_thread(persist)

    async def read(self, key: str) -> bytes | None:
        path = self._path(key)

        def load() -> bytes | None:
            try:
                return path.read_bytes()
            except FileNotFoundError:
                return None

        return await asyncio.to_thread(load)

    async def delete(self, key: str) -> None:
        path = self._path(key)

        def remove() -> None:
            try:
                path.unlink()
            except FileNotFoundError:
                pass

        await asyncio.to_thread(remove)


class GCSReportArtifactStorage:
    """Private Google Cloud Storage adapter; access remains behind the API."""

    def __init__(self, project_id: str, bucket_name: str, prefix: str) -> None:
        from google.cloud import storage  # type: ignore[attr-defined]

        self.bucket = storage.Client(project=project_id or None).bucket(bucket_name)
        self.prefix = prefix.strip("/")

    def _name(self, key: str) -> str:
        if not key or key.startswith("/") or ".." in Path(key).parts:
            raise ValueError("Invalid report storage key")
        return f"{self.prefix}/{key}"

    async def write(self, key: str, data: bytes) -> None:
        blob = self.bucket.blob(self._name(key))
        await asyncio.to_thread(blob.upload_from_string, data)

    async def read(self, key: str) -> bytes | None:
        blob = self.bucket.blob(self._name(key))
        if not await asyncio.to_thread(blob.exists):
            return None
        return await asyncio.to_thread(blob.download_as_bytes)

    async def delete(self, key: str) -> None:
        blob = self.bucket.blob(self._name(key))
        if await asyncio.to_thread(blob.exists):
            await asyncio.to_thread(blob.delete)


def create_report_storage(settings: Settings) -> ReportArtifactStorage:
    if settings.report_storage_provider == "gcs":
        return GCSReportArtifactStorage(
            settings.gcp_project_id,
            settings.report_storage_bucket,
            settings.report_storage_prefix,
        )
    return LocalReportArtifactStorage(settings.report_storage_root)
