import logging
from typing import Optional

import markdown
from weasyprint import CSS, HTML

logger = logging.getLogger(__name__)


class PdfService:
    def __init__(self) -> None:
        self.css = CSS(
            string="""
            @page {
                margin: 2cm;
                @bottom-right {
                    content: counter(page);
                    font-family: 'Helvetica', sans-serif;
                    font-size: 9pt;
                }
            }
            body {
                font-family: 'Helvetica', 'Arial', sans-serif;
                font-size: 11pt;
                line-height: 1.6;
                color: #333;
            }
            h1, h2, h3, h4, h5, h6 {
                color: #2c3e50;
                margin-top: 1.5em;
                margin-bottom: 0.5em;
                font-weight: bold;
            }
            h1 { font-size: 24pt; border-bottom: 2px solid #eaecef; padding-bottom: 0.3em; }
            h2 { font-size: 18pt; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
            h3 { font-size: 14pt; }
            p { margin-bottom: 1em; text-align: justify; }
            code {
                font-family: 'Courier New', monospace;
                background-color: #f6f8fa;
                padding: 0.2em 0.4em;
                border-radius: 3px;
                font-size: 85%;
            }
            pre {
                background-color: #f6f8fa;
                padding: 16px;
                overflow: auto;
                border-radius: 6px;
                margin-bottom: 1em;
            }
            pre code {
                background-color: transparent;
                padding: 0;
                font-size: 100%;
            }
            blockquote {
                margin: 0;
                padding: 0 1em;
                color: #6a737d;
                border-left: 0.25em solid #dfe2e5;
            }
            ul, ol { padding-left: 2em; margin-bottom: 1em; }
            li { margin-bottom: 0.5em; }
            table {
                border-collapse: collapse;
                width: 100%;
                margin-bottom: 1em;
            }
            th, td {
                border: 1px solid #dfe2e5;
                padding: 6px 13px;
            }
            th { background-color: #f6f8fa; font-weight: bold; }
            tr:nth-child(2n) { background-color: #f8f8f8; }
            a { color: #0366d6; text-decoration: none; }
            a:hover { text-decoration: underline; }
            img { max-width: 100%; height: auto; }
            hr {
                height: 0.25em;
                padding: 0;
                margin: 24px 0;
                background-color: #e1e4e8;
                border: 0;
            }
        """
        )

    def generate_pdf(self, markdown_content: str, output_path: str) -> bool:
        """
        Generates a PDF file from markdown content.

        Args:
            markdown_content: The markdown string to convert.
            output_path: The absolute path where the PDF should be saved.

        Returns:
            True if successful, False otherwise.
        """
        try:
            logger.info(f"Generating PDF at {output_path}")

            # Convert Markdown to HTML
            html_content = markdown.markdown(
                markdown_content,
                extensions=["fenced_code", "codehilite", "tables", "sane_lists"],
            )

            # Wrap in a basic HTML structure
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """

            # Generate PDF
            HTML(string=full_html).write_pdf(output_path, stylesheets=[self.css])

            logger.info(f"PDF generated successfully at {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to generate PDF: {str(e)}", exc_info=True)
            return False
