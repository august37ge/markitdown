# SPDX-FileCopyrightText: 2024 MarkItDown Contributors
# SPDX-License-Identifier: MIT

"""MarkItDown - A utility for converting various file formats to Markdown.

This package provides tools to convert documents, spreadsheets, presentations,
images, audio, and web content into clean Markdown format.
"""

from markitdown._markitdown import MarkItDown, DocumentConverter, ConversionResult

__version__ = "0.1.0"
__all__ = ["MarkItDown", "DocumentConverter", "ConversionResult"]
