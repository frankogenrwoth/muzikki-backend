from __future__ import annotations

import abc
import datetime as dt
from dataclasses import dataclass
from enum import Enum
from typing import Any, BinaryIO, Dict, Iterable, IO, Optional, Literal
import hashlib
import json
import logging
import os
import time
import mimetypes


class StorageError(Exception):
    """Raised for storage-related errors that callers may want to handle."""


class ObjectStatus(Enum):
    AVAILABLE = "available"
    NOT_FOUND = "not_found"
    IN_PROGRESS = "in_progress"
    UNKNOWN = "unknown"


@dataclass
class StoredObjectInfo:
    key: str
    size_bytes: Optional[int] = None
    checksum: Optional[str] = None
    content_type: Optional[str] = None
    created_at: Optional[dt.datetime] = None
    updated_at: Optional[dt.datetime] = None
    metadata: Optional[Dict[str, str]] = None
    raw: Optional[Any] = None  # Provider-specific raw payload


@dataclass
class UploadResult:
    key: str
    etag: Optional[str] = None
    version_id: Optional[str] = None
    raw: Optional[Any] = None  # Provider-specific raw payload


@dataclass
class MediaBundleResult:
    song_id: str
    audio_key: Optional[str]
    video_key: Optional[str]
    art_key: Optional[str]
    audio_url: Optional[str]
    video_url: Optional[str]
    art_url: Optional[str]
    manifest_key: str
    manifest_url: Optional[str]


class StorageBase(abc.ABC):
    """
    Base interface for object storage providers (e.g. S3, GCS, Azure Blob).

    Implementations should provide concrete behavior for all abstract methods.
    Methods are intentionally high-level and provider-agnostic.
    """

    def __init__(self, bucket: str, *, base_path: str = "") -> None:
        self.bucket = bucket
        self.base_path = base_path.strip("/")

    @abc.abstractmethod
    def upload_file(
        self,
        key: str,
        file: IO[bytes] | bytes | str,
        *,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        overwrite: bool = True,
    ) -> UploadResult:
        """Upload bytes or a file-like/filename to the given key."""

    @abc.abstractmethod
    def download_file(self, key: str, destination: str | IO[bytes]) -> None:
        """Download object identified by key into a file path or binary stream."""

    @abc.abstractmethod
    def open_stream(self, key: str) -> BinaryIO:
        """Open the object for reading as a binary stream."""

    @abc.abstractmethod
    def delete_object(self, key: str, *, missing_ok: bool = True) -> None:
        """Delete the object if it exists; optionally raise when missing."""

    @abc.abstractmethod
    def copy_object(
        self, source_key: str, dest_key: str, *, overwrite: bool = True
    ) -> StoredObjectInfo:
        """Copy an object to a new key within the same bucket/account."""

    @abc.abstractmethod
    def object_exists(self, key: str) -> bool:
        """Return True if the object exists and is accessible."""

    @abc.abstractmethod
    def get_object_info(self, key: str) -> Optional[StoredObjectInfo]:
        """Return rich object info or None if not found."""

    @abc.abstractmethod
    def list_objects(self, prefix: str = "") -> Iterable[str]:
        """Yield object keys under the optional prefix."""

    @abc.abstractmethod
    def update_metadata(
        self, key: str, metadata: Dict[str, str], *, merge: bool = True
    ) -> StoredObjectInfo:
        """Update object metadata; merge or replace existing entries."""

    @abc.abstractmethod
    def get_object_status(self, key: str) -> ObjectStatus:
        """Return a coarse status for the object (availability/progress)."""

    @abc.abstractmethod
    def build_url(self, key: str, *, expires_in: Optional[int] = None) -> Optional[str]:
        """Return a public or signed URL when supported; otherwise None."""

    def resolve_key(self, key: str) -> str:
        if not key:
            raise StorageError("Object key must be a non-empty string")
        if self.base_path:
            return f"{self.base_path}/{key.lstrip('/')}"
        return key.lstrip("/")


