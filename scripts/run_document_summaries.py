#!/usr/bin/env python3
"""Login to Brevio and POST /brevio/summary-documents for each book category.

Discovers folders under ~/Documentos/libros, matches them to Brevio categories,
keeps only styles whose source_types include text/pdf/docx, and submits the
first PDF/DOCX in each folder (sorted by name). Long PDFs are clipped to pages
20-30 (1-based, inclusive) so the benchmark skips front matter / TOC; originals
are never modified. Shorter PDFs are uploaded whole.

Sends the requests. Pass --dry-run to print the plan without POSTing.
"""

from __future__ import annotations

import argparse
import mimetypes
import os
import sys
import tempfile
from pathlib import Path

import httpx
from dotenv import load_dotenv
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

API_URL = os.getenv("BREVIO_API_URL", "http://localhost:8000").rstrip("/")
IDENTITY = os.getenv("BREVIO_BENCHMARK_IDENTITY", "").strip()
PASSWORD = os.getenv("BREVIO_BENCHMARK_PASSWORD", "")
API_KEY = os.getenv("API_KEY", "").strip()
BOOKS_DIR = Path.home() / "Documentos" / "libros"
ACCESS_COOKIE = "brevio_access"
# 1-based inclusive page window used for long PDFs (skips index / front matter).
CLIP_START_PAGE = 20
CLIP_END_PAGE = 30
DOCUMENT_EXTS = {".pdf", ".docx"}
DOCUMENT_SOURCE_TYPES = {"text", "pdf", "docx"}
MEDIA_SOURCE_TYPES = {"video", "audio", "media", "image"}
PREFERRED_LOCAL_MODEL = "qwen3:14b"


