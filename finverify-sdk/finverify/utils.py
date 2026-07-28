"""finverify.utils — small shared helpers with no other natural home."""

from __future__ import annotations

from typing import Iterable, TypeVar

T = TypeVar("T")


def chunked(items: list[T], size: int) -> Iterable[list[T]]:
    """Yield successive ``size``-sized chunks of ``items``."""
    for i in range(0, len(items), size):
        yield items[i : i + size]


__all__ = ["chunked"]
