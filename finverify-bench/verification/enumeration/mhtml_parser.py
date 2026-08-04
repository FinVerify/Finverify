"""Local deterministic MHTML primary-content extraction."""

from __future__ import annotations

from email import policy
from email.parser import BytesParser
from typing import List

from .html_parser import parse_html
from .models import StructuralBlock


def parse_mhtml(data: bytes) -> List[StructuralBlock]:
    message = BytesParser(policy=policy.default).parsebytes(data)
    html_parts = []
    text_parts = []
    for index, part in enumerate(message.walk()):
        if part.is_multipart():
            continue
        content_type = part.get_content_type().lower()
        if content_type not in {"text/html", "text/plain"}:
            continue
        try:
            payload = part.get_content()
        except (LookupError, UnicodeError):
            payload = part.get_payload(decode=True) or b""
            payload = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        record = (index, str(payload))
        if content_type == "text/html":
            html_parts.append(record)
        else:
            text_parts.append(record)
    if html_parts:
        return parse_html(html_parts[0][1].encode("utf-8"))
    if text_parts:
        text = " ".join(text_parts[0][1].split())
        return [StructuralBlock(text, "block/0", "prose", {"mhtml_part_index": text_parts[0][0]})] if text else []
    return []
