"""Validation utilities for ensuring binary integrity of original PDF files."""

import hashlib
import logging
from typing import Tuple

logger = logging.getLogger("diu_mcp.downloader.validator")

# Standard PDF magic bytes
PDF_MAGIC_HEADER = b"%PDF-"


def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hex digest for binary data."""
    return hashlib.sha256(data).hexdigest()


def validate_pdf_bytes(data: bytes, min_size_bytes: int = 30) -> Tuple[bool, str, str]:
    """Validate that binary data represents an unmodified valid PDF.
    
    Returns:
        (is_valid: bool, sha256_checksum: str, reason: str)
    """
    if not data:
        return False, "", "Empty byte stream received."

    if len(data) < min_size_bytes:
        return False, "", f"File size ({len(data)} bytes) is below minimum valid PDF threshold."

    # Verify PDF magic header
    if not data.startswith(PDF_MAGIC_HEADER):
        header_sample = data[:20].decode("ascii", errors="replace")
        return (
            False,
            "",
            f"Invalid magic header: expected b'%PDF-', got '{header_sample}' (possible HTML error page)."
        )

    # Check for EOF marker near end of PDF
    tail = data[-1024:]
    if b"%%EOF" not in tail:
        logger.warning("PDF does not end with standard '%%EOF' marker, but starts with '%PDF-'.")

    checksum = compute_sha256(data)
    return True, checksum, "Valid original PDF."
