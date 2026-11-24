"""On-demand, in-memory PDF page rendering service for multi-modal AI agents."""

import io
import logging
from pathlib import Path
from typing import Optional, Tuple
import httpx
import pypdfium2
from database.repository import DatabaseRepository

logger = logging.getLogger("diu_mcp.services.preview_service")


class PreviewService:
    """Renders PDF pages to high-resolution PNG images on-the-fly with zero permanent disk footprint."""

    def __init__(self, repo: DatabaseRepository, client: Optional[httpx.AsyncClient] = None):
        self.repo = repo
        self._client = client

    async def get_page_png_bytes(
        self,
        file_id: str,
        page_number: int = 1,
        scale: float = 2.0,
    ) -> Tuple[bytes, int, int]:
        """Render a specific page of a question PDF into PNG bytes.

        If the file is already cached locally, it reads it directly.
        Otherwise, it streams the PDF from OurDIU straight into memory (RAM),
        renders the page to PNG, and discards the raw PDF with zero disk footprint.

        Returns:
            Tuple of (png_bytes, current_page_number, total_page_count)
        """
        meta = self.repo.get_pdf_by_id(file_id)
        if not meta:
            raise ValueError(f"File ID '{file_id}' not found in database.")

        pdf_bytes: Optional[bytes] = None

        # 1. Check local file if available
        if meta.local_path and Path(meta.local_path).is_file():
            try:
                pdf_bytes = Path(meta.local_path).read_bytes()
            except Exception as exc:
                logger.warning(f"Could not read local file {meta.local_path}: {exc}")

        # 2. Otherwise fetch into RAM on-demand from remote URL
        if not pdf_bytes:
            if not meta.pdf_url:
                raise ValueError(f"No local file or remote pdf_url available for '{file_id}'.")

            close_client = False
            client = self._client
            if client is None:
                client = httpx.AsyncClient(
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                    timeout=httpx.Timeout(25.0),
                    follow_redirects=True,
                )
                close_client = True

            try:
                logger.info(f"Streaming PDF in-memory for {file_id} from {meta.pdf_url}...")
                resp = await client.get(meta.pdf_url)
                if resp.status_code != 200:
                    raise ValueError(f"Failed to fetch remote PDF: HTTP {resp.status_code}")
                pdf_bytes = resp.content
            finally:
                if close_client:
                    await client.aclose()

        # 3. Render page to PNG using pypdfium2 in-memory
        doc = None
        try:
            doc = pypdfium2.PdfDocument(pdf_bytes)
            total_pages = len(doc)
            if total_pages == 0:
                raise ValueError("PDF document contains no pages.")

            if page_number < 1 or page_number > total_pages:
                raise ValueError(f"Page {page_number} is out of range. Document has {total_pages} page(s).")

            page = doc[page_number - 1]
            rendered_image = page.render(scale=scale).to_pil()
            output_buffer = io.BytesIO()
            rendered_image.save(output_buffer, format="PNG")
            return output_buffer.getvalue(), page_number, total_pages
        except Exception as exc:
            logger.error(f"Error rendering PDF page {page_number} for {file_id}: {exc}")
            raise ValueError(f"Failed to render PDF page image: {exc}")
        finally:
            if doc is not None:
                try:
                    doc.close()
                except Exception:
                    pass
