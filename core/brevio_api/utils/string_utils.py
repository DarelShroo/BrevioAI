def secure_filename(filename: str | bytes) -> str:
    if isinstance(filename, bytes):
        filename = filename.decode("utf-8", errors="replace")
    return "".join(
        str(c) if str(c).isalnum() or str(c) in "._-" else "_" for c in filename
    )
