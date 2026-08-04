"""Minimal deterministic local PDF text extraction without OCR or network."""

from __future__ import annotations

import re
import zlib
from typing import List, Tuple

from .models import ParseIssue, StructuralBlock


_TEXT_BLOCK = re.compile(rb"BT(.*?)ET", re.DOTALL)
_STRING = re.compile(rb"\((?:\\.|[^\\)])*\)")
_HEX_STRING = re.compile(rb"<([0-9A-Fa-f]+)>")
_OBJECT = re.compile(rb"(\d+)\s+\d+\s+obj\b(.*?)endobj", re.DOTALL)
_PAGE = re.compile(rb"/Type\s*/Page(?:\s|/|>)")
_CONTENTS = re.compile(rb"/Contents\s+(.*?)(?=/(?:[A-Za-z]+)\b|>>)", re.DOTALL)
_REFERENCE = re.compile(rb"(\d+)\s+\d+\s+R")
_STREAM = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.DOTALL)


def _decode_pdf_string(raw: bytes) -> str:
    value = raw[1:-1]
    value = re.sub(rb"\\([\\()nrt])", lambda match: {b"n": b"\n", b"r": b"\r", b"t": b"\t"}.get(match.group(1), match.group(1)), value)
    return value.decode("utf-8", errors="replace")


def _decode_stream(payload: bytes, dictionary: bytes) -> bytes | None:
    if b"/FlateDecode" in dictionary:
        try:
            return zlib.decompress(payload)
        except zlib.error:
            return None
    return payload


def _content_streams(data: bytes) -> List[bytes]:
    """Return only streams structurally owned by or referenced from pages."""
    objects = {match.group(1): match.group(2) for match in _OBJECT.finditer(data)}
    streams_by_object = {}
    for object_id, body in objects.items():
        streams = []
        for match in _STREAM.finditer(body):
            payload = _decode_stream(match.group(1), body[:match.start()])
            if payload is not None:
                streams.append(payload)
        if streams:
            streams_by_object[object_id] = streams

    selected: List[bytes] = []
    for object_id, body in objects.items():
        if not _PAGE.search(body):
            continue
        direct = streams_by_object.get(object_id, [])
        selected.extend(direct)
        contents = _CONTENTS.search(body)
        if contents:
            for reference in _REFERENCE.findall(contents.group(1)):
                selected.extend(streams_by_object.get(reference, []))
    return selected


def parse_pdf(data: bytes) -> Tuple[List[StructuralBlock], List[ParseIssue]]:
    page_count = len(re.findall(rb"/Type\s*/Page(?:\s|/|>)", data)) or 1
    blocks: List[StructuralBlock] = []
    issues: List[ParseIssue] = []
    text_blocks = []
    for stream in _content_streams(data):
        text_blocks.extend(_TEXT_BLOCK.findall(stream))
    for index, text_block in enumerate(text_blocks):
        strings = [_decode_pdf_string(item) for item in _STRING.findall(text_block)]
        strings.extend(bytes.fromhex(item.decode("ascii")).decode("utf-8", errors="replace") for item in _HEX_STRING.findall(text_block) if len(item) % 2 == 0)
        text = " ".join(part for part in strings if part).strip()
        if not text:
            continue
        page_index = min(index, page_count - 1)
        block_index = sum(1 for block in blocks if block.metadata.get("page_index") == page_index)
        blocks.append(StructuralBlock(
            text=text,
            locator="page/%d/block/%d" % (page_index, block_index),
            kind="prose",
            metadata={"page_index": page_index, "page_number": page_index + 1},
        ))
    if not blocks:
        issues.append(ParseIssue("", "", "pdf_text_unavailable", "No deterministic PDF text operators were recovered; OCR was not attempted"))
    return blocks, issues
