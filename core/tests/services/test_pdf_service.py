import os
from pathlib import Path

import pytest

from core.brevio.services.pdf_service import PdfService


class TestPdfService:
    @pytest.fixture
    def pdf_service(self) -> PdfService:
        return PdfService()

    def test_generate_pdf_success(
        self, pdf_service: PdfService, tmp_path: Path
    ) -> None:
        # Arrange
        markdown_content = "# Hello World\n\nThis is a test."
        output_path = tmp_path / "test.pdf"

        # Act
        result = pdf_service.generate_pdf(markdown_content, str(output_path))

        # Assert
        assert result is True
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0

    def test_generate_pdf_with_code_block(
        self, pdf_service: PdfService, tmp_path: Path
    ) -> None:
        # Arrange
        markdown_content = """
# Code Test

```python
def hello():
    print("world")
```
        """
        output_path = tmp_path / "code_test.pdf"

        # Act
        result = pdf_service.generate_pdf(markdown_content, str(output_path))

        # Assert
        assert result is True
        assert os.path.exists(output_path)
