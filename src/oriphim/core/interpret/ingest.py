"""Document ingestion: a paper file becomes plain text for the interpreter.

Deliberately shallow for this slice — whole-document text, no sectioning, no
equation or figure extraction. It exists so a run can feed a paper to the
model as context. The moment a run needs structure (equations as first-class
objects, figure captions tied to results), that need picks the build and this
module grows.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from pypdf import PdfReader

_PDF_SUFFIXES = {".pdf"}
_HTML_SUFFIXES = {".html", ".htm"}
_TEXT_SUFFIXES = {".txt", ".md"}
_DROP_TAGS = {"script", "style"}


def extract_text(path: Path) -> str:
    """Return the plain-text content of a paper file.

    Supports PDF (via pypdf), HTML, and plain text / Markdown. Raises
    `ValueError` for any other suffix rather than guessing.
    """
    suffix = path.suffix.lower()
    if suffix in _PDF_SUFFIXES:
        return _extract_pdf(path)
    if suffix in _HTML_SUFFIXES:
        return _extract_html(path)
    if suffix in _TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8")
    raise ValueError(f"Don't know how to extract text from {path.suffix!r} ({path}).")


def _extract_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages).strip()


def _extract_html(path: Path) -> str:
    parser = _TextExtractor()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    lines = (line.strip() for line in parser.text().splitlines())
    return "\n".join(line for line in lines if line)


class _TextExtractor(HTMLParser):
    """Collect character data, dropping the content of script/style tags."""

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._suppressed = 0  # depth inside a dropped tag; handles malformed nesting

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _DROP_TAGS:
            self._suppressed += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _DROP_TAGS and self._suppressed > 0:
            self._suppressed -= 1

    def handle_data(self, data: str) -> None:
        if self._suppressed == 0:
            self._chunks.append(data)

    def text(self) -> str:
        return "".join(self._chunks)
