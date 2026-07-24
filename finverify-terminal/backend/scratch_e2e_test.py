"""End-to-end test: 5 live financial queries through the new inference pipeline."""
import httpx
import json
import sys

BASE = "http://127.0.0.1:8000"

# Health check first
r = httpx.get(f"{BASE}/health", timeout=10)
sys.stdout.buffer.write(f"HEALTH: {r.json()}\n\n".encode("utf-8", "replace"))

QUESTIONS = [
    "What was Apple's revenue growth?",
    "What was Tesla's operating margin?",
    "What was Microsoft's EPS?",
    "What was NVIDIA's gross margin?",
    "What was Amazon's free cash flow?",
]

results = []
for i, q in enumerate(QUESTIONS, 1):
    sys.stdout.buffer.write(f"--- QUERY {i}: {q} ---\n".encode())
    try:
        r = httpx.post(f"{BASE}/query", json={"question": q}, timeout=30)
        data = r.json()
        raw_text = data.get("raw_text", "")
        raw_num = data.get("raw_number")
        verified = data.get("verified_number")
        trust = data.get("trust_score")
        display = data.get("display_value")
        mode = data.get("mode")
        corrections = data.get("correction_log", [])

        sys.stdout.buffer.write(f"  Status:     {r.status_code}\n".encode())
        sys.stdout.buffer.write(f"  raw_text:   {repr(raw_text[:100])}\n".encode())
        sys.stdout.buffer.write(f"  raw_number: {raw_num}\n".encode())
        sys.stdout.buffer.write(f"  verified:   {verified}\n".encode())
        sys.stdout.buffer.write(f"  trust:      {trust}\n".encode())
        sys.stdout.buffer.write(f"  display:    {display}\n".encode())
        sys.stdout.buffer.write(f"  mode:       {mode}\n".encode())
        sys.stdout.buffer.write(f"  corrections:{corrections}\n\n".encode())
        results.append({"q": q, "raw_num": raw_num, "verified": verified, "raw_text": raw_text})
    except Exception as e:
        sys.stdout.buffer.write(f"  ERROR: {e}\n\n".encode())
        results.append({"q": q, "raw_num": None, "error": str(e)})

# Analysis
sys.stdout.buffer.write(b"\n=== COLLAPSE ANALYSIS ===\n")
raw_nums = [r["raw_num"] for r in results if r.get("raw_num") is not None]
verified_nums = [r["verified"] for r in results if r.get("verified") is not None]
raw_texts = [r["raw_text"] for r in results if r.get("raw_text")]

sys.stdout.buffer.write(f"raw_numbers:    {raw_nums}\n".encode())
sys.stdout.buffer.write(f"unique raw:     {len(set(raw_nums))}/{len(raw_nums)}\n".encode())
sys.stdout.buffer.write(f"verified:       {verified_nums}\n".encode())
sys.stdout.buffer.write(f"unique verified:{len(set(verified_nums))}/{len(verified_nums)}\n".encode())

if len(set(raw_nums)) > 1:
    sys.stdout.buffer.write(b"\nVERDICT: OUTPUTS ARE DIFFERENT -- no collapse detected\n")
elif len(raw_nums) > 0:
    sys.stdout.buffer.write(b"\nVERDICT: ALL OUTPUTS IDENTICAL -- model may still be collapsing\n")
