from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from azure.storage.blob import BlobServiceClient


@dataclass(frozen=True)
class BlobSyncResult:
    uploaded: int = 0
    skipped_existing: int = 0
    failed: int = 0


class AzureBlobSyncClient:
    def __init__(self, *, connection_string: str, container: str) -> None:
        self._service = BlobServiceClient.from_connection_string(connection_string)
        self._container = self._service.get_container_client(container)

    def ensure_container(self) -> None:
        self._container.create_container()

    def upload_file_if_missing(
        self,
        *,
        local_path: Path,
        blob_path: str,
    ) -> bool:
        blob = self._container.get_blob_client(blob_path)
        if blob.exists():
            return False

        with local_path.open("rb") as handle:
            blob.upload_blob(handle, overwrite=False)
        return True


def collect_files(
    *,
    files: Iterable[Path],
    directories: Iterable[Path],
    globs: Iterable[str],
    source_root: Path,
    extensions: tuple[str, ...],
) -> list[Path]:
    candidates: set[Path] = set()

    for file_path in files:
        if file_path.is_file() and file_path.suffix.lower() in extensions:
            candidates.add(file_path.resolve())

    for directory in directories:
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix.lower() in extensions:
                candidates.add(path.resolve())

    for pattern in globs:
        for path in source_root.glob(pattern):
            if path.is_file() and path.suffix.lower() in extensions:
                candidates.add(path.resolve())

    return sorted(candidates)


def to_blob_path(
    *,
    local_file: Path,
    blob_prefix: str,
    preserve_paths: bool = False,
    source_root: Path | None = None,
) -> str:
    """Build the blob object key for a local file.

    By default only the filename is used under ``blob_prefix``, e.g.
    ``inventory/inventory_2026-07-11.csv``. Pass ``preserve_paths=True`` to
    keep directory structure relative to ``source_root``.
    """
    if preserve_paths:
        if source_root is None:
            raise ValueError("source_root is required when preserve_paths=True")
        relative = local_file.resolve().relative_to(source_root.resolve())
        rel_posix = relative.as_posix()
    else:
        rel_posix = local_file.name

    prefix = blob_prefix.strip("/")
    if not prefix:
        return rel_posix
    return f"{prefix}/{rel_posix}"
