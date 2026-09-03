from __future__ import annotations

from pathlib import Path

import pytest

from oriphim.core.interpret.ingest import extract_text

_FIXTURES = Path(__file__).parent / "fixtures"
_KNOWN = "strongly magnetized and weakly collisional"

_DIFF_PIC = Path(
    "/Users/pc5/Desktop/BOOKS/PAPERS/"
    "Diff-PIC- Revolutionizing Particle-In-Cell Nuclear Fusion Simulation with Diffusion Models.pdf"
)


def test_extract_text_reads_plain_text() -> None:
    assert _KNOWN in extract_text(_FIXTURES / "tiny.txt")


def test_extract_text_strips_html() -> None:
    text = extract_text(_FIXTURES / "tiny.html")
    assert _KNOWN in text
    assert "color: red" not in text  # <style> contents dropped
    assert "console.log" not in text  # <script> contents dropped
    assert "<p>" not in text  # tags gone


def test_extract_text_rejects_unknown_suffix(tmp_path: Path) -> None:
    weird = tmp_path / "system.docx"
    weird.write_bytes(b"whatever")
    with pytest.raises(ValueError):
        extract_text(weird)


@pytest.mark.skipif(not _DIFF_PIC.exists(), reason="Diff-PIC PDF not on this machine")
def test_extract_text_reads_pdf() -> None:
    text = extract_text(_DIFF_PIC)
    assert len(text) > 5_000
    assert "particle-in-cell" in text.lower() or "diffusion" in text.lower()
