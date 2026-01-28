import os
import json
import re 
from typing import Optional, Dict, Any

from openai import OpenAI
from .static import TYPE_PRIORITY
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM = """You are a careful legal analyst.
Your job: detect HARD contradictions between two contract paragraphs.
Return ONLY a valid JSON object. Do not include markdown blocks, explanations or any text outside the JSON."""

USER_TMPL = """Paragraph A:
{a}

Paragraph B:
{b}

Task:
1) Decide if A and B are contradictory (hard conflict, mutually exclusive).
2) If contradictory, classify type:
- deontic, numeric, scope, definition, precedence, other.
3) Provide evidence snippets (exact substrings) from A and B.

Return JSON with this structure:
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
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": USER_TMPL.format(a=a, b=b)},
            ],
            max_tokens=350,
            response_format={ "type": "json_object" }
        )
        
        txt = resp.choices[0].message.content.strip()
        
        if txt.startswith("```"):
            txt = re.sub(r'^```json\s*|```$', '', txt, flags=re.MULTILINE).strip()
        
        return json.loads(txt)

    except json.JSONDecodeError as e:
        print(f"Error parseando JSON del LLM: {e}. Texto recibido: {txt}")
        return {
            "label": "neutral",
            "type": "other",
            "confidence": 0.0,
            "evidence": {"source": "", "target": ""},
            "summary": "Error de formato en la respuesta de IA"
        }
    except Exception as e:
        print(f"Error inesperado en clasificación: {e}")
        return {"label": "neutral", "confidence": 0.0}

def rank_score(result: dict, edge_type: str, sim_score: Optional[float]) -> float:
    base = float(result.get("confidence", 0.0))
    t = str(result.get("type", "other")).lower()
    pri = TYPE_PRIORITY.get(t, 1)

    bonus_ref = 0.10 if edge_type.startswith("reference") else 0.0
    bonus_sim = 0.05 if (edge_type == "semantic_similarity" and (sim_score or 0) > 0.85) else 0.0

    return base + (0.05 * pri) + bonus_ref + bonus_sim

def postfilter_and_rank(candidates: list[dict]) -> list[dict]:
    kept = []
    for c in candidates:
        res = c.get("result", {})
        if res.get("label") != "contradiction":
            continue
        
        if float(res.get("confidence", 0.0)) < 0.75:
            continue
            
        c["final_score"] = rank_score(res, c["edge_type"], c.get("edge_score"))
        kept.append(c)

    kept.sort(key=lambda x: x.get("final_score", 0), reverse=True)
    return kept