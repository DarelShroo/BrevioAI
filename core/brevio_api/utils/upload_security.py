"""Upload hardening: filename sanitization, size/count limits, magic bytes."""

from __future__ import annotations

import os
import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from fastapi import HTTPException, UploadFile, status

from core.shared.utils.environment import env_flag, env_int

# Infrastructure ceiling defaults: must not reject Business plan video (10 GiB).
# Prefer commercial registry max when available; env overrides still win.
DEFAULT_MAX_UPLOAD_BYTES = 10 * 1024 * 1024 * 1024  # 10 GiB per file
DEFAULT_MAX_UPLOAD_FILES = 10
DEFAULT_MAX_TOTAL_UPLOAD_BYTES = 10 * 1024 * 1024 * 1024  # 10 GiB per request


def _commercial_upload_ceiling() -> int:
    try:
        from core.brevio_api.services.billing.plan_registry import (
            max_commercial_upload_bytes,
        )

        return max_commercial_upload_bytes()
    except Exception:
        return DEFAULT_MAX_UPLOAD_BYTES


def max_upload_bytes() -> int:
    # Env override; otherwise commercial max across plans.
    if os.getenv("MAX_UPLOAD_BYTES"):
        return max(1, env_int("MAX_UPLOAD_BYTES", DEFAULT_MAX_UPLOAD_BYTES))
    return max(1, _commercial_upload_ceiling())


def max_upload_files() -> int:
    return max(1, env_int("MAX_UPLOAD_FILES", DEFAULT_MAX_UPLOAD_FILES))


def max_total_upload_bytes() -> int:
    if os.getenv("MAX_TOTAL_UPLOAD_BYTES"):
        return max(1, env_int("MAX_TOTAL_UPLOAD_BYTES", DEFAULT_MAX_TOTAL_UPLOAD_BYTES))
    return max(1, _commercial_upload_ceiling())


_UNSAFE_FILENAME_CHARS = re.compile(r"[^\w.\- ()\[\]]+", re.UNICODE)
_RESERVED_NAMES = frozenset(
    {
        "",
        ".",
        "..",
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{i}" for i in range(1, 10)),
        *(f"lpt{i}" for i in range(1, 10)),
    }
)


def sanitize_upload_filename(filename: str | None, *, fallback: str = "upload") -> str:
    """Return a single-segment safe filename (no path traversal)."""
    raw = (filename or "").strip()
    # Drop any directory components from clients that send absolute/relative paths.
    name = Path(raw.replace("\\", "/")).name.strip()
    if not name or name.lower() in _RESERVED_NAMES:
        name = fallback

    # Collapse consecutive dots used in traversal tricks after basename.
    while ".." in name:
        name = name.replace("..", ".")

    name = _UNSAFE_FILENAME_CHARS.sub("_", name).strip(" ._")
    if not name or name.lower() in _RESERVED_NAMES:
        name = fallback

    # Cap length while preserving a short extension when present.
    if len(name) > 180:
        stem, ext = os.path.splitext(name)
        name = f"{stem[:160]}{ext[:20]}"
    return name


def ensure_path_inside(base_dir: Path, candidate: Path) -> Path:
    """Resolve ``candidate`` and ensure it stays under ``base_dir``."""
    base = base_dir.resolve()
    resolved = candidate.resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path",
        ) from exc
    return resolved


def magic_bytes_enabled() -> bool:
    return env_flag("UPLOAD_MAGIC_BYTES_ENABLED", True)


def _ext(name: str) -> str:
    return Path(name).suffix.lower().lstrip(".")


def _is_pdf(content: bytes) -> bool:
    head = content[:1024].lstrip()
    return head.startswith(b"%PDF-")


def _is_docx(content: bytes) -> bool:
    if not content.startswith(b"PK\x03\x04"):
        return False
    try:
        with zipfile.ZipFile(BytesIO(content)) as zf:
            names = set(zf.namelist())
            return "[Content_Types].xml" in names and any(
                n.startswith("word/") for n in names
            )
    except zipfile.BadZipFile:
        return False


def _is_zip_container(content: bytes) -> bool:
    return content.startswith(b"PK\x03\x04") or content.startswith(b"PK\x05\x06")


