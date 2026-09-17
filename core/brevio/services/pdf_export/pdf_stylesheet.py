"""Print stylesheet for PDF export.

Visual identity matches ``frontend/src/assets/styles/markdown-viewer.css``
(``.markdown-body``) while adding pagination and overflow rules that only
make sense on paper.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from core.brevio.services.pdf_export.highlight import pygments_css

logger = logging.getLogger(__name__)

CSS_PATH = Path(__file__).with_name("pdf_styles.css")

_FONT_DIRS = (
    Path("/usr/share/fonts/truetype/noto"),
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/truetype/liberation"),
    Path("/usr/share/fonts/truetype/freefont"),
    Path("/usr/local/share/fonts"),
    Path("/usr/share/fonts"),
)

_SANS_REGULAR = (
    "NotoSans-Regular.ttf",
    "DejaVuSans.ttf",
    "LiberationSans-Regular.ttf",
    "FreeSans.ttf",
)
_SANS_BOLD = (
    "NotoSans-Bold.ttf",
    "DejaVuSans-Bold.ttf",
    "LiberationSans-Bold.ttf",
    "FreeSansBold.ttf",
)
_SANS_ITALIC = (
    "NotoSans-Italic.ttf",
    "DejaVuSans-Oblique.ttf",
    "LiberationSans-Italic.ttf",
    "FreeSansOblique.ttf",
)
_SANS_BOLD_ITALIC = (
    "NotoSans-BoldItalic.ttf",
    "DejaVuSans-BoldOblique.ttf",
    "LiberationSans-BoldItalic.ttf",
    "FreeSansBoldOblique.ttf",
)
_MONO_REGULAR = (
    "NotoSansMono-Regular.ttf",
    "NotoMono-Regular.ttf",
    "DejaVuSansMono.ttf",
    "LiberationMono-Regular.ttf",
    "FreeMono.ttf",
)
_MONO_BOLD = (
    "NotoSansMono-Bold.ttf",
    "DejaVuSansMono-Bold.ttf",
    "LiberationMono-Bold.ttf",
    "FreeMonoBold.ttf",
)


def _find_font(names: tuple[str, ...]) -> Path | None:
    for directory in _FONT_DIRS:
        if not directory.exists():
            continue
        for name in names:
            direct = directory / name
            if direct.is_file():
                return direct
        for name in names:
            matches = list(directory.rglob(name))
            if matches:
                return matches[0]
    return None


def _font_face(family: str, path: Path, weight: str, style: str) -> str:
    url = path.resolve().as_uri()
    return (
        "@font-face {\n"
        f'  font-family: "{family}";\n'
        f"  src: url(\"{url}\");\n"
        f"  font-weight: {weight};\n"
        f"  font-style: {style};\n"
        "  font-display: swap;\n"
        "}\n"
    )


def build_font_face_css() -> str:
    faces: list[str] = []
    mapping = (
        ("Brevio Sans", _SANS_REGULAR, "400", "normal"),
        ("Brevio Sans", _SANS_BOLD, "700", "normal"),
        ("Brevio Sans", _SANS_ITALIC, "400", "italic"),
        ("Brevio Sans", _SANS_BOLD_ITALIC, "700", "italic"),
        ("Brevio Mono", _MONO_REGULAR, "400", "normal"),
        ("Brevio Mono", _MONO_BOLD, "700", "normal"),
    )
    found: list[str] = []
    for family, names, weight, style in mapping:
        path = _find_font(names)
        if path is None:
            continue
        faces.append(_font_face(family, path, weight, style))
        found.append(f"{family}:{weight}:{style}={path.name}")
    if found:
        logger.info("PDF_CSS_LOADED fonts=%s", ",".join(found))
    else:
        logger.warning(
            "PDF_CSS_LOADED no embedded font files found; using system fontconfig fallback"
        )
    return "\n".join(faces)


@lru_cache(maxsize=1)
def load_pdf_stylesheet() -> str:
    if not CSS_PATH.is_file():
        raise FileNotFoundError(f"PDF stylesheet missing: {CSS_PATH}")
    css = CSS_PATH.read_text(encoding="utf-8")
    fonts = build_font_face_css()
    token_css = pygments_css()
    combined = "\n".join(part for part in (fonts, css, token_css) if part)
    logger.info(
        "PDF_CSS_LOADED path=%s css_chars=%s has_fonts=%s",
        CSS_PATH,
        len(combined),
        bool(fonts),
    )
    return combined
