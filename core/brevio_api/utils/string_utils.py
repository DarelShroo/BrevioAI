def secure_filename(filename: str | bytes) -> str:
    if isinstance(filename, bytes):
        filename = filename.decode("utf-8", errors="replace")
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
