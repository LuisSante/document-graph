from pathlib import Path
from typing import Optional, Tuple, List
from fuzzywuzzy import fuzz
import re

def iter_pdfs(base_dir: Path):
    return (
        p for p in base_dir.rglob("*")
        if p.is_file() and p.suffix.lower() == ".pdf"
    )

def _norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _intersects(a: List[float], b: List[float], pad: float = 0.0) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ax0 -= pad; ay0 -= pad; ax1 += pad; ay1 += pad
    return not (ax1 < bx0 or bx1 < ax0 or ay1 < by0 or by1 < ay0)

def find_evidence_bbox(
    df_lines,
    page: int,
    para_bbox: List[float],
    evidence: str,
    pad: float = 1.5,
) -> Tuple[Optional[List[float]], Optional[int]]:
    ev = _norm(evidence or "")
    if not ev:
        return None, None

    page_lines = df_lines[df_lines["page"] == page].copy()
    if page_lines.empty:
        return None, None

    cand = []
    for _, r in page_lines.iterrows():
        lb = [float(r["x0"]), float(r["y0"]), float(r["x1"]), float(r["y1"])]
        if _intersects(lb, para_bbox, pad=pad):
            cand.append((r["text"], lb))

    if not cand:
        return None, None

    for txt, lb in cand:
        if ev in _norm(txt):
            return lb, page

    norm_lines = [(_norm(t), b) for t, b in cand]

    max_window = 4 
    for w in range(2, max_window + 1):
        for i in range(0, len(norm_lines) - w + 1):
            chunk_txt = " ".join(norm_lines[i + k][0] for k in range(w))
            if ev in chunk_txt:
                boxes = [norm_lines[i + k][1] for k in range(w)]
                x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
                x1 = max(b[2] for b in boxes); y1 = max(b[3] for b in boxes)
                return [x0, y0, x1, y1], page

    best = (0, None)
    for txt, lb in cand:
        score = fuzz.partial_ratio(ev, _norm(txt))
        if score > best[0]:
            best = (score, lb)

    if best[0] >= 90:
        return best[1], page

    return None, None
