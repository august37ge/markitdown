"""Core MarkItDown conversion engine.

This module provides the main MarkItDown class responsible for converting
various file formats and URLs to Markdown.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import requests


class DocumentConverterResult:
    """Result object returned by document converters."""

    def __init__(self, title: Optional[str] = None, text_content: str = "") -> None:
        self.title = title
        self.text_content = text_content

    def __str__(self) -> str:
        return self.text_content


class DocumentConverter:
    """Base class for all document converters."""

    def convert(
        self,
        local_path: str,
        **kwargs: Any,
    ) -> Optional[DocumentConverterResult]:
        """Convert a document at the given local path to Markdown.

        Args:
            local_path: Path to the local file to convert.
            **kwargs: Additional keyword arguments for converters.

        Returns:
            A DocumentConverterResult or None if conversion is not supported.
        """
        raise NotImplementedError("Subclasses must implement convert()")


class MarkItDown:
    """Main class for converting documents to Markdown.

    Supports converting local files, URLs, and raw content from various
    formats including HTML, PDF, DOCX, XLSX, PPTX, and plain text.

    Example::

        from markitdown import MarkItDown

        md = MarkItDown()
        result = md.convert("document.pdf")
        print(result.text_content)
    """

    def __init__(
        self,
        requests_session: Optional[requests.Session] = None,
        mlm_client: Optional[Any] = None,
        mlm_model: Optional[str] = None,
    ) -> None:
        """Initialize MarkItDown.

        Args:
            requests_session: Optional requests session for HTTP requests.
            mlm_client: Optional multimodal language model client for image
                        descriptions.
            mlm_model: Optional model name to use with the mlm_client.
        """
        self._requests_session = requests_session or requests.Session()
        self._mlm_client = mlm_client
        self._mlm_model = mlm_model
        self._converters: List[DocumentConverter] = []
        self._register_default_converters()

    def _register_default_converters(self) -> None:
        """Register the built-in set of document converters."""
        # Converters are tried in order; first match wins.
        # Additional converters are imported lazily to avoid hard dependencies.
        from markitdown.converters import (
            HtmlConverter,
            PlainTextConverter,
        )

        self._converters = [
            HtmlConverter(),
            PlainTextConverter(),
        ]

    def register_converter(self, converter: DocumentConverter) -> None:
        """Register a custom converter at the front of the converter list.

        Args:
            converter: A DocumentConverter instance to register.
        """
        self._converters.insert(0, converter)

    def convert(
        self,
        source: Union[str, Path],
        **kwargs: Any,
    ) -> DocumentConverterResult:
        """Convert a file or URL to Markdown.

        Args:
            source: A file path (str or Path) or a URL string.
            **kwargs: Additional keyword arguments forwarded to converters.

        Returns:
            A DocumentConverterResult containing the Markdown text.

        Raises:
            FileNotFoundError: If the local file does not exist.
            ValueError: If no converter could handle the given source.
        """
        source = str(source)

        # Handle URLs
        parsed = urlparse(source)
        if parsed.scheme in ("http", "https"):
            return self._convert_url(source, **kwargs)

        # Handle local files
        local_path = os.path.abspath(source)
        if not os.path.isfile(local_path):
            raise FileNotFoundError(f"File not found: {local_path}")

        return self._convert_local(local_path, **kwargs)

    def _convert_url(
        self,
        url: str,
        **kwargs: Any,
    ) -> DocumentConverterResult:
        """Download a URL to a temporary file and convert it."""
        response = self._requests_session.get(url, stream=True)
        response.raise_for_status()

        # Determine a reasonable file extension from Content-Type
        content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
        ext = _content_type_to_ext(content_type)

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            for chunk in response.iter_content(chunk_size=8192):
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            result = self._convert_local(tmp_path, url=url, **kwargs)
        finally:
            os.unlink(tmp_path)

        return result

    def _convert_local(
        self,
        local_path: str,
        **kwargs: Any,
    ) -> DocumentConverterResult:
        """Try each registered converter until one succeeds."""
        for converter in self._converters:
            result = converter.convert(local_path, **kwargs)
            if result is not None:
                return result

        raise ValueError(
            f"No converter was able to handle the file: {local_path}"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CONTENT_TYPE_MAP: Dict[str, str] = {
    "text/html": ".html",
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/plain": ".txt",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def _content_type_to_ext(content_type: str) -> str:
    """Map a MIME content type to a file extension."""
    return _CONTENT_TYPE_MAP.get(content_type, ".bin")
