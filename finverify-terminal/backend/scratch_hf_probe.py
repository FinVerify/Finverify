"""
Scratch script: Probe HF model repo + live inference.
This file is for investigation only -- delete after use.
"""
import os
import json
import asyncio
from dotenv import load_dotenv
load_dotenv(".env")

import httpx

TOKEN = os.getenv("HF_TOKEN")
MODEL = "aadi2026/finverify-lora"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL}"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# ── Part 1: Model repo metadata ──────────────────────────────────────

def probe_model_repo():
    print("=" * 60)
    print("PART 1: MODEL REPOSITORY METADATA")
    print("=" * 60)
    r = httpx.get(
        f"https://huggingface.co/api/models/{MODEL}",
        headers=HEADERS,
        timeout=30,
    )
    print(f"Status: {r.status_code}")
    if r.status_code != 200:
        print(f"Response: {r.text[:500]}")
        return

    info = r.json()
    model_id = info.get("modelId", "?")
    pipeline = info.get("pipeline_tag", "?")
    library = info.get("library_name", "?")
    tags = info.get("tags", [])
    print(f"Model ID:     {model_id}")
    print(f"Pipeline tag: {pipeline}")
    print(f"Library:      {library}")
    print(f"Tags:         {tags}")

    print("\nFiles in repo:")
    for s in info.get("siblings", []):
        fname = s.get("rfilename", "?")
        print(f"  - {fname}")

    config = info.get("config", {})
    print(f"\nConfig (truncated): {json.dumps(config, indent=2)[:600]}")


# ── Part 2: Direct HF Inference API calls ────────────────────────────

QUESTIONS = [
    "What was Apple's revenue growth?",
    "What was Tesla's operating margin?",
    "What was Microsoft's EPS?",
    "What was NVIDIA's gross margin?",
    "What was Amazon's free cash flow?",
]


def call_hf_direct(question: str) -> dict:
    """Call HF Inference API directly (bypass FastAPI) and return full details."""
    payload = {
        "inputs": f"Question: {question}\nAnswer:",
        "parameters": {
            "max_new_tokens": 50,
            "do_sample": True,
            "temperature": 0.3,
            "repetition_penalty": 1.15,
            "return_full_text": False,
        },
    }
    result = {
        "question": question,
        "prompt": payload["inputs"],
        "parameters": payload["parameters"],
    }

    try:
        r = httpx.post(API_URL, json=payload, headers=HEADERS, timeout=120)
        result["status_code"] = r.status_code
        result["raw_response_text"] = r.text[:1000]

        if r.status_code == 200:
            data = r.json()
            result["raw_json"] = data
            if isinstance(data, list) and len(data) > 0:
                result["generated_text"] = data[0].get("generated_text", "")
            else:
                result["generated_text"] = str(data)
        else:
            result["generated_text"] = None
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
        result["generated_text"] = None
        print(f"  !!! EXCEPTION: {type(e).__name__}: {e}")

    return result


def run_parser_on(text: str):
    """Run the project's own parser on the generated text."""
    try:
        from app.parser import clean_llm_output
        cleaned, number = clean_llm_output(text)
        return {"cleaned": cleaned, "raw_number": number}
    except Exception as e:
        return {"error": str(e)}


def run_dvl_on(question: str, raw_number):
    """Run the project's DVL on the extracted number."""
    if raw_number is None:
        return {"skipped": "no raw_number to verify"}
    try:
        from app.dvl import full_verify
        verified, log, label, color = full_verify(question, raw_number, None)
        return {
            "verified_value": verified,
            "correction_log": log,
            "trust_label": label,
            "trust_color": color,
        }
    except Exception as e:
        return {"error": str(e)}


def main():
    probe_model_repo()

    print("\n")
    print("=" * 60)
    print("PART 2: LIVE INFERENCE -- 5 DIFFERENT QUESTIONS")
    print("=" * 60)

    all_results = []

    for i, q in enumerate(QUESTIONS, 1):
        print(f"\n{'-' * 60}")
        print(f"QUERY {i}/{len(QUESTIONS)}: {q}")
        print(f"{'-' * 60}")

        result = call_hf_direct(q)
        print(f"  Status:         {result.get('status_code')}")
        print(f"  Prompt:         {result['prompt']!r}")
        print(f"  Raw response:   {result.get('raw_response_text', 'N/A')[:300]}")
        print(f"  Generated text: {result.get('generated_text')!r}")

        # Parse
        gen = result.get("generated_text")
        if gen:
            parsed = run_parser_on(gen)
            result["parsed"] = parsed
            print(f"  Parsed number:  {parsed.get('raw_number')}")

            # DVL
            dvl = run_dvl_on(q, parsed.get("raw_number"))
            result["dvl"] = dvl
            print(f"  DVL verified:   {dvl.get('verified_value')}")
            print(f"  DVL trust:      {dvl.get('trust_label')}")
            print(f"  DVL corrections:{dvl.get('correction_log')}")
        else:
            print(f"  *** No generated_text — cannot parse ***")

        all_results.append(result)

    # ── Part 3: Analysis ─────────────────────────────────────────────
    print("\n")
    print("=" * 60)
    print("PART 3: COLLAPSE ANALYSIS")
    print("=" * 60)

    gen_texts = [r.get("generated_text") for r in all_results if r.get("generated_text")]
    raw_numbers = [
        r["parsed"]["raw_number"]
        for r in all_results
        if r.get("parsed") and r["parsed"].get("raw_number") is not None
    ]

    print(f"\nGenerated texts ({len(gen_texts)}):")
    for i, t in enumerate(gen_texts, 1):
        print(f"  [{i}] {t!r}")

    print(f"\nRaw numbers ({len(raw_numbers)}):")
    for i, n in enumerate(raw_numbers, 1):
        print(f"  [{i}] {n}")

    unique_texts = set(gen_texts)
    unique_numbers = set(raw_numbers)
    print(f"\nUnique generated_texts: {len(unique_texts)}/{len(gen_texts)}")
    print(f"Unique raw_numbers:    {len(unique_numbers)}/{len(raw_numbers)}")

    if len(unique_texts) == 1:
        print("\n*** VERDICT: MODEL IS STILL COLLAPSING -- all generated_text identical ***")
    elif len(unique_texts) < len(gen_texts):
        print("\n*** VERDICT: PARTIAL COLLAPSE -- some outputs repeated ***")
    else:
        print("\n*** VERDICT: ALL OUTPUTS DIFFERENT -- decoding fix appears effective ***")

    if len(unique_numbers) == 1 and len(raw_numbers) > 1:
        print("*** VERDICT: ALL raw_numbers identical -- numeric collapse confirmed ***")
    elif len(unique_numbers) < len(raw_numbers) and len(raw_numbers) > 1:
        print("*** VERDICT: SOME raw_numbers repeated ***")


if __name__ == "__main__":
    main()