def fail(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def source_type_name(item: object) -> str:
    if hasattr(item, "value"):
        item = getattr(item, "value")
    text = str(item).strip().lower()
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    return text


def is_document_style(source_types: list[object]) -> bool:
    names = {source_type_name(item) for item in source_types}
    if not names:
        return False
    if names <= MEDIA_SOURCE_TYPES:
        return False
    return bool(names & DOCUMENT_SOURCE_TYPES)


def pdf_page_count(path: Path) -> int:
    return len(PdfReader(str(path)).pages)


def clip_page_window(total_pages: int) -> tuple[int, int] | None:
    """Return 0-based [start, end) slice, or None to keep the full PDF."""
    if total_pages < CLIP_START_PAGE:
        return None
    start = CLIP_START_PAGE - 1
    end = min(CLIP_END_PAGE, total_pages)
    return start, end


def clip_pdf(path: Path, start: int, end: int, destination: Path) -> Path:
    reader = PdfReader(str(path))
    writer = PdfWriter()
    for index in range(start, end):
        writer.add_page(reader.pages[index])
    with destination.open("wb") as handle:
        writer.write(handle)
    return destination


def first_document(folder: Path) -> Path | None:
    files = [
        path
        for path in sorted(folder.iterdir(), key=lambda item: item.name.lower())
        if path.is_file() and path.suffix.lower() in DOCUMENT_EXTS
    ]
    return files[0] if files else None


def discover_categories(books_dir: Path) -> list[Path]:
    return sorted(
        (path for path in books_dir.iterdir() if path.is_dir() and not path.name.startswith(".")),
        key=lambda item: item.name.lower(),
    )


def unwrap(payload: dict) -> dict:
    data = payload.get("data")
    return data if isinstance(data, dict) else payload


class BrevioClient:
    def __init__(self, base_url: str) -> None:
        self.http = httpx.Client(base_url=base_url, timeout=httpx.Timeout(120.0, connect=20.0))
        self.token = ""

    def close(self) -> None:
        self.http.close()

    def login(self, identity: str, password: str) -> str:
        response = self.http.post("/auth/login", json={"identity": identity, "password": password})
        if response.status_code >= 400:
            fail(f"login HTTP {response.status_code}: {response.text[:500]}")
        token = response.cookies.get(ACCESS_COOKIE) or self.http.cookies.get(ACCESS_COOKIE)
        if not token:
            fail("login ok but no brevio_access cookie")
        self.token = str(token)
        return self.token

    def _headers(self, *, api_key: bool = False) -> dict[str, str]:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if api_key:
            headers["X-API-KEY"] = API_KEY
        return headers

    def get_json(self, path: str, *, api_key: bool = False) -> dict:
        response = self.http.get(path, headers=self._headers(api_key=api_key))
        if response.status_code >= 400:
            fail(f"GET {path} HTTP {response.status_code}: {response.text[:500]}")
        payload = response.json()
        if not isinstance(payload, dict):
            fail(f"GET {path} returned non-object JSON")
        return unwrap(payload)

    def category_styles(self) -> dict[str, list[dict]]:
        payload = self.get_json("/brevio/categories-styles", api_key=True)
        combos = payload.get("advanced_content_combinations") or {}
        if not isinstance(combos, dict):
            fail("categories-styles did not return advanced_content_combinations")
        return combos

    def local_model(self) -> str:
        payload = self.get_json("/brevio/models", api_key=True)
        catalog = payload.get("catalog") or []
        local_ids = [
            str(item.get("id"))
            for item in catalog
            if isinstance(item, dict)
            and item.get("access") == "local"
            and not item.get("requires_api_key")
        ]
        if PREFERRED_LOCAL_MODEL in local_ids:
            return PREFERRED_LOCAL_MODEL
        if local_ids:
            return local_ids[0]
        fail("no local model in /brevio/models; refusing to use a paid model")

    def submit_document(self, document: Path, fields: dict[str, str]) -> dict:
        mime = mimetypes.guess_type(document.name)[0] or "application/octet-stream"
        with document.open("rb") as handle:
            response = self.http.post(
                "/brevio/summary-documents",
                headers=self._headers(),
                files={"files": (document.name, handle, mime)},
                data=fields,
                timeout=None,
            )
        if response.status_code == 401:
            refresh = self.http.post("/auth/refresh")
            token = refresh.cookies.get(ACCESS_COOKIE) or self.http.cookies.get(ACCESS_COOKIE)
            if refresh.status_code >= 400 or not token:
                raise RuntimeError(
                    f"summary-documents HTTP 401 and refresh failed: {refresh.text[:500]}"
                )
            self.token = str(token)
            with document.open("rb") as handle:
                response = self.http.post(
                    "/brevio/summary-documents",
                    headers=self._headers(),
                    files={"files": (document.name, handle, mime)},
                    data=fields,
                    timeout=None,
                )
        if response.status_code >= 400:
            raise RuntimeError(
                f"summary-documents HTTP {response.status_code}: {response.text[:500]}"
            )
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("summary-documents returned non-object JSON")
        return payload


def document_styles_for(combos: dict[str, list[dict]], category: str) -> list[str]:
    styles = []
    for item in combos.get(category, []):
        if not isinstance(item, dict):
            continue
        style = str(item.get("style") or "").strip()
        source_types = item.get("source_types") or []
        if style and is_document_style(source_types):
            styles.append(style)
    return styles


def prepare_input(document: Path, workdir: Path) -> tuple[Path, int, int]:
    if document.suffix.lower() != ".pdf":
        return document, 1, 1
    total = pdf_page_count(document)
    window = clip_page_window(total)
    if window is None:
        return document, total, total
    start, end = window
    pages_used = end - start
    clipped = workdir / f"{document.stem}__benchmark_p{CLIP_START_PAGE}-{end}.pdf"
    clip_pdf(document, start, end, clipped)
    return clipped, total, pages_used


def build_plan(
    books_dir: Path,
    combos: dict[str, list[dict]],
) -> list[dict]:
    plan = []
    known = {name.lower(): name for name in combos}
    for folder in discover_categories(books_dir):
        api_category = known.get(folder.name.lower())
        document = first_document(folder)
        styles = document_styles_for(combos, api_category) if api_category else []
        pages = None
        readable = True
        error = ""
        if api_category is None:
            error = f"folder {folder.name!r} is not a Brevio category"
        elif document is None:
            error = "no pdf/docx in folder"
        else:
            try:
                if document.suffix.lower() == ".pdf":
                    pages = pdf_page_count(document)
            except Exception as exc:
                readable = False
                error = f"cannot read pages: {exc}"
        plan.append(
            {
                "folder": folder.name,
                "category": api_category,
                "document": document,
                "pages": pages,
                "styles": styles,
                "error": error,
                "readable": readable,
            }
        )
    return plan


def print_dry_run(
    plan: list[dict],
    *,
    books_dir: Path,
    model: str,
    language: str,
    summary_levels: list[str],
) -> int:
    print("Brevio Document Benchmark")
    print()
    print(f"Input:\n{books_dir}")
    print()
    print("Categories found:")
    for item in plan:
        print(f"- {item['folder']}")
    print()
    print("Documents:")
    print()
    style_jobs = 0
    for item in plan:
        print(item["folder"])
        if item["error"]:
            print(f"  ✗ {item['error']}")
            print()
            continue
        document = item["document"]
        pages = item["pages"]
        print(f"  ✓ {document.name}")
        if document.suffix.lower() == ".pdf":
            print(f"  ✓ {pages} pages")
            window = clip_page_window(pages or 0)
            if window is None:
                print("  → benchmark input: complete document")
            else:
                start, end = window
                print(
                    f"  → benchmark input: pages {start + 1}-{end} "
                    f"(skip front matter / TOC)"
                )
        else:
            print("  → benchmark input: complete document")
        print(f"  styles: {', '.join(item['styles']) or '(none)'}")
        print()
        style_jobs += len(item["styles"])
    allowed = sorted(
        {
            style
            for item in plan
            for style in item["styles"]
        }
    )
    print("Styles allowed for document:")
    for style in allowed:
        print(f"- {style}")
    print()
    print(f"Model: {model}")
    print(f"Language: {language}")
    print(f"Summary levels: {', '.join(summary_levels)}")
    print()
    print("Execution plan:")
    print()
    for item in plan:
        if item["error"] or not item["styles"]:
            continue
        print(f"{item['category']}:")
        for style in item["styles"]:
            for level in summary_levels:
                print(f"  - {style} @ {level}")
        print()
    total = style_jobs * max(1, len(summary_levels))
    print(f"Total executions: {total}")
    return total


def validate_or_stop(plan: list[dict], books_dir: Path) -> None:
    if not books_dir.is_dir():
        fail(f"books directory does not exist: {books_dir}")
    if not plan:
        fail(f"no category folders in {books_dir}")
    runnable = [item for item in plan if not item["error"] and item["styles"]]
    if not runnable:
        fail("no valid category × document-style combinations")
    for item in runnable:
        if item["document"].suffix.lower() == ".pdf" and item["pages"] is None:
            fail(f"could not count pages for {item['document']}")
        if item["pages"] is not None and item["pages"] < 1:
            fail(f"invalid page count for {item['document']}")


def parse_summary_levels(raw: list[str] | None) -> list[str]:
    if not raw:
        return ["moderate"]
    levels: list[str] = []
    seen: set[str] = set()
    for chunk in raw:
        for part in chunk.split(","):
            level = part.strip().lower()
            if not level or level in seen:
                continue
            seen.add(level)
            levels.append(level)
    return levels or ["moderate"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan without calling POST /brevio/summary-documents.",
    )
    parser.add_argument("--language", default="ENGLISH", help="Prompt language enum name, e.g. ENGLISH")
    parser.add_argument(
        "--summary-level",
        action="append",
        dest="summary_levels",
        help=(
            "Summary depth. Pass multiple times or comma-separated "
            "(e.g. --summary-level very_concise,moderate,very_detailed). "
            "Default: moderate."
        ),
    )
    parser.add_argument("--format", dest="output_format", default="markdown")
    parser.add_argument("--model", default="", help="Override model id. Must be local unless you pass this.")
    parser.add_argument("--books-dir", type=Path, default=BOOKS_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    books_dir = args.books_dir.expanduser()
    summary_levels = parse_summary_levels(args.summary_levels)
    if not IDENTITY or not PASSWORD:
        fail("set BREVIO_BENCHMARK_IDENTITY and BREVIO_BENCHMARK_PASSWORD")
    if not API_KEY:
        fail("set API_KEY (needed for /brevio/categories-styles)")
    if not books_dir.is_dir():
        fail(f"books directory does not exist: {books_dir}")

    client = BrevioClient(API_URL)
    try:
        print(f"Login as {IDENTITY} @ {API_URL}")
        client.login(IDENTITY, PASSWORD)
        print("Token: brevio_access cookie + Authorization Bearer")
        combos = client.category_styles()
        model = args.model.strip() or client.local_model()
        if args.model.strip():
            print(f"Using explicit model {model}")
        else:
            print(f"Using local model {model}")

        plan = build_plan(books_dir, combos)
        total = print_dry_run(
            plan,
            books_dir=books_dir,
            model=model,
            language=args.language,
            summary_levels=summary_levels,
        )
        validate_or_stop(plan, books_dir)
        if args.dry_run:
            print()
            print("Dry-run only. Re-run without --dry-run to submit POST /brevio/summary-documents.")
            return 0

        print()
        print(f"Submitting {total} request(s)...")
        with tempfile.TemporaryDirectory(prefix="brevio-doc-bench-") as tmp:
            workdir = Path(tmp)
            for item in plan:
                if item["error"]:
                    print(f"SKIP {item['folder']}: {item['error']}")
                    continue
                try:
                    upload, total_pages, pages_used = prepare_input(item["document"], workdir)
                except Exception as exc:
                    print(f"FAIL {item['folder']}: cannot prepare document ({exc})")
                    continue
                for style in item["styles"]:
                    for summary_level in summary_levels:
                        fields = {
                            "language": args.language.upper(),
                            "model": model,
                            "category": item["category"],
                            "style": style,
                            "format": args.output_format,
                            "summary_level": summary_level,
                        }
                        label = f"{item['category']} + {style} @ {summary_level}"
                        try:
                            payload = client.submit_document(upload, fields)
                            print(
                                f"OK   {label}  "
                                f"file={upload.name} pages={pages_used}/{total_pages} "
                                f"task={payload.get('task_id')} "
                                f"entry={payload.get('folder_entry_id')}"
                            )
                        except Exception as exc:
                            print(f"FAIL {label}: {exc}")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
