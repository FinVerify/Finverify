"""FCG structural eligibility with exact alias matching only.

Aliases are Unicode-normalized, case-folded, and whitespace-collapsed.
Matches are case-insensitive exact bounded matches. When aliases overlap,
the longest non-overlapping alias wins; registry order cannot affect the
result. No fuzzy, embedding, or model-based extraction is used.
"""

import importlib.util
import re
import unicodedata
from pathlib import Path
from typing import Iterable, Mapping

try:
    # Reuse the repository's frozen registry; do not call its legacy fuzzy API.
    from fcg.normalizer import METRIC_ALIASES
except ImportError:
    path = Path(__file__).parents[2] / "finverify-terminal" / "backend" / "fcg" / "normalizer.py"
    spec = importlib.util.spec_from_file_location("finverify_frozen_fcg_normalizer", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load frozen FCG alias registry: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    METRIC_ALIASES = module.METRIC_ALIASES


def _normal(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).casefold()).strip()


def extract_concepts(text: str, aliases: Mapping[str, Iterable[str]] | None = None) -> tuple[str, ...]:
    registry = aliases if aliases is not None else METRIC_ALIASES
    normalized = _normal(text)
    found = []
    for canonical in sorted(registry):
        candidates = {_normal(canonical), *(_normal(a) for a in registry[canonical])}
        matches = []
        occupied: list[tuple[int, int]] = []
        for alias in sorted(candidates, key=lambda value: (-len(value), value)):
            if alias:
                for match in re.finditer(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", normalized):
                    if not any(match.start() < end and start < match.end() for start, end in occupied):
                        matches.append(match)
                        occupied.append((match.start(), match.end()))
        # The protocol defines presence by one exact alias match. Longest
        # non-overlapping matching resolves aliases such as "revenue" inside
        # "net revenue"; sorting makes registry reordering irrelevant.
        if len(matches) == 1:
            found.append(canonical)
    return tuple(found)


def eligible_constraints(concepts: Iterable[str], constraints: Iterable[Mapping]) -> tuple[str, ...]:
    concept_set = set(concepts)
    return tuple(sorted(str(c["id"]) for c in constraints if set(c.get("requires", ())).issubset(concept_set)))


def structural_eligibility(text: str, constraints: Iterable[Mapping]) -> dict:
    concepts = extract_concepts(text)
    eligible = eligible_constraints(concepts, constraints)
    return {"concepts": list(concepts), "eligible": bool(eligible), "constraint_ids": list(eligible)}
