#!/usr/bin/env python3
"""Upload local files to Azure Blob Storage without duplicating existing blobs."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generator.utils.azure_blob_sync import (  # noqa: E402
    AzureBlobSyncClient,
    BlobSyncResult,
    collect_files,
    to_blob_path,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync local CSV files to Azure Blob Storage (upload only missing blobs)."
    )
    parser.add_argument(
        "--file",
        action="append",
        default=[],
        help="Single file path to upload. Can be passed multiple times.",
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="Directory path to scan recursively for files. Can be passed multiple times.",
    )
    parser.add_argument(
        "--glob",
        action="append",
        default=[],
        help="Glob pattern relative to --source-root (e.g. 'output/wms/**/*.csv').",
    )
    parser.add_argument(
        "--source-root",
        default=".",
        help="Base path for --preserve-paths mode. Ignored by default (flat upload).",
    )
    parser.add_argument(
        "--preserve-paths",
        action="store_true",
        help="Keep local directory structure under --blob-prefix (off by default).",
    )
    parser.add_argument(
        "--blob-prefix",
        default="",
        help="Optional blob folder prefix (e.g. 'raw').",
    )
    parser.add_argument(
        "--container",
        required=True,
        help="Azure Blob container name.",
    )
    parser.add_argument(
        "--connection-string",
        default="",
        help="Azure Storage connection string. If omitted, uses AZURE_STORAGE_CONNECTION_STRING.",
    )
    parser.add_argument(
        "--extensions",
        default=".csv",
        help="Comma-separated file extensions to sync. Default: .csv",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview files and blob paths without uploading.",
    )
    return parser


def parse_extensions(raw_extensions: str) -> tuple[str, ...]:
    extensions: list[str] = []
    for item in raw_extensions.split(","):
        ext = item.strip().lower()
        if not ext:
            continue
        if not ext.startswith("."):
            ext = f".{ext}"
        extensions.append(ext)
    return tuple(extensions or [".csv"])


def sync_files(args: argparse.Namespace) -> BlobSyncResult:
    source_root = Path(args.source_root).resolve()
    file_paths = [Path(item).resolve() for item in args.file]
    directories = [Path(item).resolve() for item in args.path]
    extensions = parse_extensions(args.extensions)

    files_to_sync = collect_files(
        files=file_paths,
        directories=directories,
        globs=args.glob,
        source_root=source_root,
        extensions=extensions,
    )

    if not files_to_sync:
        print("No matching files found to sync.")
        return BlobSyncResult()

    connection_string = args.connection_string or ""
    if not connection_string:
        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "").strip()
    if not connection_string:
        raise ValueError(
            "Missing connection string. Pass --connection-string or set "
            "AZURE_STORAGE_CONNECTION_STRING."
        )

    if args.dry_run:
        print(f"Dry run: {len(files_to_sync)} file(s) matched.")
        for local_path in files_to_sync:
            blob_path = to_blob_path(
                local_file=local_path,
                blob_prefix=args.blob_prefix,
                preserve_paths=args.preserve_paths,
                source_root=source_root,
            )
            print(f"  - {local_path} -> {args.container}/{blob_path}")
        return BlobSyncResult()

    client = AzureBlobSyncClient(
        connection_string=connection_string,
        container=args.container,
    )
    result = BlobSyncResult()

    for local_path in files_to_sync:
        try:
            blob_path = to_blob_path(
                local_file=local_path,
                blob_prefix=args.blob_prefix,
                preserve_paths=args.preserve_paths,
                source_root=source_root,
            )
            uploaded = client.upload_file_if_missing(
                local_path=local_path,
                blob_path=blob_path,
            )
            if uploaded:
                result = BlobSyncResult(
                    uploaded=result.uploaded + 1,
                    skipped_existing=result.skipped_existing,
                    failed=result.failed,
                )
                print(f"Uploaded: {local_path} -> {args.container}/{blob_path}")
            else:
                result = BlobSyncResult(
                    uploaded=result.uploaded,
                    skipped_existing=result.skipped_existing + 1,
                    failed=result.failed,
                )
                print(f"Skipped (exists): {args.container}/{blob_path}")
        except Exception as exc:  # pragma: no cover - runtime/environment specific
            result = BlobSyncResult(
                uploaded=result.uploaded,
                skipped_existing=result.skipped_existing,
                failed=result.failed + 1,
            )
            print(f"Failed: {local_path} ({exc})")

    return result


def main() -> None:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()

    if not args.file and not args.path and not args.glob:
        parser.error("Provide at least one of --file, --path, or --glob.")

    result = sync_files(args)
    print("")
    print("Sync summary")
    print(f"  uploaded: {result.uploaded}")
    print(f"  skipped_existing: {result.skipped_existing}")
    print(f"  failed: {result.failed}")


if __name__ == "__main__":
    main()
