"""
DVL Decision Logic Diagnostic
==============================
Traces every DVL decision for demo questions and live LLM queries.
No code changes — investigation only.
"""
import sys
import httpx
from app.dvl import full_verify, RATIO_KEYWORDS, is_correct
from app.parser import clean_llm_output
from app.router import classify_query

BASE = "http://127.0.0.1:8000"

def pr(msg):
    sys.stdout.buffer.write((msg + "\n").encode("utf-8", "replace"))

# ===================================================================
# PART 1: Trace the sample/demo questions WITH ground truth
# These are the hardcoded samples from /sample-queries
# ===================================================================

pr("=" * 70)
pr("PART 1: DEMO QUESTIONS WITH GROUND TRUTH")
pr("=" * 70)

demo_cases = [
    {
        "question": "What was JPMorgan's CET1 ratio change?",
        "predicted": 0.07004,
        "actual": 0.10935,
        "description": "Reasoning error case from paper",
    },
    {
        "question": "What was the increase in Class A shares outstanding?",
        "predicted": 104.0,
        "actual": 995.0,
        "description": "Magnitude error case from paper",
    },
    {
        "question": "What was the percentage decrease in HTM securities?",
        "predicted": -34.11,
        "actual": 0.34146,
        "description": "Compound error (scale + sign) from paper",
    },
]

for i, case in enumerate(demo_cases, 1):
    q = case["question"]
    pred = case["predicted"]
    actual = case["actual"]
    q_lower = q.lower()

    # Trace keyword matching
    matched_keywords = [kw for kw in RATIO_KEYWORDS if kw in q_lower]
    is_ratio = len(matched_keywords) > 0
    mode = classify_query(q)

    pr(f"\n--- DEMO CASE {i}: {case['description']} ---")
    pr(f"  Question:   {q}")
    pr(f"  Predicted:  {pred}")
    pr(f"  Actual:     {actual}")
    pr(f"  Mode:       {mode}")
    pr(f"  is_ratio:   {is_ratio}")
    pr(f"  Keywords:   {matched_keywords}")

    # Trace scale decision
    if is_ratio:
        if abs(pred) > 100:
            pr(f"  Scale path: abs({pred}) > 100 -> would try div100 = {pred/100}")
            div_candidate = pred / 100
            if is_correct(div_candidate, actual) or is_correct(-div_candidate, actual):
                pr(f"    -> div100 VALIDATES against actual ({actual})")
            else:
                pr(f"    -> div100 does NOT validate against actual")
        elif abs(pred) < 1:
            pr(f"  Scale path: abs({pred}) < 1 -> would try mul100 = {pred*100}")
            mul_candidate = pred * 100
            if is_correct(mul_candidate, actual) or is_correct(-mul_candidate, actual):
                pr(f"    -> mul100 VALIDATES against actual ({actual})")
            else:
                pr(f"    -> mul100 does NOT validate against actual")
        else:
            pr(f"  Scale path: abs({pred}) in [1, 100] -> AMBIGUOUS range, try both")
            div_r = pred / 100
            mul_r = pred * 100
            pr(f"    div100 = {div_r}, mul100 = {mul_r}")
            if is_correct(div_r, actual) or is_correct(-div_r, actual):
                pr(f"    -> div100 VALIDATES (with sign lookahead)")
            elif is_correct(mul_r, actual) or is_correct(-mul_r, actual):
                pr(f"    -> mul100 VALIDATES (with sign lookahead)")
            else:
                pr(f"    -> neither validates, leave unchanged")
    else:
        pr(f"  Scale path: NOT a ratio question, skip scale correction entirely")

    # Run actual DVL
    verified, log, label, color = full_verify(q, pred, actual)
    rules = [e["rule"] for e in log]
    pr(f"  DVL result: verified={verified}, rules={rules}, trust={label}")
    pr(f"  Correct?    {is_correct(verified, actual)}")

# ===================================================================
# PART 2: Live LLM queries WITHOUT ground truth (production path)
# This is what actually happens when a user asks a question
# ===================================================================

pr("\n" + "=" * 70)
pr("PART 2: LIVE LLM QUERIES WITHOUT GROUND TRUTH")
pr("=" * 70)

questions = [
    "What was Apple's revenue growth?",
    "What was Tesla's operating margin?",
    "What was Microsoft's EPS?",
    "What was NVIDIA's gross margin?",
    "What was Amazon's free cash flow?",
    "What was JPMorgan's CET1 ratio?",
    "What was the percentage decrease in HTM securities?",
    "What was the increase in Class A shares outstanding?",
]

for i, q in enumerate(questions, 1):
    q_lower = q.lower()
    matched_keywords = [kw for kw in RATIO_KEYWORDS if kw in q_lower]
    is_ratio = len(matched_keywords) > 0
    mode = classify_query(q)

    # Get live LLM output
    try:
        r = httpx.post(f"{BASE}/query", json={"question": q}, timeout=30)
        data = r.json()
    except Exception as e:
        pr(f"\n--- LIVE {i}: {q} ---")
        pr(f"  ERROR: {e}")
        continue

    raw_text = data.get("raw_text", "")
    raw_number = data.get("raw_number")
    verified_number = data.get("verified_number")
    trust = data.get("trust_score")
    corrections = data.get("correction_log", [])
    display = data.get("display_value")

    pr(f"\n--- LIVE {i}: {q} ---")
    pr(f"  Mode:       {mode}")
    pr(f"  is_ratio:   {is_ratio} (keywords: {matched_keywords})")
    pr(f"  LLM output: {repr(raw_text[:100])}")
    pr(f"  raw_number: {raw_number}")

    if raw_number is not None and is_ratio:
        # Trace which heuristic path would fire WITHOUT ground truth
        if abs(raw_number) > 100:
            pr(f"  Heuristic:  abs({raw_number}) > 100 -> FIRES scale_div100 = {raw_number/100}")
            pr(f"              THIS IS THE AGGRESSIVE RULE")
        elif abs(raw_number) < 1:
            pr(f"  Heuristic:  abs({raw_number}) < 1 -> FIRES scale_mul100 = {raw_number*100}")
        else:
            pr(f"  Heuristic:  abs({raw_number}) in [1,100] -> AMBIGUOUS, no correction")
    elif raw_number is not None:
        pr(f"  Heuristic:  not a ratio question, no scale correction")

    pr(f"  verified:   {verified_number}")
    pr(f"  trust:      {trust}")
    pr(f"  corrections:{[c['rule'] for c in corrections]}")
    pr(f"  display:    {display}")

    # Assess correctness
    if corrections:
        pr(f"  ASSESSMENT: DVL modified the value")
        for c in corrections:
            pr(f"    {c['rule']}: {c['before']} -> {c['after']}")
    else:
        pr(f"  ASSESSMENT: DVL left value unchanged (no correction fired)")
