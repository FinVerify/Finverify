"""Canonical financial document models."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class FinancialPeriod(BaseModel):
    start_date: date
    end_date: date
    fiscal_year: int
    fiscal_quarter: Optional[int] = None


class FinancialStatementItem(BaseModel):
    concept: str
    value: float
    unit: str
    period: FinancialPeriod
    source_ref: str
    xbrl_tag: Optional[str] = None
    confidence: float = 1.0


class FinancialStatement(BaseModel):
    name: str
    items: list[FinancialStatementItem] = Field(default_factory=list)
    period: FinancialPeriod
    currency: str = "USD"


class FinancialDocument(BaseModel):
    company_name: str
    ticker: Optional[str] = None
    cik: Optional[str] = None
    filing_type: str
    filing_date: date
    periods: list[FinancialPeriod] = Field(default_factory=list)
    statements: dict[str, FinancialStatement] = Field(default_factory=dict)
    footnotes: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, str] = Field(default_factory=dict)
    source_url: Optional[str] = None
