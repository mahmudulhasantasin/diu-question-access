"""MCP Resource providers for binary PDF delivery and collection manifests."""

import base64
import json
import logging
from pathlib import Path
from typing import Optional
import mcp.types as types
from services.collection_service import CollectionService

logger = logging.getLogger("diu_mcp.mcp_server.resources")


def read_pdf_resource(
    service: CollectionService,
    file_id: str,
) -> types.BlobResourceContents:
    """Read an original PDF from disk and return as binary MCP BlobResourceContents."""
    meta = service.get_pdf_metadata(file_id)
    if not meta:
        raise ValueError(f"PDF file '{file_id}' not found in database.")

    path = Path(meta.local_path)
    if not path.is_file():
        raise FileNotFoundError(
            f"PDF file '{file_id}' registered in database but missing on disk at '{meta.local_path}'."
        )

    with open(path, "rb") as f:
        pdf_bytes = f.read()

    b64_blob = base64.b64encode(pdf_bytes).decode("ascii")

    return types.BlobResourceContents(
        uri=f"diu-question://pdf/{file_id}",
        mime_type="application/pdf",
        blob=b64_blob,
    )


def read_collection_resource(
    service: CollectionService,
    collection_id: str,
) -> types.TextResourceContents:
    """Read a collection manifest and return as JSON TextResourceContents."""
    summary = service.get_collection_summary(collection_id)
    if not summary:
        raise ValueError(f"Collection bundle '{collection_id}' not found.")

    return types.TextResourceContents(
        uri=f"diu-question://collection/{collection_id}",
        mime_type="application/json",
        text=json.dumps(summary, indent=2),
    )
