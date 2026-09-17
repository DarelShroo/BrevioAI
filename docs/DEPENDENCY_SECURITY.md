# Dependency Security Verification (P0)

## Status

```text
DEPENDENCY SECURITY VERIFICATION: FINDINGS PRESENT
```

Previous interim state (before a successful audit run):

```text
DEPENDENCY SECURITY VERIFICATION PENDING
```

## Evidence (real execution)

- **Date:** 2026-09-15
- **Production requirements file:** `core/requirements.txt`
- **Production install path:** `core/Dockerfile` (Python **3.12**-slim-bookworm)
- **Command (authoritative):**

```bash
docker run --rm \
  -v "$PWD/core/requirements.txt:/req.txt:ro" \
  python:3.12-slim-bookworm bash -lc '
    apt-get update -qq
    apt-get install -y -qq --no-install-recommends libxml2-dev libxslt1-dev gcc
    pip install -q --upgrade pip "setuptools==83.0.0" wheel pip-audit
    printf "setuptools>=83\n" > /tmp/c.txt
    pip install -q --build-constraint /tmp/c.txt -r /req.txt
    pip-audit --progress-spinner off -f columns
  '
```

- **Exit code:** `1` (vulnerabilities reported)
- **Result line:** `Found 29 known vulnerabilities in 2 packages`
- **Artifacts (local, gitignored):** `tmp_pip_audit/pip_audit_columns.txt`, `tmp_pip_audit/prod_freeze.txt`

Auditing `-r requirements.txt --disable-pip --no-deps` alone is **invalid** here when lines are unpinned; the authoritative check is `pip-audit` against the **installed** production closure on Python 3.12.

## Safe upgrades applied in this P0

Pinned / bumped in `core/requirements.txt` (non-exhaustive): click, filelock, h11/h2/hpack/httpcore, idna, lxml, Markdown, pillow, Pygments, PyJWT, pypdf, python-dotenv, python-multipart, requests, soupsieve, urllib3, yt-dlp, and previously unpinned motor/celery/aiofiles/cryptography/etc. HuggingFace/transformers/tokenizers/safetensors were removed from production (token estimates use tiktoken only).

`core/Dockerfile` setuptools pin moved to `83.0.0` (prod image does not install Whisper). `Dockerfile.dev` keeps setuptools `<81` for Whisper/`pkg_resources`.

## Remaining findings (not auto-upgraded)

| Package | Installed | Why not bumped in P0 | Fix direction |
| --- | --- | --- | --- |
| `starlette` | 0.46.2 | Tied to `fastapi==0.115.12`; needs coordinated FastAPI upgrade | FastAPI + Starlette ≥0.47.2 / 1.x |

Unique advisory IDs remaining: re-run `pip-audit` after image rebuild (transformers stack removed from prod).

## Re-verification

After FastAPI upgrades, re-run the Docker command above and update this file's **Status** line to either:

- `DEPENDENCY SECURITY VERIFICATION: VERIFIED — NO KNOWN VULNERABILITIES FOUND`, or
- keep `FINDINGS PRESENT` with an updated table.
