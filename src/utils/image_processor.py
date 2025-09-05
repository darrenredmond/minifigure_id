import os
import uuid
from typing import Tuple, Optional
from pathlib import Path
from PIL import Image
import magic
from slugify import slugify

from config.settings import settings
from src.models.schemas import ImageUpload


class ImageProcessor:
    def __init__(self, upload_dir: str = "data/uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def validate_image(self, file_content: bytes, filename: str) -> bool:
        """Validate if the uploaded file is a valid image"""
        # Check file size
        if len(file_content) > settings.max_upload_size:
            raise ValueError(
                f"File size exceeds maximum allowed size of {settings.max_upload_size} bytes"
            )

        # Check file type using python-magic
        mime_type = magic.from_buffer(file_content, mime=True)
        if not mime_type.startswith("image/"):
            raise ValueError(f"File type {mime_type} is not supported")

        # Check file extension (allow missing extension if MIME type is valid)
        file_ext = filename.lower().split(".")[-1] if "." in filename else ""
        if file_ext and file_ext not in settings.allowed_image_types:
            raise ValueError(f"File extension '{file_ext}' is not allowed")

        return True

    def save_image(
        self, file_content: bytes, original_filename: str
    ) -> Tuple[str, ImageUpload]:
        """Save uploaded image and return the saved filename and metadata"""
        # Validate the image
        self.validate_image(file_content, original_filename)

        # Generate unique filename
        file_ext = (
            original_filename.lower().split(".")[-1]
            if "." in original_filename
            else "jpg"
        )
        base_name = slugify(Path(original_filename).stem)
        unique_id = str(uuid.uuid4())[:8]
        new_filename = f"{base_name}_{unique_id}.{file_ext}"

        # Save file
        file_path = self.upload_dir / new_filename
        with open(file_path, "wb") as f:
            f.write(file_content)

        # Create metadata
        image_upload = ImageUpload(
            filename=new_filename,
            content_type=magic.from_buffer(file_content, mime=True),
            size=len(file_content),
        )

        return str(file_path), image_upload

    def optimize_image_for_ai(
        self, file_path: str, max_size: Tuple[int, int] = (1024, 1024)
    ) -> str:
        """Optimize image for AI processing by resizing if needed"""
        optimized_dir = self.upload_dir / "optimized"
        optimized_dir.mkdir(exist_ok=True)

        with Image.open(file_path) as img:
            # Convert to RGB if necessary
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Resize if image is too large
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Save optimized version
            optimized_filename = f"opt_{Path(file_path).name}"
            optimized_path = optimized_dir / optimized_filename

            # Save with quality optimization
            img.save(optimized_path, "JPEG", quality=85, optimize=True)

            return str(optimized_path)

    def get_image_info(self, file_path: str) -> dict:
        """Extract basic information from an image"""
        with Image.open(file_path) as img:
            return {
                "format": img.format,
                "mode": img.mode,
                "size": img.size,
                "width": img.width,
                "height": img.height,
            }

    def cleanup_old_files(self, days_old: int = 30) -> int:
        """Remove files older than specified days"""
        import time

        current_time = time.time()
        cutoff_time = current_time - (days_old * 24 * 60 * 60)

        deleted_count = 0
        for file_path in self.upload_dir.glob("**/*"):
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                deleted_count += 1

        return deleted_count
