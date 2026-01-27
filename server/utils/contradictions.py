import os
import json
from typing import Optional, Dict, Any

from openai import OpenAI
from .static import TYPE_PRIORITY
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM = """You are a careful legal analyst.
Your job: detect HARD contradictions between two contract paragraphs.
Return JSON only. No extra text.
"""

USER_TMPL = """Paragraph A:
{a}

Paragraph B:
{b}

Task:
1) Decide if A and B are contradictory (hard conflict, mutually exclusive).
2) If contradictory, classify type:
- deontic (shall/must/may/shall not)
- numeric (amounts, dates, days, caps)
- scope (only/except/notwithstanding/subject to)
- definition (term meaning conflict)
- precedence (order of precedence between docs/exhibits)
- other
3) Provide evidence snippets (exact substrings) from A and B.

Return JSON with:
{{
  "label": "contradiction" | "neutral",
  "type": "...",
  "confidence": 0.0-1.0,
  "evidence": {{
     "source": "exact snippet from A or empty",
     "target": "exact snippet from B or empty"
  }},
  "summary": "one-line reason"
}}
"""

def classify_contradiction(a: str, b: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER_TMPL.format(a=a, b=b)},
        ],
        max_tokens=350,
    )
    txt = resp.choices[0].message.content.strip()
    return json.loads(txt)


def rank_score(result: dict, edge_type: str, sim_score: Optional[float]) -> float:
    base = float(result.get("confidence", 0.0))
    t = str(result.get("type", "other")).lower()
    pri = TYPE_PRIORITY.get(t, 1)

    bonus_ref = 0.10 if edge_type.startswith("reference") else 0.0
    bonus_sim = 0.05 if (edge_type == "semantic_similarity" and (sim_score or 0) > 0.85) else 0.0

    return base + 0.05 * pri + bonus_ref + bonus_sim


def postfilter_and_rank(candidates: list[dict]) -> list[dict]:
    kept = []
    for c in candidates:
        if c["result"].get("label") != "contradiction":
            continue
        if float(c["result"].get("confidence", 0.0)) < 0.75:
            continue
        c["final_score"] = rank_score(c["result"], c["edge_type"], c.get("edge_score"))
        kept.append(c)

    kept.sort(key=lambda x: x["final_score"], reverse=True)
    return kept
