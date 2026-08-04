"""Deterministic visible HTML structural extraction."""

from __future__ import annotations

from html.parser import HTMLParser
from typing import List, Optional

from .models import StructuralBlock


class _VisibleHTMLParser(HTMLParser):
    BLOCK_TAGS = {"p", "div", "section", "article", "li", "blockquote", "pre", "h1", "h2", "h3", "h4", "h5", "h6"}
    IGNORE_TAGS = {"script", "style", "noscript", "template", "head", "svg", "canvas"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: List[StructuralBlock] = []
        self._ignored = 0
        self._block_tag: Optional[str] = None
        self._block_depth = 0
        self._block_buffer: List[str] = []
        self._block_heading: Optional[str] = None
        self._heading_context: Optional[str] = None
        self._table_index = -1
        self._table_depth = 0
        self._row_index = -1
        self._cell_index = -1
        self._cell_buffer: List[str] = []
        self._cell_tag: Optional[str] = None
        self._cell_heading: Optional[str] = None

    @staticmethod
    def _text(parts: List[str]) -> str:
        return " ".join("".join(parts).split())

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in self.IGNORE_TAGS:
            self._ignored += 1
            return
        if self._ignored:
            return
        if tag == "table":
            self._table_depth += 1
            if self._table_depth == 1:
                self._table_index += 1
            return
        if self._table_depth:
            if tag == "tr":
                self._row_index += 1
                self._cell_index = -1
            elif tag in {"td", "th"}:
                self._cell_index += 1
                self._cell_tag = tag
                self._cell_buffer = []
                self._cell_heading = self._heading_context
            return
        if tag in self.BLOCK_TAGS:
            if self._block_tag is None:
                self._block_tag = tag
                self._block_depth = 1
                self._block_buffer = []
                self._block_heading = self._heading_context
            else:
                self._block_depth += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.IGNORE_TAGS:
            self._ignored = max(0, self._ignored - 1)
            return
        if self._ignored:
            return
        if tag == "table" and self._table_depth:
            self._table_depth -= 1
            return
        if self._table_depth:
            if tag in {"td", "th"} and self._cell_tag == tag:
                text = self._text(self._cell_buffer)
                if text:
                    locator = "table/%d/row/%d/cell/%d" % (self._table_index, self._row_index, self._cell_index)
                    self.blocks.append(StructuralBlock(
                        text=text,
                        locator=locator,
                        kind="table",
                        metadata={"table_index": self._table_index, "row_index": self._row_index, "cell_index": self._cell_index, "heading_context": self._cell_heading},
                    ))
                self._cell_tag = None
            return
        if self._block_tag is not None and tag in self.BLOCK_TAGS:
            self._block_depth -= 1
            if self._block_depth == 0:
                text = self._text(self._block_buffer)
                if text:
                    block_index = sum(1 for block in self.blocks if block.kind == "prose")
                    kind = "heading" if self._block_tag.startswith("h") else "prose"
                    self.blocks.append(StructuralBlock(text, "block/%d" % block_index, kind, {"heading_context": self._block_heading}))
                    if kind == "heading":
                        self._heading_context = text
                self._block_tag = None
                self._block_buffer = []

    def handle_data(self, data: str) -> None:
        if self._ignored:
            return
        if self._table_depth and self._cell_tag:
            self._cell_buffer.append(data)
        elif self._block_tag is not None:
            self._block_buffer.append(data)


def parse_html(data: bytes) -> List[StructuralBlock]:
    parser = _VisibleHTMLParser()
    parser.feed(data.decode("utf-8", errors="replace"))
    parser.close()
    return parser.blocks
