import os
import zipfile
from pathlib import Path

ALLOWED_EXTENSIONS = {
    ".html", ".htm", ".css", ".js", ".json", ".txt", ".md",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".xml", ".webmanifest", ".map", ".pdf",
}

MAX_ZIP_SIZE = 50 * 1024 * 1024  # 50MB
MAX_EXTRACTED_SIZE = 100 * 1024 * 1024  # 100MB


class ZipValidationError(Exception):
    pass


def validate_and_extract(zip_path: Path, dest_dir: Path) -> dict:
    if zip_path.stat().st_size > MAX_ZIP_SIZE:
        raise ZipValidationError(f"ZIP file exceeds {MAX_ZIP_SIZE // (1024*1024)}MB limit")

    if not zipfile.is_zipfile(zip_path):
        raise ZipValidationError("File is not a valid ZIP archive")

    dest_dir.mkdir(parents=True, exist_ok=True)
    file_count = 0
    total_size = 0

    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            # Skip directories
            if info.is_dir():
                continue

            # Skip macOS metadata and hidden files
            name = Path(info.filename).name
            if info.filename.startswith("__MACOSX/") or name.startswith("."):
                continue

            # Reject path traversal
            member_path = Path(info.filename)
            if ".." in member_path.parts:
                raise ZipValidationError(f"Path traversal detected: {info.filename}")

            # Check extension
            ext = member_path.suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise ZipValidationError(
                    f"Disallowed file type: {ext} ({info.filename}). "
                    f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
                )

            total_size += info.file_size
            if total_size > MAX_EXTRACTED_SIZE:
                raise ZipValidationError(
                    f"Extracted size exceeds {MAX_EXTRACTED_SIZE // (1024*1024)}MB limit"
                )

            file_count += 1

        # Extract all files
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = Path(info.filename).name
            if info.filename.startswith("__MACOSX/") or name.startswith("."):
                continue
            target = dest_dir / info.filename
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                dst.write(src.read())

    if file_count == 0:
        raise ZipValidationError("ZIP archive is empty")

    # Check for index.html (at root or one level deep)
    has_index = (dest_dir / "index.html").exists()
    if not has_index:
        # Check one level deep (common pattern: zip contains a folder)
        for child in dest_dir.iterdir():
            if child.is_dir() and (child / "index.html").exists():
                # Move contents up one level
                for item in child.iterdir():
                    item.rename(dest_dir / item.name)
                child.rmdir()
                has_index = True
                break

    if not has_index:
        raise ZipValidationError("No index.html found in ZIP root (or first subfolder)")

    return {"file_count": file_count, "total_size": total_size}


def get_text_files(deploy_dir: Path) -> list[dict]:
    """Read text file contents for AI analysis."""
    text_extensions = {".html", ".htm", ".css", ".js", ".json", ".txt", ".md", ".xml", ".svg"}
    files = []
    for root, _, filenames in os.walk(deploy_dir):
        for fname in filenames:
            fpath = Path(root) / fname
            if fpath.suffix.lower() in text_extensions:
                try:
                    content = fpath.read_text(errors="replace")
                    rel_path = fpath.relative_to(deploy_dir)
                    # Limit per-file size for AI context
                    if len(content) > 50_000:
                        content = content[:50_000] + "\n... [truncated]"
                    files.append({"path": str(rel_path), "content": content})
                except Exception:
                    pass
    return files


def get_file_metadata(deploy_dir: Path) -> dict:
    """Get metadata (no file contents) for cost estimation."""
    file_types: dict[str, int] = {}
    total_size = 0
    file_count = 0
    for root, _, filenames in os.walk(deploy_dir):
        for fname in filenames:
            fpath = Path(root) / fname
            ext = fpath.suffix.lower() or "(no ext)"
            file_types[ext] = file_types.get(ext, 0) + 1
            total_size += fpath.stat().st_size
            file_count += 1
    return {
        "file_count": file_count,
        "total_size_bytes": total_size,
        "file_types": file_types,
    }
