"""Concept registry loader for financial reasoning."""

import json
from pathlib import Path
from typing import Any

from .constraints.loader import load_equations_from_concepts
from .constraints.models import Equation

try:
    import yaml
except ImportError:
    yaml = None


class ConceptRegistry:
    def __init__(self, config_path: str | Path):
        with open(config_path, encoding="utf-8") as handle:
            if yaml is not None:
                data = yaml.safe_load(handle) or {}
            else:
                data = json.load(handle)
        self.concepts: dict[str, dict[str, Any]] = data.get("concepts", {})
        self._equations_cache: tuple[Equation, ...] | None = None
        self._build_indexes()

    def _build_indexes(self) -> None:
        self.alias_map: dict[str, str] = {}
        self.tag_map: dict[str, str] = {}
        for name, spec in self.concepts.items():
            self.alias_map[name.lower()] = name
            for alias in spec.get("aliases", []):
                self.alias_map[alias.lower()] = name
            for tag in spec.get("xbrl_tags", []):
                normalized_tag = tag.lower()
                self.tag_map[normalized_tag] = name
                if ":" in normalized_tag:
                    self.tag_map[normalized_tag.split(":", 1)[1]] = name

    def get_concept(self, name: str) -> dict[str, Any]:
        return self.concepts.get(name, {})

    def resolve_alias(self, alias: str) -> str | None:
        return self.alias_map.get(alias.lower())

    def resolve_xbrl_tag(self, tag: str) -> str | None:
        return self.tag_map.get(tag.lower())

    def load_equations(self) -> list[Equation]:
        if self._equations_cache is None:
            self._equations_cache = tuple(load_equations_from_concepts(self.concepts))
        return list(self._equations_cache)
