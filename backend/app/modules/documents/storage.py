"""Temporary and persistent document storage management with safe deterministic cleanup."""

import os
import uuid
from pathlib import Path
from backend.app.core.config import get_settings
from backend.app.core.logging import logger
from backend.app.modules.documents.sanitizer import sanitize_filename


class TemporaryStorageManager:
    """Manages temporary files safely, avoiding race conditions and ensuring cleanup."""

    def __init__(self, base_dir: str | None = None):
        settings = get_settings()
        self.base_dir = Path(base_dir or settings.UPLOAD_TEMP_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_temp_file_sync(self, content: bytes, original_filename: str) -> str:
        """Saves uploaded binary content to a uniquely generated server path using stdlib."""
        safe_name = sanitize_filename(original_filename)
        unique_prefix = str(uuid.uuid4())
        destination = self.base_dir / f"{unique_prefix}_{safe_name}"
        destination.write_bytes(content)
        return str(destination.resolve())

    async def save_temp_file(self, content: bytes, original_filename: str) -> str:
        """Async-compatible save wrapper."""
        return self.save_temp_file_sync(content, original_filename)

    @staticmethod
    def cleanup_file(file_path: str) -> bool:
        """Safely removes a temporary file from disk."""
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception as e:
            logger.warning(f"Failed to delete temporary file {file_path}: {e}")
        return False