class R2Storage(StorageBase):
    """
    Cloudflare R2 implementation using the S3-compatible API via boto3.

    To instantiate, provide credentials and endpoint details explicitly, or
    rely on environment variables:
      - R2_ACCESS_KEY_ID
      - R2_SECRET_ACCESS_KEY
      - R2_ACCOUNT_ID
      - R2_BUCKET
      - R2_REGION (optional, default: auto)
      - R2_PUBLIC_BASE_URL (optional, for constructing public URLs)
    """

    def __init__(
        self,
        bucket: str,
        *,
        base_path: str = "",
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        account_id: Optional[str] = None,
        region: Optional[str] = None,
        public_base_url: Optional[str] = None,
        endpoint_url: Optional[str] = None,
    ) -> None:
        super().__init__(bucket=bucket, base_path=base_path)
        self.access_key_id = access_key_id or os.getenv("R2_ACCESS_KEY_ID")
        self.secret_access_key = secret_access_key or os.getenv("R2_SECRET_ACCESS_KEY")
        self.account_id = account_id or os.getenv("R2_ACCOUNT_ID")
        self.region = region or os.getenv("R2_REGION") or "auto"
        self.public_base_url = public_base_url or os.getenv("R2_PUBLIC_BASE_URL")
        self.endpoint_url = (
            endpoint_url
            or os.getenv("R2_ENDPOINT_URL")
            or (
                f"https://{self.account_id}.r2.cloudflarestorage.com"
                if self.account_id
                else None
            )
        )

        try:
            import boto3  # type: ignore
            from boto3.s3.transfer import TransferConfig  # type: ignore
            from botocore.config import Config  # type: ignore
        except Exception as exc:  # pragma: no cover - import-time guard
            raise StorageError(
                "boto3 is required for R2Storage. Install with 'pip install boto3'."
            ) from exc

        if not self.endpoint_url:
            raise StorageError("R2 endpoint_url or ACCOUNT_ID must be provided")
        if not self.access_key_id or not self.secret_access_key:
            raise StorageError("R2 access_key_id and secret_access_key are required")

        botocore_config = Config(
            retries={
                "max_attempts": int(os.getenv("R2_MAX_RETRY_ATTEMPTS", "8")),
                "mode": "standard",
            },
            signature_version="s3v4",
            s3={"addressing_style": "virtual"},
            tcp_keepalive=True,
        )
        self._s3 = boto3.client(
            "s3",
            region_name=self.region,
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            config=botocore_config,
        )
        self._logger = logging.getLogger(__name__)
        # Transfer config for high-throughput multipart uploads (env tunable)
        try:
            chunk_mb = int(os.getenv("R2_MP_CHUNKSIZE_MB", "8"))
            concurrency = int(os.getenv("R2_MP_MAX_CONCURRENCY", "10"))
            self._transfer_config = TransferConfig(
                multipart_threshold=chunk_mb * 1024 * 1024,
                multipart_chunksize=chunk_mb * 1024 * 1024,
                max_concurrency=concurrency,
                use_threads=True,
            )
        except Exception:
            self._transfer_config = None

    def upload_file(
        self,
        key: str,
        file: IO[bytes] | bytes | str,
        *,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        overwrite: bool = True,
        cache_control: Optional[str] = None,
        content_disposition: Optional[str] = None,
        compute_md5: bool = False,
    ) -> UploadResult:
        r2_key = self.resolve_key(key)
        extra_args: Dict[str, Any] = {}
        # Guess content type when not specified
        if not content_type:
            try:
                path_for_guess = key if not isinstance(file, str) else file
                guessed, _ = mimetypes.guess_type(path_for_guess)
                content_type = guessed or None
            except Exception:
                content_type = None
        if content_type:
            extra_args["ContentType"] = content_type
        if metadata:
            extra_args["Metadata"] = metadata
        if cache_control:
            extra_args["CacheControl"] = cache_control
        if content_disposition:
            extra_args["ContentDisposition"] = content_disposition
        if not overwrite and self.object_exists(r2_key):
            raise StorageError(f"Object already exists: {r2_key}")

        body: IO[bytes]
        should_close = False
        if isinstance(file, (bytes, bytearray)):
            import io

            body = io.BytesIO(file)
            should_close = True
        elif isinstance(file, str):
            body = open(file, "rb")
            should_close = True
        else:
            body = file

        # Optional MD5 integrity check (bytes only)
        if compute_md5 and isinstance(file, (bytes, bytearray)):
            import base64

            extra_args["ContentMD5"] = base64.b64encode(
                hashlib.md5(file).digest()
            ).decode("ascii")

        try:
            if self._transfer_config is not None:
                self._s3.upload_fileobj(
                    Fileobj=body,
                    Bucket=self.bucket,
                    Key=r2_key,
                    ExtraArgs=extra_args if extra_args else None,
                    Config=self._transfer_config,
                )
                head = self._s3.head_object(Bucket=self.bucket, Key=r2_key)
                put_resp = {
                    "ETag": head.get("ETag"),
                    "VersionId": head.get("VersionId"),
                }
            else:
                put_resp = self._s3.put_object(
                    Bucket=self.bucket, Key=r2_key, Body=body, **extra_args
                )
        finally:
            if should_close:
                try:
                    body.close()
                except Exception:  # pragma: no cover
                    pass

        etag = put_resp.get("ETag")
        version_id = put_resp.get("VersionId")
        self._logger.info(
            "Uploaded object",
            extra={"key": r2_key, "etag": etag, "version_id": version_id},
        )
        return UploadResult(key=r2_key, etag=etag, version_id=version_id, raw=put_resp)

    def download_file(self, key: str, destination: str | IO[bytes]) -> None:
        r2_key = self.resolve_key(key)
        if isinstance(destination, str):
            with open(destination, "wb") as fh:
                self._s3.download_fileobj(self.bucket, r2_key, fh)
        else:
            self._s3.download_fileobj(self.bucket, r2_key, destination)

    def open_stream(self, key: str) -> BinaryIO:
        r2_key = self.resolve_key(key)
        obj = self._s3.get_object(Bucket=self.bucket, Key=r2_key)
        return obj["Body"]  # type: ignore[return-value]

    def delete_object(self, key: str, *, missing_ok: bool = True) -> None:
        r2_key = self.resolve_key(key)
        try:
            self._s3.delete_object(Bucket=self.bucket, Key=r2_key)
        except Exception:
            if not missing_ok:
                raise

    def copy_object(
        self, source_key: str, dest_key: str, *, overwrite: bool = True
    ) -> StoredObjectInfo:
        src = self.resolve_key(source_key)
        dst = self.resolve_key(dest_key)
        if not overwrite and self.object_exists(dst):
            raise StorageError(f"Destination already exists: {dst}")
        self._s3.copy({"Bucket": self.bucket, "Key": src}, self.bucket, dst)
        return self.get_object_info(dst) or StoredObjectInfo(key=dst)

    def object_exists(self, key: str) -> bool:
        r2_key = self.resolve_key(key)
        try:
            self._s3.head_object(Bucket=self.bucket, Key=r2_key)
            return True
        except Exception:
            return False

    def get_object_info(self, key: str) -> Optional[StoredObjectInfo]:
        r2_key = self.resolve_key(key)
        try:
            resp = self._s3.head_object(Bucket=self.bucket, Key=r2_key)
        except Exception:
            return None
        size = resp.get("ContentLength")
        content_type = resp.get("ContentType")
        metadata = resp.get("Metadata") or None
        etag = resp.get("ETag")
        last_mod = resp.get("LastModified")
        created = None
        updated = None
        if last_mod:
            # boto3 returns tz-aware datetime
            created = updated = last_mod
        checksum = etag.strip('"') if isinstance(etag, str) else None
        return StoredObjectInfo(
            key=r2_key,
            size_bytes=size,
            checksum=checksum,
            content_type=content_type,
            created_at=created,
            updated_at=updated,
            metadata=metadata,
            raw=resp,
        )

    def list_objects(self, prefix: str = "") -> Iterable[str]:
        r2_prefix = self.resolve_key(prefix) if prefix else self.base_path
        paginator = self._s3.get_paginator("list_objects_v2")
        kwargs = {"Bucket": self.bucket}
        if r2_prefix:
            kwargs["Prefix"] = r2_prefix
        for page in paginator.paginate(**kwargs):
            for item in page.get("Contents", []) or []:
                yield item.get("Key")

    def update_metadata(
        self, key: str, metadata: Dict[str, str], *, merge: bool = True
    ) -> StoredObjectInfo:
        r2_key = self.resolve_key(key)
        current = {}  # type: Dict[str, str]
        info = self.get_object_info(r2_key)
        if info and info.metadata:
            current = dict(info.metadata)
        new_metadata = {**current, **metadata} if merge else metadata
        # S3-compatible metadata update requires a self-copy with replace directive
        self._s3.copy_object(
            Bucket=self.bucket,
            Key=r2_key,
            CopySource={"Bucket": self.bucket, "Key": r2_key},
            Metadata=new_metadata,
            MetadataDirective="REPLACE",
            ContentType=info.content_type if info else None,
        )
        return self.get_object_info(r2_key) or StoredObjectInfo(
            key=r2_key, metadata=new_metadata
        )

    def get_object_status(self, key: str) -> ObjectStatus:
        return (
            ObjectStatus.AVAILABLE
            if self.object_exists(key)
            else ObjectStatus.NOT_FOUND
        )

    def build_url(self, key: str, *, expires_in: Optional[int] = None) -> Optional[str]:
        r2_key = self.resolve_key(key)
        if expires_in:
            try:
                url = self._s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket, "Key": r2_key},
                    ExpiresIn=int(expires_in),
                )
                return url
            except Exception:
                return None
        if self.public_base_url:
            base = self.public_base_url.rstrip("/")
            return f"{base}/{r2_key}"
        return None

    def upload_media_bundle(
        self,
        *,
        song_id: str,
        audio: IO[bytes] | bytes | str,
        audio_content_type: Optional[str] = None,
        video: Optional[IO[bytes] | bytes | str] = None,
        video_content_type: Optional[str] = None,
        art: Optional[IO[bytes] | bytes | str] = None,
        art_content_type: Optional[str] = None,
        prefix: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        user_id: Optional[str] = None,
        url_expires_in: Optional[int] = 3600,
    ) -> MediaBundleResult:
        """
        Upload audio (+ optional video and artwork) under a song-specific prefix.
        Creates and stores a manifest JSON with links and metadata for the bundle,
        and stores per-object JSON logs alongside each object.
        """

        if not song_id:
            raise StorageError("song_id is required for media bundle uploads")

        normalized_prefix = prefix.strip("/") if prefix else f"songs/{song_id}"

        ts = int(time.time())
        audio_key = f"{normalized_prefix}/audio"
        video_key = f"{normalized_prefix}/video" if video is not None else None
        art_key = f"{normalized_prefix}/art" if art is not None else None

        audio_up = self.upload_file(
            audio_key,
            audio,
            content_type=audio_content_type or "audio/mpeg",
            metadata={**(metadata or {}), "song_id": song_id, "type": "audio"},
        )
        audio_url = self.build_url(
            audio_up.key, expires_in=url_expires_in
        ) or self.build_url(audio_up.key)

        video_up: Optional[UploadResult] = None
        video_url: Optional[str] = None
        if video_key is not None and video is not None:
            video_up = self.upload_file(
                video_key,
                video,
                content_type=video_content_type or "video/mp4",
                metadata={**(metadata or {}), "song_id": song_id, "type": "video"},
            )
            video_url = self.build_url(
                video_up.key, expires_in=url_expires_in
            ) or self.build_url(video_up.key)

        art_up: Optional[UploadResult] = None
        art_url: Optional[str] = None
        if art_key is not None and art is not None:
            art_up = self.upload_file(
                art_key,
                art,
                content_type=art_content_type or "image/jpeg",
                metadata={**(metadata or {}), "song_id": song_id, "type": "art"},
            )
            art_url = self.build_url(
                art_up.key, expires_in=url_expires_in
            ) or self.build_url(art_up.key)

        manifest = {
            "song_id": song_id,
            "uploaded_at": ts,
            "bucket": self.bucket,
            "prefix": normalized_prefix,
            "links": {
                "audio": audio_url,
                "video": video_url,
                "art": art_url,
            },
            "keys": {
                "audio": audio_up.key,
                "video": video_up.key if video_up else None,
                "art": art_up.key if art_up else None,
            },
            "metadata": metadata or {},
            "uploader_id": user_id,
            "versions": {
                "audio": getattr(audio_up, "version_id", None),
                "video": getattr(video_up, "version_id", None) if video_up else None,
                "art": getattr(art_up, "version_id", None) if art_up else None,
            },
            "etags": {
                "audio": getattr(audio_up, "etag", None),
                "video": getattr(video_up, "etag", None) if video_up else None,
                "art": getattr(art_up, "etag", None) if art_up else None,
            },
        }

        manifest_key = f"{normalized_prefix}/manifest.json"
        self._put_json(
            manifest_key, manifest, metadata={"song_id": song_id, "type": "manifest"}
        )
        manifest_url = self.build_url(
            manifest_key, expires_in=url_expires_in
        ) or self.build_url(manifest_key)

        # Per-object logs
        self._write_object_log(audio_up.key, song_id=song_id, user_id=user_id)
        if video_up:
            self._write_object_log(video_up.key, song_id=song_id, user_id=user_id)
        if art_up:
            self._write_object_log(art_up.key, song_id=song_id, user_id=user_id)

        return MediaBundleResult(
            song_id=song_id,
            audio_key=audio_up.key,
            video_key=video_up.key if video_up else None,
            art_key=art_up.key if art_up else None,
            audio_url=audio_url,
            video_url=video_url,
            art_url=art_url,
            manifest_key=manifest_key,
            manifest_url=manifest_url,
        )

    def _put_json(
        self,
        key: str,
        payload: Dict[str, Any],
        *,
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
        self.upload_file(
            key, body, content_type="application/json", metadata=metadata or {}
        )

    def _write_object_log(
        self, key: str, *, song_id: Optional[str], user_id: Optional[str]
    ) -> None:
        info = self.get_object_info(key)
        log_payload = {
            "song_id": song_id,
            "user_id": user_id,
            "key": info.key if info else self.resolve_key(key),
            "status": self.get_object_status(key).value,
            "size_bytes": info.size_bytes if info else None,
            "content_type": info.content_type if info else None,
            "checksum": info.checksum if info else None,
            "timestamp": int(time.time()),
        }
        log_key = f"{os.path.dirname(self.resolve_key(key))}/upload_log_{int(time.time()*1000)}.json"
        self._put_json(
            log_key,
            log_payload,
            metadata={"song_id": song_id or "", "type": "upload_log"},
        )
        self._logger.info("Wrote upload log", extra={"key": key, "log_key": log_key})

    @staticmethod
    def compute_md5(data: bytes) -> str:
        return hashlib.md5(data).hexdigest()

    def replace_media_asset(
        self,
        *,
        song_id: str,
        asset: Literal["audio", "video", "art"],
        file: IO[bytes] | bytes | str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        user_id: Optional[str] = None,
        prefix: Optional[str] = None,
        url_expires_in: Optional[int] = 3600,
    ) -> MediaBundleResult:
        """Replace one asset, update manifest and logs, return updated links/keys."""
        normalized_prefix = prefix.strip("/") if prefix else f"songs/{song_id}"
        key = f"{normalized_prefix}/{asset}"
        up = self.upload_file(
            key,
            file,
            content_type=content_type,
            metadata={**(metadata or {}), "song_id": song_id, "type": asset},
        )

        manifest_key = f"{normalized_prefix}/manifest.json"
        manifest: Dict[str, Any] = {}
        try:
            with self.open_stream(manifest_key) as fh:
                manifest = json.loads(fh.read())
        except Exception:
            manifest = {
                "song_id": song_id,
                "bucket": self.bucket,
                "prefix": normalized_prefix,
                "links": {"audio": None, "video": None, "art": None},
                "keys": {"audio": None, "video": None, "art": None},
                "metadata": {},
            }

        manifest.setdefault("keys", {})[asset] = up.key
        manifest.setdefault("links", {})[asset] = self.build_url(
            up.key, expires_in=url_expires_in
        ) or self.build_url(up.key)
        manifest["uploaded_at"] = int(time.time())
        if metadata:
            manifest.setdefault("metadata", {}).update(metadata)
        if user_id:
            manifest["uploader_id"] = user_id

        self._put_json(
            manifest_key, manifest, metadata={"song_id": song_id, "type": "manifest"}
        )
        self._write_object_log(up.key, song_id=song_id, user_id=user_id)

        return MediaBundleResult(
            song_id=song_id,
            audio_key=manifest["keys"].get("audio"),
            video_key=manifest["keys"].get("video"),
            art_key=manifest["keys"].get("art"),
            audio_url=manifest["links"].get("audio"),
            video_url=manifest["links"].get("video"),
            art_url=manifest["links"].get("art"),
            manifest_key=manifest_key,
            manifest_url=self.build_url(manifest_key, expires_in=url_expires_in)
            or self.build_url(manifest_key),
        )

    def create_presigned_post(
        self,
        key: str,
        *,
        expires_in: int = 3600,
        conditions: Optional[list] = None,
        fields: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return a dict suitable for client-side direct upload via HTML form/JS."""
        r2_key = self.resolve_key(key)
        try:
            resp = self._s3.generate_presigned_post(
                Bucket=self.bucket,
                Key=r2_key,
                ExpiresIn=int(expires_in),
                Conditions=conditions,
                Fields=fields,
            )
            return resp
        except Exception:
            return None
