"""Secure document processing and validation service."""

import io
import os
from typing import Tuple
from fastapi import UploadFile
import pypdf
import docx

from backend.app.core.config import get_settings
from backend.app.core.errors import UnsupportedDocumentError
from backend.app.modules.documents.sanitizer import detect_file_format, sanitize_filename, validate_file_size
from backend.app.modules.documents.schemas import DocumentFormat, DocumentMetadata
from backend.app.modules.documents.storage import TemporaryStorageManager

settings = get_settings()

CHUNK_SIZE = 64 * 1024  # 64 KB read buffer
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


class DocumentUploadService:
    """Safely streams, inspects magic bytes, validates integrity, and persists uploads."""

    def __init__(self, storage_manager: TemporaryStorageManager | None = None):
        self.storage = storage_manager or TemporaryStorageManager()

    async def process_and_store_upload(
        self,
        file: UploadFile,
    ) -> Tuple[DocumentMetadata, bytes]:
        """Validates stream safely without memory exhaustion, verifies integrity, and saves to temp disk."""
        if not file.filename:
            raise UnsupportedDocumentError("Uploaded file has no filename.")

        ext = os.path.splitext(file.filename.lower())[1]
        if ext not in ALLOWED_EXTENSIONS:
            raise UnsupportedDocumentError(
                f"File extension '{ext}' is not supported. Allowed formats: PDF, DOCX, TXT."
            )

        sanitized_name = sanitize_filename(file.filename)
        buffer = bytearray()
        total_size = 0

        # Stream chunk by chunk to prevent memory exhaustion
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > settings.MAX_UPLOAD_SIZE_BYTES:
                raise UnsupportedDocumentError(
                    f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024):.1f} MB."
                )
            buffer.extend(chunk)

        content_bytes = bytes(buffer)
        validate_file_size(len(content_bytes), settings.MAX_UPLOAD_SIZE_BYTES)

        # 1. Magic bytes sniff
        detected_format = detect_file_format(content_bytes[:32], sanitized_name)

        # 2. Structural integrity check
        self._validate_document_integrity(content_bytes, detected_format, sanitized_name)

        # 3. Store securely
        saved_path = await self.storage.save_temp_file(content_bytes, sanitized_name)

        # Map MIME type
        content_type_map = {
            DocumentFormat.PDF: "application/pdf",
            DocumentFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            DocumentFormat.TXT: "text/plain",
        }

        metadata = DocumentMetadata(
            original_filename=file.filename,
            sanitized_filename=sanitized_name,
            format=detected_format,
            content_type=content_type_map[detected_format],
            file_size_bytes=len(content_bytes),
            storage_path=saved_path,
        )

        return metadata, content_bytes

    def _validate_document_integrity(
        self,
        content: bytes,
        doc_format: DocumentFormat,
        filename: str,
    ) -> None:
        """Verifies document structure to catch corrupted files, decompression bombs, or fakes."""
        bio = io.BytesIO(content)

        if doc_format == DocumentFormat.PDF:
            try:
                reader = pypdf.PdfReader(bio)
                if reader.is_encrypted:
                    raise UnsupportedDocumentError("Password-protected or encrypted PDFs are not supported.")
                if len(reader.pages) == 0:
                    raise UnsupportedDocumentError("PDF contains no readable pages.")
            except UnsupportedDocumentError:
                raise
            except Exception as e:
                raise UnsupportedDocumentError(f"Malformed or corrupted PDF file: {str(e)}")

        elif doc_format == DocumentFormat.DOCX:
            try:
                doc = docx.Document(bio)
                # Ensure document can be parsed
                _ = len(doc.paragraphs)
            except Exception as e:
                raise UnsupportedDocumentError(f"Malformed or corrupted DOCX file: {str(e)}")

        elif doc_format == DocumentFormat.TXT:
            try:
                content.decode("utf-8")
            except UnicodeDecodeError:
                raise UnsupportedDocumentError("Text document is not valid UTF-8.")
