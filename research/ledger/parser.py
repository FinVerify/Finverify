"""Frozen numeric answer parser used by raw-ledger generation."""

import re

_NUMBER = re.compile(r"\(\s*[$€£¥₹]?\s*[-+]?\d[\d,]*(?:\.\d+)?(?:[eE][-+]?\d+)?\s*%?\s*\)|[$€£¥₹]?\s*[-+]?\d[\d,]*(?:\.\d+)?(?:[eE][-+]?\d+)?\s*%?")


def extract_number(text: str) -> float | None:
    matches = _NUMBER.findall(text or "")
    if not matches:
        return None
    token = matches[-1].strip()
    negative = token.startswith("(") and token.endswith(")")
    token = token.strip("() ").replace(",", "")
    token = re.sub(r"^[$€£¥₹]\s*", "", token).replace("%", "").strip()
    try:
        value = float(token)
    except ValueError:
        return None
    return -value if negative else value
