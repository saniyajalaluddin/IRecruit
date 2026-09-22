"""Filename sanitization and file signature verification."""

import os
import re
from backend.app.core.errors import UnsupportedDocumentError
from backend.app.modules.documents.schemas import DocumentFormat

# Magic byte signatures
PDF_MAGIC = b"%PDF"
ZIP_MAGIC = b"PK\x03\x04"  # DOCX files are zip archives


def sanitize_filename(filename: str) -> str:
    """Removes path traversal sequences, directory separators, and dangerous characters."""
    # Strip directory components
    clean = os.path.basename(filename)
    # Remove null bytes and non-printable characters
    clean = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", clean)
    # Keep only safe alphanumeric, dashes, dots, and underscores
    clean = re.sub(r"[^\w\s\.-]", "", clean).strip()
    # Collapse consecutive dots or spaces
    clean = re.sub(r"\.{2,}", ".", clean)
    clean = re.sub(r"\s+", "_", clean)
    return clean or "document"


def validate_file_size(size_bytes: int, max_bytes: int) -> None:
    """Validates that file is non-empty and does not exceed maximum limit."""
    if size_bytes <= 0:
        raise UnsupportedDocumentError("Uploaded file is empty (0 bytes).")
    if size_bytes > max_bytes:
        max_mb = max_bytes / (1024 * 1024)
        raise UnsupportedDocumentError(f"Uploaded file exceeds maximum allowed size of {max_mb:.1f} MB.")


def detect_file_format(header_bytes: bytes, filename: str) -> DocumentFormat:
    """Sniffs magic bytes to determine document format, defending against forged extensions."""
    ext = os.path.splitext(filename.lower())[1]

    if header_bytes.startswith(PDF_MAGIC):
        return DocumentFormat.PDF
    elif header_bytes.startswith(ZIP_MAGIC):
        # Could be docx or zip bomb; extension must match docx
        if ext == ".docx":
            return DocumentFormat.DOCX
        raise UnsupportedDocumentError("ZIP archives that are not DOCX are not permitted.")
    elif ext in [".txt", ".text"]:
        try:
            header_bytes.decode("utf-8")
            return DocumentFormat.TXT
        except UnicodeDecodeError:
            raise UnsupportedDocumentError("Text file is not valid UTF-8.")
    
    raise UnsupportedDocumentError(
        f"Unsupported file format or invalid file signature for '{filename}'. Allowed formats: PDF, DOCX, TXT."
    )
