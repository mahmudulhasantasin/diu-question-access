"""Async PDF downloader that strictly preserves original PDF bytes."""

import asyncio
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Optional, Tuple
import httpx
from database.models import PDFMetadata
from downloader.storage import PDFStorageManager
from downloader.validator import validate_pdf_bytes

logger = logging.getLogger("diu_mcp.downloader.pdf_downloader")


class PDFDownloader:
    """Downloads original DIU question paper PDFs with validation and caching."""

    def __init__(
        self,
        storage_manager: Optional[PDFStorageManager] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        self.storage = storage_manager or PDFStorageManager()
        self.timeout = timeout
        self.max_retries = max_retries

    async def download_pdf(
        self,
        meta: PDFMetadata,
        client: Optional[httpx.AsyncClient] = None,
        force_refresh: bool = False,
    ) -> PDFMetadata:
        """Download one PDF document, validate binary integrity, and store locally."""
        dest_path = self.storage.get_destination_path(meta)
        meta.local_path = str(dest_path.resolve())

        # Check local cache first if force_refresh is False
        if not force_refresh and meta.sha256 and self.storage.is_file_cached(dest_path, meta.sha256):
            logger.info(f"File {meta.file_id} already cached at {dest_path}. Skipping download.")
            meta.download_status = "cached"
            meta.file_size = dest_path.stat().st_size
            return meta

        logger.info(f"Downloading original PDF for {meta.file_id} from {meta.pdf_url}...")

        should_close_client = False
        if client is None:
            client = httpx.AsyncClient(
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
            )
            should_close_client = True

        try:
            for attempt in range(1, self.max_retries + 1):
                try:
                    resp = await client.get(meta.pdf_url)
                    if resp.status_code != 200:
                        raise httpx.HTTPStatusError(
                            f"HTTP {resp.status_code}",
                            request=resp.request,
                            response=resp
                        )

                    pdf_bytes = resp.content

                    # Validate PDF bytes
                    is_valid, checksum, reason = validate_pdf_bytes(pdf_bytes)
                    if not is_valid:
                        raise ValueError(f"PDF validation failed: {reason}")

                    # Write unmodified binary bytes to local file
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(dest_path, "wb") as f:
                        f.write(pdf_bytes)

                    meta.download_status = "downloaded"
                    meta.download_timestamp = datetime.now(timezone.utc).isoformat()
                    meta.file_size = len(pdf_bytes)
                    meta.sha256 = checksum
                    meta.error_message = None

                    logger.info(
                        f"Successfully downloaded {meta.file_id} ({meta.file_size} bytes, SHA256: {checksum[:12]}...)"
                    )
                    return meta

                except Exception as e:
                    if attempt == self.max_retries:
                        logger.error(f"Download failed for {meta.file_id} after {self.max_retries} attempts: {e}")
                        meta.download_status = "failed"
                        meta.error_message = str(e)
                        return meta
                    await asyncio.sleep(1.0 * attempt)

        finally:
            if should_close_client:
                await client.aclose()

        return meta