def _is_png(content: bytes) -> bool:
    return content.startswith(b"\x89PNG\r\n\x1a\n")


def _is_jpeg(content: bytes) -> bool:
    return content.startswith(b"\xff\xd8\xff")


def _is_gif(content: bytes) -> bool:
    return content.startswith(b"GIF87a") or content.startswith(b"GIF89a")


def _is_webp(content: bytes) -> bool:
    return len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"


def _is_mp3(content: bytes) -> bool:
    if content.startswith(b"ID3"):
        return True
    return len(content) >= 2 and content[0] == 0xFF and (content[1] & 0xE0) == 0xE0


def _is_mp4_family(content: bytes) -> bool:
    if len(content) < 12:
        return False
    return content[4:8] == b"ftyp"


def _is_wav(content: bytes) -> bool:
    return (
        len(content) >= 12
        and content[:4] == b"RIFF"
        and content[8:12] == b"WAVE"
    )


def _is_ogg(content: bytes) -> bool:
    return content.startswith(b"OggS")


def _is_webm_or_mkv(content: bytes) -> bool:
    return content.startswith(b"\x1a\x45\xdf\xa3")


def _is_txt_like(content: bytes) -> bool:
    sample = content[:4096]
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


_EXT_VALIDATORS = {
    "pdf": _is_pdf,
    "docx": _is_docx,
    "png": _is_png,
    "jpg": _is_jpeg,
    "jpeg": _is_jpeg,
    "gif": _is_gif,
    "webp": _is_webp,
    "mp3": _is_mp3,
    "mp4": _is_mp4_family,
    "m4a": _is_mp4_family,
    "mov": _is_mp4_family,
    "wav": _is_wav,
    "ogg": _is_ogg,
    "oga": _is_ogg,
    "webm": _is_webm_or_mkv,
    "mkv": _is_webm_or_mkv,
    "txt": _is_txt_like,
    "md": _is_txt_like,
}


def assert_content_matches_extension(filename: str, content: bytes) -> None:
    """Reject extension/content mismatches (magic-byte check)."""
    if not magic_bytes_enabled():
        return
    ext = _ext(filename)
    validator = _EXT_VALIDATORS.get(ext)
    if validator is None:
        return
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file is not allowed",
        )
    if not validator(content):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File content does not match .{ext} type",
        )
    if ext == "docx" and _is_zip_container(content):
        try:
            with zipfile.ZipFile(BytesIO(content)) as zf:
                if len(zf.namelist()) > 5000:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Document archive is too complex",
                    )
        except zipfile.BadZipFile as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Office document",
            ) from exc


async def read_upload_limited(
    upload: UploadFile,
    *,
    max_bytes: int | None = None,
    validate_magic: bool = True,
) -> Tuple[str, bytes]:
    """Read one upload with a hard size cap; sanitize the client filename."""
    limit = max_bytes if max_bytes is not None else max_upload_bytes()
    safe_name = sanitize_upload_filename(upload.filename)
    chunks: List[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum size of {limit} bytes",
            )
        chunks.append(chunk)
    content = b"".join(chunks)
    if validate_magic:
        assert_content_matches_extension(safe_name, content)
    return safe_name, content


async def read_uploads_limited(
    uploads: Sequence[UploadFile],
    *,
    max_files: int | None = None,
    max_bytes_per_file: int | None = None,
    max_total_bytes: int | None = None,
) -> List[Tuple[str, bytes]]:
    file_limit = max_files if max_files is not None else max_upload_files()
    per_file = max_bytes_per_file if max_bytes_per_file is not None else max_upload_bytes()
    total_limit = (
        max_total_bytes if max_total_bytes is not None else max_total_upload_bytes()
    )

    if not uploads:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one file is required",
        )
    if len(uploads) > file_limit:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Too many files (max {file_limit})",
        )

    results: List[Tuple[str, bytes]] = []
    total = 0
    for upload in uploads:
        name, content = await read_upload_limited(upload, max_bytes=per_file)
        total += len(content)
        if total > total_limit:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Total upload exceeds maximum of {total_limit} bytes",
            )
        results.append((name, content))
    return results


def assert_safe_relative_filenames(names: Iterable[str]) -> None:
    for name in names:
        if name != sanitize_upload_filename(name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename",
            )
