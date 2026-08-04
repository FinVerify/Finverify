"""Amendment 1 source-event graph grouping."""

from __future__ import annotations

import hashlib
from collections import defaultdict, deque
from typing import Dict, Iterable, List

from .models import SourceDescriptor
from .normalization import lexical


def source_group_id(member_ids: Iterable[str]) -> str:
    members = sorted(member_ids)
    payload = "finverify-source-group-v1\n" + "\n".join(members)
    return "sg1_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_source_groups(descriptors: Iterable[SourceDescriptor]) -> Dict[str, str]:
    items = list(descriptors)
    adjacency = defaultdict(set)
    for index, left in enumerate(items):
        for right in items[index + 1:]:
            same_event = (
                left.issuer_key not in {"UNKNOWN", "UNSPECIFIED"}
                and right.issuer_key == left.issuer_key
                and left.reporting_event_key not in {"UNKNOWN", "UNSPECIFIED"}
                and right.reporting_event_key == left.reporting_event_key
            )
            explicit_overlap = bool(left.same_event_key and left.same_event_key == right.same_event_key)
            if same_event or explicit_overlap:
                adjacency[left.source_id].add(right.source_id)
                adjacency[right.source_id].add(left.source_id)
    mapping: Dict[str, str] = {}
    seen = set()
    for item in sorted(items, key=lambda value: value.source_id):
        if item.source_id in seen:
            continue
        component = []
        queue = deque([item.source_id])
        seen.add(item.source_id)
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor in sorted(adjacency[current]):
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        group = source_group_id(component)
        for source_id in component:
            mapping[source_id] = group
    return mapping
