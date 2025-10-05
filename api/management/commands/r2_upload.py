import os
from typing import Optional
from dotenv import load_dotenv
from django.core.management.base import BaseCommand, CommandParser

from services.storage import R2Storage


_ = load_dotenv()


class Command(BaseCommand):
    help = "Upload media files to Cloudflare R2 and print URLs using R2Storage.upload_media_bundle"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("song_id", type=str, help="Song identifier")
        parser.add_argument("audio", type=str, help="Path to audio file (mp3, etc.)")
        parser.add_argument(
            "--video", type=str, default=None, help="Path to video file (mp4)"
        )
        parser.add_argument(
            "--art", type=str, default=None, help="Path to cover art (jpg/png)"
        )
        parser.add_argument(
            "--bucket",
            type=str,
            default=None,
            help="R2 bucket name (overrides R2_BUCKET env)",
        )
        parser.add_argument(
            "--prefix", type=str, default=None, help="Optional base prefix under bucket"
        )
        parser.add_argument(
            "--user", type=str, default=None, help="Optional uploader user id"
        )
        parser.add_argument(
            "--expires", type=int, default=3600, help="Presigned URL expiry in seconds"
        )

    def handle(self, *args, **options) -> Optional[str]:
        song_id: str = options["song_id"]
        audio_path: str = options["audio"]
        video_path: Optional[str] = options.get("video")
        art_path: Optional[str] = options.get("art")
        prefix: Optional[str] = options.get("prefix")
        user_id: Optional[str] = options.get("user")
        expires: int = int(options.get("expires") or 3600)

        bucket = os.getenv("R2_BUCKET", options.get("bucket"))
        if not bucket:
            self.stderr.write(
                self.style.ERROR("R2_BUCKET environment variable is required")
            )
            return None

        storage = R2Storage(bucket=bucket, base_path=os.getenv("R2_BASE_PATH", ""))

        if not os.path.isfile(audio_path):
            self.stderr.write(self.style.ERROR(f"Audio file not found: {audio_path}"))
            return None

        video_file = video_path if video_path and os.path.isfile(video_path) else None
        art_file = art_path if art_path and os.path.isfile(art_path) else None

        result = storage.upload_media_bundle(
            song_id=song_id,
            audio=audio_path,
            audio_content_type=None,
            video=video_file,
            video_content_type=None,
            art=art_file,
            art_content_type=None,
            prefix=prefix,
            metadata={},
            user_id=user_id,
            url_expires_in=expires,
        )

        self.stdout.write(self.style.SUCCESS("Upload complete"))
        self.stdout.write(f"Audio:  {result.audio_url}")
        if result.video_url:
            self.stdout.write(f"Video:  {result.video_url}")
        if result.art_url:
            self.stdout.write(f"Art:    {result.art_url}")
        if result.manifest_url:
            self.stdout.write(f"Manifest: {result.manifest_url}")

        return None
