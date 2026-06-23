"""Integration contract for PDF QR seal generation and verification.

This test is intentionally black-box: the production letter sealer and verifier
live in the host application, not in this reusable image-generation package. To
run it against that application, set both command environment variables below:

- ``PDF_QR_SEAL_GENERATOR_CMD``: command that accepts an input PDF path and an
  output PDF path as its final two arguments, and writes a sealed PDF.
- ``PDF_QR_SEAL_VERIFIER_CMD``: command that accepts a sealed PDF path as its
  final argument and exits 0 only when every embedded QR seal verifies.

The test creates a small PDF letter, asks the configured generator to add the QR
seals, and then validates the sealed PDF with the configured verifier.
"""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

import pytest


_MINIMAL_LETTER_PDF = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length 90 >>
stream
BT
/F1 12 Tf
72 720 Td
(QR seal integration letter) Tj
0 -18 Td
(Every generated seal must validate.) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000241 00000 n 
0000000311 00000 n 
trailer
<< /Root 1 0 R /Size 6 >>
startxref
451
%%EOF
"""


def _configured_command(name: str) -> list[str]:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"{name} is not configured for the PDF QR seal integration test")
    return shlex.split(value)


def _run(command: list[str], *paths: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*command, *(str(path) for path in paths)],
        check=False,
        text=True,
        capture_output=True,
    )


@pytest.mark.integration
def test_generated_pdf_qr_seals_validate_with_verifier(tmp_path: Path) -> None:
    """Generate QR seals for a PDF letter and verify every generated seal."""

    generator = _configured_command("PDF_QR_SEAL_GENERATOR_CMD")
    verifier = _configured_command("PDF_QR_SEAL_VERIFIER_CMD")
    source_pdf = tmp_path / "letter.pdf"
    sealed_pdf = tmp_path / "letter.sealed.pdf"
    source_pdf.write_bytes(_MINIMAL_LETTER_PDF)

    generated = _run(generator, source_pdf, sealed_pdf)

    assert generated.returncode == 0, generated.stderr or generated.stdout
    assert sealed_pdf.exists(), "QR seal generator did not write the sealed PDF"
    assert sealed_pdf.stat().st_size > source_pdf.stat().st_size, "sealed PDF should include QR seal data"

    verified = _run(verifier, sealed_pdf)

    assert verified.returncode == 0, verified.stderr or verified.stdout
