from pathlib import Path

def iter_pdfs(base_dir: Path):
    return (
        p for p in base_dir.rglob("*")
        if p.is_file() and p.suffix.lower() == ".pdf"
    )