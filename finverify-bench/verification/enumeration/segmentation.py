"""The frozen punctuation-based raw source span segmentation."""

from __future__ import annotations

from typing import List


def normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def segment_prose(text: str) -> List[str]:
    text = normalize_line_endings(text)
    segments: List[str] = []
    start = 0
    index = 0
    while index < len(text):
        char = text[index]
        if char in ".?!":
            next_char = text[index + 1] if index + 1 < len(text) else ""
            previous_char = text[index - 1] if index else ""
            between_decimal_digits = previous_char.isdigit() and next_char.isdigit()
            followed_by_boundary = not next_char or next_char.isspace()
            if followed_by_boundary and not between_decimal_digits:
                end = index + 1
                while end < len(text) and text[end] in ".?!":
                    end += 1
                segment = text[start:end].strip()
                if segment:
                    segments.append(segment)
                start = end
                index = end
                continue
        index += 1
    tail = text[start:].strip()
    if tail:
        segments.append(tail)
    return segments or ([text.strip()] if text.strip() else [])
