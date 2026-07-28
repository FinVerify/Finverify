#!/usr/bin/env python3
"""
FinVerifyBench — Dataset Generator (Phase 4)
Generates 500 mathematically verified benchmark samples across all error categories,
difficulty levels, reasoning types, and source document types.

Run: python scripts/create_dataset.py
"""

import json
import math
import random
from typing import List, Dict, Any

random.seed(42)

# ──────────────────────────────────────────────────────────────────────────────
# Helper: round to sig figs for realistic financial output
# ──────────────────────────────────────────────────────────────────────────────

def r(x: float, decimals: int = 2) -> float:
    if x == 0:
        return 0.0
    return round(x, decimals)

def pct(num: float, denom: float, dec: int = 2) -> float:
    return r(num / denom * 100, dec)

def yoy_pct(new: float, old: float, dec: int = 2) -> float:
    return r((new - old) / abs(old) * 100, dec)

def cagr(end: float, start: float, years: int, dec: int = 2) -> float:
    return r(((end / start) ** (1 / years) - 1) * 100, dec)


# ──────────────────────────────────────────────────────────────────────────────
# Sample factories — one per template family
# ──────────────────────────────────────────────────────────────────────────────

def make_gross_margin(idx: int, split: str, rev: float, cogs: float, unit: str = "million_usd") -> Dict:
    gp = r(rev - cogs, 1)
    gm = pct(gp, rev)
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": f"What is the gross profit margin percentage?",
        "context": f"Income Statement ({unit.replace('_usd','').replace('_',' ')})\nRevenue: ${rev:,.1f}\nCost of Revenue: ${cogs:,.1f}\nGross Profit: ${gp:,.1f}",
        "ground_truth": gm,
        "unit": "percent",
        "error_category": ["scale_error"],
        "difficulty": "easy",
        "reasoning_type": ["margin_calculation"],
        "source_type": "income_statement",
        "split": split,
    }


def make_operating_margin(idx: int, split: str, rev: float, op_inc: float) -> Dict:
    om = pct(op_inc, rev)
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": "What is the operating margin percentage for the reported period?",
        "context": f"Income Statement (in millions)\nTotal Revenue: ${rev:,.1f}\nOperating Income: ${op_inc:,.1f}",
        "ground_truth": om,
        "unit": "percent",
        "error_category": ["scale_error", "ratio_error"],
        "difficulty": "easy",
        "reasoning_type": ["margin_calculation"],
        "source_type": "income_statement",
        "split": split,
    }


def make_net_profit_margin(idx: int, split: str, rev: float, net: float) -> Dict:
    npm = pct(net, rev)
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": "What is the net profit margin for the period?",
        "context": f"Consolidated P&L (in millions)\nTotal Revenue: ${rev:,.1f}\nNet Income: ${net:,.1f}",
        "ground_truth": npm,
        "unit": "percent",
        "error_category": ["scale_error"],
        "difficulty": "easy",
        "reasoning_type": ["margin_calculation"],
        "source_type": "income_statement",
        "split": split,
    }


def make_yoy_abs(idx: int, split: str, label: str, y1: float, y2: float, unit: str,
                 y1_label: str = "2022", y2_label: str = "2023", sign_neg: bool = False) -> Dict:
    delta = r(y2 - y1, 1)
    ec = ["sign_error"] if sign_neg and delta < 0 else ["sign_error"] if delta < 0 else ["arithmetic_error"]
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": f"What was the change in {label} from {y1_label} to {y2_label}?",
        "context": f"Financial Data (in {unit.replace('_usd','').replace('_',' ')})\n{y1_label} {label}: ${y1:,.1f}\n{y2_label} {label}: ${y2:,.1f}",
        "ground_truth": delta,
        "unit": unit,
        "error_category": ec,
        "difficulty": "easy",
        "reasoning_type": ["yoy_change"],
        "source_type": "income_statement",
        "split": split,
    }


def make_yoy_pct(idx: int, split: str, label: str, y1: float, y2: float,
                 y1_label: str = "2022", y2_label: str = "2023") -> Dict:
    chg = yoy_pct(y2, y1)
    ec = ["sign_error", "percentage_error"] if chg < 0 else ["percentage_error"]
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": f"What was the percentage change in {label} from {y1_label} to {y2_label}?",
        "context": f"Annual Data (in millions)\n{y1_label} {label}: ${y1:,.1f}\n{y2_label} {label}: ${y2:,.1f}",
        "ground_truth": chg,
        "unit": "percent",
        "error_category": ec,
        "difficulty": "medium",
        "reasoning_type": ["percentage_change", "yoy_change"],
        "source_type": "income_statement",
        "split": split,
    }


def make_roe(idx: int, split: str, net_inc: float, equity: float) -> Dict:
    roe = pct(net_inc, equity)
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": "What is the return on equity (ROE)?",
        "context": f"Financial Data (in millions)\nNet Income: ${net_inc:,.1f}\nTotal Shareholders' Equity: ${equity:,.1f}",
        "ground_truth": roe,
        "unit": "percent",
        "error_category": ["ratio_error", "scale_error"],
        "difficulty": "medium",
        "reasoning_type": ["ratio_calculation"],
        "source_type": "sec_10k",
        "split": split,
    }


def make_roa(idx: int, split: str, net_inc: float, assets: float) -> Dict:
    roa = pct(net_inc, assets)
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": "What is the return on assets (ROA) for the period?",
        "context": f"Financial Data (in millions)\nNet Income: ${net_inc:,.1f}\nAverage Total Assets: ${assets:,.1f}",
        "ground_truth": roa,
        "unit": "percent",
        "error_category": ["ratio_error", "scale_error"],
        "difficulty": "medium",
        "reasoning_type": ["ratio_calculation"],
        "source_type": "sec_10k",
        "split": split,
    }


def make_current_ratio(idx: int, split: str, ca: float, cl: float) -> Dict:
    cr = r(ca / cl, 3)
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": "What is the current ratio as of the balance sheet date?",
        "context": f"Balance Sheet (in millions)\nCurrent Assets: ${ca:,.1f}\nCurrent Liabilities: ${cl:,.1f}",
        "ground_truth": cr,
        "unit": "ratio",
        "error_category": ["ratio_error"],
        "difficulty": "easy",
        "reasoning_type": ["ratio_calculation"],
        "source_type": "balance_sheet",
        "split": split,
    }


def make_debt_to_equity(idx: int, split: str, debt: float, equity: float) -> Dict:
    de = r(debt / equity, 3)
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": "What is the debt-to-equity ratio?",
        "context": f"Capital Structure (in millions)\nTotal Debt: ${debt:,.1f}\nTotal Shareholders' Equity: ${equity:,.1f}",
        "ground_truth": de,
        "unit": "ratio",
        "error_category": ["ratio_error", "scale_error"],
        "difficulty": "medium",
        "reasoning_type": ["ratio_calculation"],
        "source_type": "balance_sheet",
        "split": split,
    }


def make_interest_coverage(idx: int, split: str, ebit: float, interest: float) -> Dict:
    ic = r(ebit / interest, 2)
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": "What is the interest coverage ratio for the period?",
        "context": f"Income Statement (in millions)\nEBIT: ${ebit:,.1f}\nInterest Expense: ${interest:,.1f}",
        "ground_truth": ic,
        "unit": "ratio",
        "error_category": ["ratio_error"],
        "difficulty": "medium",
        "reasoning_type": ["ratio_calculation"],
        "source_type": "income_statement",
        "split": split,
    }


def make_pe_ratio(idx: int, split: str, price: float, eps: float) -> Dict:
    pe = r(price / eps, 2)
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": "What is the price-to-earnings (P/E) ratio?",
        "context": f"Market Data\nCurrent Stock Price: ${price:,.2f}\nEarnings Per Share (TTM): ${eps:,.2f}",
        "ground_truth": pe,
        "unit": "ratio",
        "error_category": ["ratio_error"],
        "difficulty": "easy",
        "reasoning_type": ["ratio_calculation"],
        "source_type": "investor_presentation",
        "split": split,
    }


def make_cagr(idx: int, split: str, label: str, start: float, end: float, years: int) -> Dict:
    c = cagr(end, start, years)
    y_start = 2023 - years
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": f"What is the {years}-year CAGR of {label} from {y_start} to 2023?",
        "context": f"Annual {label} (in millions)\n{y_start}: ${start:,.1f}\n2023: ${end:,.1f}",
        "ground_truth": c,
        "unit": "percent",
        "error_category": ["arithmetic_error", "percentage_error"],
        "difficulty": "hard",
        "reasoning_type": ["growth_rate", "multi_step_arithmetic"],
        "source_type": "investor_presentation",
        "split": split,
    }


def make_multi_year_cagr(idx: int, split: str, label: str, values: List[float], years: List[int]) -> Dict:
    start_y, end_y = years[0], years[-1]
    n = end_y - start_y
    c = cagr(values[-1], values[0], n)
    rows = "\n".join(f"{y}: ${v:,.1f}" for y, v in zip(years, values))
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": f"What is the compound annual growth rate (CAGR) of {label} from {start_y} to {end_y}?",
        "context": f"Annual {label} (in millions)\n{rows}",
        "ground_truth": c,
        "unit": "percent",
        "error_category": ["arithmetic_error", "percentage_error"],
        "difficulty": "hard",
        "reasoning_type": ["growth_rate", "multi_step_arithmetic"],
        "source_type": "sec_10k",
        "split": split,
    }


def make_magnitude_lookup(idx: int, split: str, label: str, value_m: float, ask_unit: str) -> Dict:
    """value in millions; ask in different unit."""
    if ask_unit == "billion_usd":
        gt = r(value_m / 1000, 3)
        ask_str = "billions"
    elif ask_unit == "thousand_usd":
        gt = r(value_m * 1000, 1)
        ask_str = "thousands"
    else:
        gt = value_m
        ask_str = "millions"
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": f"What is the {label} reported, expressed in {ask_str}?",
        "context": f"Balance Sheet (in millions)\n{label}: ${value_m:,.1f}",
        "ground_truth": gt,
        "unit": ask_unit,
        "error_category": ["magnitude_error", "unit_conversion"],
        "difficulty": "hard",
        "reasoning_type": ["unit_conversion", "single_lookup"],
        "source_type": "balance_sheet",
        "split": split,
    }


def make_aggregation(idx: int, split: str, label: str, values: List[float],
                     quarters: List[str], agg: str = "total") -> Dict:
    if agg == "total":
        gt = r(sum(values), 1)
        q_str = "total"
    elif agg == "average":
        gt = r(sum(values) / len(values), 1)
        q_str = "average quarterly"
    elif agg == "max":
        gt = r(max(values), 1)
        q_str = "maximum quarterly"
    else:
        gt = r(min(values), 1)
        q_str = "minimum quarterly"
    rows = "\n".join(f"{q}: ${v:,.1f}" for q, v in zip(quarters, values))
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": f"What is the {q_str} {label} across all quarters?",
        "context": f"Quarterly {label} (in millions)\n{rows}",
        "ground_truth": gt,
        "unit": "million_usd",
        "error_category": ["aggregation_error"],
        "difficulty": "medium",
        "reasoning_type": ["aggregation"],
        "source_type": "earnings_release",
        "split": split,
    }


def make_sign_loss(idx: int, split: str, label: str, value: float, unit: str,
                   context_note: str = "") -> Dict:
    assert value < 0, "sign_loss samples must have negative ground_truth"
    abs_v = abs(value)
    ctx_extra = f"\n{context_note}" if context_note else ""
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": f"What was the {label} reported for the period?",
        "context": f"Financial Statement (in millions)\n{label}: $({abs_v:,.1f}){ctx_extra}",
        "ground_truth": value,
        "unit": unit,
        "error_category": ["sign_error"],
        "difficulty": "easy",
        "reasoning_type": ["single_lookup"],
        "source_type": "income_statement",
        "split": split,
    }


def make_ebitda_margin(idx: int, split: str, rev: float, ebit: float, da: float) -> Dict:
    ebitda = r(ebit + da, 1)
    margin = pct(ebitda, rev)
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": "What is the EBITDA margin for the period?",
        "context": f"Income Statement (in millions)\nRevenue: ${rev:,.1f}\nEBIT: ${ebit:,.1f}\nDepreciation & Amortization: ${da:,.1f}\nEBITDA: ${ebitda:,.1f}",
        "ground_truth": margin,
        "unit": "percent",
        "error_category": ["scale_error", "aggregation_error"],
        "difficulty": "hard",
        "reasoning_type": ["margin_calculation", "multi_step_arithmetic"],
        "source_type": "income_statement",
        "split": split,
    }


def make_quick_ratio(idx: int, split: str, cash: float, sti: float, ar: float, cl: float) -> Dict:
    numerator = r(cash + sti + ar, 1)
    qr = r(numerator / cl, 3)
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": "What is the quick ratio (acid-test ratio)?",
        "context": f"Balance Sheet (in millions)\nCash & Equivalents: ${cash:,.1f}\nShort-term Investments: ${sti:,.1f}\nAccounts Receivable: ${ar:,.1f}\nCurrent Liabilities: ${cl:,.1f}",
        "ground_truth": qr,
        "unit": "ratio",
        "error_category": ["ratio_error", "aggregation_error"],
        "difficulty": "hard",
        "reasoning_type": ["ratio_calculation", "aggregation"],
        "source_type": "balance_sheet",
        "split": split,
    }


def make_dividend_yield(idx: int, split: str, div: float, price: float) -> Dict:
    dy = pct(div, price)
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": "What is the dividend yield percentage?",
        "context": f"Market Data\nAnnual Dividend Per Share: ${div:,.2f}\nCurrent Stock Price: ${price:,.2f}",
        "ground_truth": dy,
        "unit": "percent",
        "error_category": ["scale_error", "ratio_error"],
        "difficulty": "easy",
        "reasoning_type": ["ratio_calculation"],
        "source_type": "investor_presentation",
        "split": split,
    }


def make_inventory_turnover(idx: int, split: str, cogs: float, inv: float) -> Dict:
    it = r(cogs / inv, 2)
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": "What is the inventory turnover ratio for the period?",
        "context": f"Financial Data (in millions)\nCost of Goods Sold: ${cogs:,.1f}\nAverage Inventory: ${inv:,.1f}",
        "ground_truth": it,
        "unit": "ratio",
        "error_category": ["ratio_error"],
        "difficulty": "easy",
        "reasoning_type": ["ratio_calculation"],
        "source_type": "sec_10k",
        "split": split,
    }


def make_multi_step_fcf(idx: int, split: str, ocf: float, capex: float) -> Dict:
    fcf = r(ocf - capex, 1)
    sign_ec = ["sign_error", "arithmetic_error"] if fcf < 0 else ["arithmetic_error"]
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": "What is the free cash flow for the period?",
        "context": f"Cash Flow Statement (in millions)\nOperating Cash Flow: ${ocf:,.1f}\nCapital Expenditures: ${capex:,.1f}",
        "ground_truth": fcf,
        "unit": "million_usd",
        "error_category": sign_ec,
        "difficulty": "medium",
        "reasoning_type": ["multi_step_arithmetic"],
        "source_type": "cash_flow_statement",
        "split": split,
    }


def make_net_cash_all(idx: int, split: str, op: float, inv: float, fin: float) -> Dict:
    net = r(op + inv + fin, 1)
    sign_ec = ["sign_error", "arithmetic_error"] if net < 0 else ["arithmetic_error"]
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": "What is the net change in cash from all activities?",
        "context": f"Cash Flow Statement (in millions)\nOperating Activities: ${op:,.1f}\nInvesting Activities: $({abs(inv):,.1f})\nFinancing Activities: $({abs(fin):,.1f})\n(Negative values denote outflows)",
        "ground_truth": net,
        "unit": "million_usd",
        "error_category": sign_ec,
        "difficulty": "medium",
        "reasoning_type": ["multi_step_arithmetic"],
        "source_type": "cash_flow_statement",
        "split": split,
    }


def make_book_value_per_share(idx: int, split: str, equity_m: float, shares_m: float) -> Dict:
    bvps = r(equity_m / shares_m * 1_000_000 / 1_000_000, 2)  # equity in M / shares in M = $ per share
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": "What is the book value per share?",
        "context": f"Balance Sheet Data\nTotal Shareholders' Equity (in millions): ${equity_m:,.1f}\nShares Outstanding (in millions): {shares_m:,.1f}",
        "ground_truth": bvps,
        "unit": "usd",
        "error_category": ["ratio_error", "magnitude_error"],
        "difficulty": "hard",
        "reasoning_type": ["ratio_calculation", "unit_conversion"],
        "source_type": "balance_sheet",
        "split": split,
    }


def make_effective_tax_rate(idx: int, split: str, pre_tax: float, tax: float) -> Dict:
    etr = pct(tax, pre_tax)
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": "What is the effective tax rate for the period?",
        "context": f"Income Statement (in millions)\nIncome Before Tax: ${pre_tax:,.1f}\nIncome Tax Expense: ${tax:,.1f}",
        "ground_truth": etr,
        "unit": "percent",
        "error_category": ["scale_error", "ratio_error"],
        "difficulty": "easy",
        "reasoning_type": ["ratio_calculation"],
        "source_type": "income_statement",
        "split": split,
    }


def make_eps_change(idx: int, split: str, eps1: float, eps2: float,
                    y1: str = "2021", y2: str = "2022") -> Dict:
    chg = yoy_pct(eps2, eps1)
    ec = ["sign_error", "percentage_error"] if chg < 0 else ["percentage_error"]
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": f"What was the percentage change in earnings per share (EPS) from {y1} to {y2}?",
        "context": f"EPS Data\n{y1} EPS: ${eps1:,.2f}\n{y2} EPS: ${eps2:,.2f}",
        "ground_truth": chg,
        "unit": "percent",
        "error_category": ec,
        "difficulty": "medium",
        "reasoning_type": ["percentage_change", "yoy_change"],
        "source_type": "earnings_release",
        "split": split,
    }


def make_segment_total(idx: int, split: str, segments: List[tuple]) -> Dict:
    total = r(sum(v for _, v in segments), 1)
    rows = "\n".join(f"{name}: ${v:,.1f}" for name, v in segments)
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": "What is the total revenue across all business segments?",
        "context": f"Segment Revenue (in billions)\n{rows}",
        "ground_truth": total,
        "unit": "billion_usd",
        "error_category": ["aggregation_error"],
        "difficulty": "easy",
        "reasoning_type": ["aggregation"],
        "source_type": "sec_10k",
        "split": split,
    }


def make_multi_period_sum(idx: int, split: str, label: str,
                          years: List[int], values: List[float]) -> Dict:
    total = r(sum(values), 1)
    rows = "\n".join(f"{y}: ${v:,.1f}" for y, v in zip(years, values))
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": f"What is the total {label} over the {len(years)}-year period from {years[0]} to {years[-1]}?",
        "context": f"{label} (in millions)\n{rows}",
        "ground_truth": total,
        "unit": "million_usd",
        "error_category": ["aggregation_error", "arithmetic_error"],
        "difficulty": "medium",
        "reasoning_type": ["aggregation", "multi_step_arithmetic"],
        "source_type": "sec_10k",
        "split": split,
    }


def make_rounding_error(idx: int, split: str, rev1: float, rev2: float,
                        y1: str = "2021", y2: str = "2022") -> Dict:
    """Percentage change — the CoT rounding error case from paper."""
    exact = yoy_pct(rev2, rev1, dec=4)
    rounded = r(exact, 2)
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": f"What is the exact percentage increase in revenue from {y1} to {y2}?",
        "context": f"Revenue Data (in millions)\n{y1}: ${rev1:,.1f}\n{y2}: ${rev2:,.1f}",
        "ground_truth": rounded,
        "unit": "percent",
        "error_category": ["rounding_error", "percentage_error"],
        "difficulty": "medium",
        "reasoning_type": ["percentage_change", "multi_step_arithmetic"],
        "source_type": "income_statement",
        "split": split,
    }


def make_context_confusion(idx: int, split: str) -> Dict:
    """Cross-period lookup confusion."""
    return {
        "id": f"fvb_{idx:06d}",
        "domain": "finance",
        "question": "What was the operating income reported for fiscal year 2021?",
        "context": "Income Statement (in millions)\n2020 Operating Income: $3,240\n2021 Operating Income: $4,180\n2022 Operating Income: $3,920\n2023 Operating Income: $5,100",
        "ground_truth": 4180.0,
        "unit": "million_usd",
        "error_category": ["context_confusion"],
        "difficulty": "medium",
        "reasoning_type": ["single_lookup"],
        "source_type": "income_statement",
        "split": split,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Generate all 500 samples
# ──────────────────────────────────────────────────────────────────────────────

def assign_split(i: int, n_train: int = 350, n_dev: int = 75) -> str:
    if i < n_train:
        return "train"
    elif i < n_train + n_dev:
        return "dev"
    return "test"


def generate_all() -> List[Dict[str, Any]]:
    samples = []
    i = 1

    # ── Block 1: Gross Margin (scale_error) ─── 40 samples ───────────────────
    gm_params = [
        (45230, 33245), (28400, 19040), (61200, 42840), (18700, 12342),
        (92400, 60984), (34500, 22425), (78900, 53532), (24600, 17220),
        (110000, 74800), (43200, 29376), (55000, 37400), (19800, 13266),
        (87300, 58491), (31500, 20790), (64800, 44496), (22400, 15232),
        (98000, 65660), (41000, 27880), (73500, 50715), (26300, 18147),
        (115000, 79350), (37800, 25326), (82100, 55818), (29000, 19720),
        (105000, 70350), (47600, 32394), (69000, 46920), (21500, 14405),
        (93000, 62310), (35400, 23868), (76500, 51255), (23700, 15918),
        (108000, 72360), (42500, 28900), (67200, 45696), (20100, 13468),
        (96500, 65140), (39100, 26388), (72000, 48960), (25100, 17068),
    ]
    for rev, cogs in gm_params:
        s = assign_split(i - 1)
        samples.append(make_gross_margin(i, s, rev, cogs))
        i += 1

    # ── Block 2: Operating Margin (scale_error, ratio_error) ─── 25 samples ──
    om_params = [
        (52400, 4460), (34200, 3078), (78600, 7074), (21300, 1917),
        (95000, 8550), (43800, 3942), (67000, 6030), (18900, 1701),
        (112000, 10080), (38500, 3465), (58000, 5220), (24700, 2223),
        (89000, 8010), (31200, 2808), (71500, 6435), (20800, 1872),
        (103000, 9270), (46200, 4158), (63500, 5715), (27400, 2466),
        (84000, 7560), (36700, 3303), (77000, 6930), (22600, 2034), (48000, 4320),
    ]
    for rev, op_inc in om_params:
        s = assign_split(i - 1)
        samples.append(make_operating_margin(i, s, rev, op_inc))
        i += 1

    # ── Block 3: Net Profit Margin (scale_error) ─── 20 samples ─────────────
    npm_params = [
        (89200, 7136), (42000, 3276), (76500, 5738), (23400, 1755),
        (98000, 7546), (35000, 2625), (61000, 4575), (19500, 1443),
        (115000, 8855), (47000, 3478), (83000, 6308), (28000, 2128),
        (102000, 7854), (39000, 2925), (72000, 5472), (21000, 1575),
        (94000, 7238), (44000, 3300), (68000, 5168), (26000, 1976),
    ]
    for rev, net in npm_params:
        s = assign_split(i - 1)
        samples.append(make_net_profit_margin(i, s, rev, net))
        i += 1

    # ── Block 4: YoY absolute change — sign_error ─── 40 samples ─────────────
    yoy_abs_params = [
        ("Operating Income", 4120, 3875, "million_usd", "2021", "2022"),
        ("Net Revenue",      28000, 31500, "million_usd", "2022", "2023"),
        ("Cash & Equivalents", 8420, 6780, "million_usd", "2022", "2023"),
        ("Long-term Debt",   14200, 12900, "million_usd", "2021", "2022"),
        ("Retained Earnings", 12340, 11890, "million_usd", "2022", "2023"),
        ("EBIT",             5670, 4980, "million_usd", "2022", "2023"),
        ("SG&A Expenses",    8920, 7840, "million_usd", "2022", "2023"),
        ("Gross Profit",     11200, 12800, "million_usd", "2021", "2022"),
        ("Total Assets",     67400, 71200, "million_usd", "2022", "2023"),
        ("Capital Expenditure", 2340, 1890, "million_usd", "2022", "2023"),
        ("R&D Expense",      3100, 3640, "million_usd", "2022", "2023"),
        ("Inventory",        4560, 5120, "million_usd", "2022", "2023"),
        ("Accounts Receivable", 6700, 5980, "million_usd", "2022", "2023"),
        ("Net Income",       5400, 4780, "million_usd", "2022", "2023"),
        ("Free Cash Flow",   3200, 2750, "million_usd", "2022", "2023"),
        ("Revenue",          42000, 48600, "million_usd", "2021", "2022"),
        ("Operating Expenses", 38000, 34500, "million_usd", "2022", "2023"),
        ("Goodwill",         9800, 9240, "million_usd", "2022", "2023"),
        ("Total Equity",     22000, 24600, "million_usd", "2022", "2023"),
        ("Depreciation",     1800, 2100, "million_usd", "2022", "2023"),
        ("Interest Expense", 1240, 980, "million_usd", "2022", "2023"),
        ("Tax Expense",      2100, 1750, "million_usd", "2022", "2023"),
        ("Short-term Debt",  3200, 2800, "million_usd", "2022", "2023"),
        ("Working Capital",  8400, 9200, "million_usd", "2022", "2023"),
        ("Dividends Paid",   1200, 1400, "million_usd", "2022", "2023"),
        ("PP&E Net",         18000, 16500, "million_usd", "2022", "2023"),
        ("Deferred Revenue", 3400, 4100, "million_usd", "2022", "2023"),
        ("Other Income",     450, 380, "million_usd", "2022", "2023"),
        ("Pension Obligation", 5600, 5100, "million_usd", "2022", "2023"),
        ("Minority Interest", 890, 760, "million_usd", "2022", "2023"),
        ("Stock-based Compensation", 1800, 2200, "million_usd", "2022", "2023"),
        ("Amortization",     920, 1080, "million_usd", "2022", "2023"),
        ("Current Liabilities", 14200, 13100, "million_usd", "2022", "2023"),
        ("Non-current Assets", 52000, 55000, "million_usd", "2022", "2023"),
        ("Prepaid Expenses", 780, 640, "million_usd", "2022", "2023"),
        ("Accrued Liabilities", 2100, 1800, "million_usd", "2022", "2023"),
        ("Total Liabilities", 41000, 38000, "million_usd", "2022", "2023"),
        ("Cash from Operations", 7800, 8900, "million_usd", "2022", "2023"),
        ("Intangible Assets Net", 4200, 3600, "million_usd", "2022", "2023"),
        ("EPS (diluted)", 4.32, 3.87, "usd", "2021", "2022"),
    ]
    for label, v1, v2, unit, y1, y2 in yoy_abs_params:
        s = assign_split(i - 1)
        samples.append(make_yoy_abs(i, s, label, v1, v2, unit, y1, y2))
        i += 1

    # ── Block 5: YoY percentage change (percentage_error, sign_error) ── 35 samples
    yoy_pct_params = [
        ("Revenue",         42000, 48600, "2022", "2023"),
        ("Net Income",      5400, 4780, "2022", "2023"),
        ("Operating Income", 4120, 3875, "2021", "2022"),
        ("EBITDA",          9200, 10500, "2022", "2023"),
        ("Gross Profit",    11200, 12800, "2021", "2022"),
        ("R&D Expense",     3100, 3640, "2022", "2023"),
        ("Free Cash Flow",  3200, 2750, "2022", "2023"),
        ("EPS",             4.32, 3.87, "2021", "2022"),
        ("Capital Expenditure", 2340, 1890, "2022", "2023"),
        ("SG&A",            8920, 7840, "2022", "2023"),
        ("Total Assets",    67400, 71200, "2022", "2023"),
        ("Long-term Debt",  14200, 12900, "2021", "2022"),
        ("Operating Expenses", 38000, 34500, "2022", "2023"),
        ("Cash Flow from Operations", 7800, 8900, "2022", "2023"),
        ("Interest Expense", 1240, 980, "2022", "2023"),
        ("Revenue",         31000, 36200, "2020", "2022"),
        ("Net Income",      2800, 4100, "2020", "2022"),
        ("Gross Margin Revenue", 18200, 22100, "2021", "2023"),
        ("EBIT",            5200, 4600, "2022", "2023"),
        ("Working Capital",  8400, 9200, "2022", "2023"),
        ("Inventory",       4560, 5120, "2022", "2023"),
        ("Accounts Receivable", 6700, 5980, "2022", "2023"),
        ("Tax Expense",     2100, 1750, "2022", "2023"),
        ("Dividends Paid",  1200, 1400, "2022", "2023"),
        ("PP&E Net",        18000, 16500, "2022", "2023"),
        ("Stock-based Compensation", 1800, 2200, "2022", "2023"),
        ("Current Liabilities", 14200, 13100, "2022", "2023"),
        ("Total Equity",    22000, 24600, "2022", "2023"),
        ("Deferred Revenue", 3400, 4100, "2022", "2023"),
        ("Non-current Assets", 52000, 55000, "2022", "2023"),
        ("Goodwill",        9800, 9240, "2022", "2023"),
        ("Other Income",    450, 380, "2022", "2023"),
        ("Amortization",    920, 1080, "2022", "2023"),
        ("Prepaid Expenses", 780, 640, "2022", "2023"),
        ("Minority Interest", 890, 760, "2022", "2023"),
    ]
    for label, v1, v2, y1, y2 in yoy_pct_params:
        s = assign_split(i - 1)
        samples.append(make_yoy_pct(i, s, label, v1, v2, y1, y2))
        i += 1

    # ── Block 6: ROE (ratio_error, scale_error) ─── 20 samples ───────────────
    roe_params = [
        (2340, 18500), (4180, 32000), (1890, 15600), (6200, 48000),
        (3450, 27000), (1250, 9800), (5100, 41000), (2780, 22000),
        (7800, 62000), (1680, 13200), (4560, 36000), (2100, 16500),
        (8900, 71000), (3200, 25000), (1450, 11400), (5800, 46000),
        (2650, 21000), (9400, 75000), (3700, 29000), (1900, 15000),
    ]
    for net_inc, equity in roe_params:
        s = assign_split(i - 1)
        samples.append(make_roe(i, s, net_inc, equity))
        i += 1

    # ── Block 7: ROA ─── 15 samples ──────────────────────────────────────────
    roa_params = [
        (4320, 67800), (2100, 34000), (6700, 98000), (1500, 24000),
        (8900, 134000), (3400, 52000), (1800, 28500), (5600, 84000),
        (2700, 43000), (7200, 108000), (1300, 20000), (4800, 73000),
        (2400, 38000), (6100, 91000), (3000, 47000),
    ]
    for net_inc, assets in roa_params:
        s = assign_split(i - 1)
        samples.append(make_roa(i, s, net_inc, assets))
        i += 1

    # ── Block 8: Current Ratio ─── 15 samples ────────────────────────────────
    cr_params = [
        (14320, 9870), (8600, 5400), (22000, 14000), (5200, 3900),
        (31000, 19000), (11400, 7600), (4800, 3600), (18000, 11200),
        (7200, 5200), (25000, 15600), (9100, 6200), (3800, 2900),
        (16000, 10200), (6400, 4700), (28000, 17500),
    ]
    for ca, cl in cr_params:
        s = assign_split(i - 1)
        samples.append(make_current_ratio(i, s, ca, cl))
        i += 1

    # ── Block 9: D/E Ratio ─── 15 samples ────────────────────────────────────
    de_params = [
        (8920, 22400), (4200, 16800), (12600, 31500), (2800, 14000),
        (18000, 42000), (6300, 18900), (3500, 10500), (9800, 24500),
        (5600, 16000), (14000, 35000), (7000, 21000), (2100, 8400),
        (11200, 28000), (4900, 14700), (16100, 40250),
    ]
    for debt, eq in de_params:
        s = assign_split(i - 1)
        samples.append(make_debt_to_equity(i, s, debt, eq))
        i += 1

    # ── Block 10: Interest Coverage ─── 10 samples ───────────────────────────
    ic_params = [
        (5670, 890), (3200, 640), (8900, 1112), (2100, 525),
        (11000, 1375), (4500, 900), (1800, 450), (7200, 800), (3800, 760), (6400, 914),
    ]
    for ebit, interest in ic_params:
        s = assign_split(i - 1)
        samples.append(make_interest_coverage(i, s, ebit, interest))
        i += 1

    # ── Block 11: P/E Ratio ─── 15 samples ───────────────────────────────────
    pe_params = [
        (142.50, 8.75), (87.20, 5.40), (234.00, 14.20), (52.40, 3.80),
        (312.00, 18.60), (108.50, 7.20), (67.80, 4.50), (189.00, 11.80),
        (43.20, 3.10), (256.00, 15.40), (94.60, 6.30), (178.00, 10.60),
        (38.50, 2.80), (145.00, 9.20), (221.00, 13.40),
    ]
    for price, eps in pe_params:
        s = assign_split(i - 1)
        samples.append(make_pe_ratio(i, s, price, eps))
        i += 1

    # ── Block 12: CAGR (arithmetic_error, percentage_error) ─── 20 samples ──
    cagr_params = [
        ("Revenue",         12400, 21300, 4),
        ("Net Income",      2800,  5400,  3),
        ("EBITDA",          8200,  14600, 4),
        ("Free Cash Flow",  3100,  5800,  3),
        ("Total Assets",    52000, 78000, 4),
        ("R&D Spend",       2100,  3900,  4),
        ("Operating Income",4100,  7200,  4),
        ("Gross Profit",    9800,  17100, 4),
        ("EPS",             3.20,  6.40,  3),
        ("Revenue",         18200, 29100, 3),
        ("Net Income",      1800,  3600,  4),
        ("EBITDA",          6200,  10800, 3),
        ("Free Cash Flow",  2400,  4200,  4),
        ("Operating Cash Flow", 5100, 8900, 3),
        ("SG&A Expense",    7200,  9800,  3),
        ("Revenue",         9400,  15200, 4),
        ("Capital Expenditure", 1800, 2900, 3),
        ("Total Equity",    14200, 22400, 4),
        ("Net Revenue",     22000, 35000, 4),
        ("EBIT",            3800,  6700,  4),
    ]
    for label, start, end, yrs in cagr_params:
        s = assign_split(i - 1)
        samples.append(make_cagr(i, s, label, start, end, yrs))
        i += 1

    # ── Block 13: Magnitude / Unit Conversion ─── 30 samples ─────────────────
    mag_params = [
        ("Total Assets",      47230,  "billion_usd"),
        ("Long-term Debt",    17020,  "billion_usd"),
        ("Total Revenue",     89400,  "billion_usd"),
        ("Net PP&E",          34100,  "billion_usd"),
        ("Goodwill",          12500,  "billion_usd"),
        ("Total Equity",      28000,  "billion_usd"),
        ("Operating Cash Flow", 9800, "billion_usd"),
        ("Capital Expenditure", 4200, "billion_usd"),
        ("Cash & Equivalents",  6780, "billion_usd"),
        ("Intangible Assets",   8900, "billion_usd"),
        ("Total Liabilities",  52300, "billion_usd"),
        ("Current Assets",     14300, "billion_usd"),
        ("Non-current Assets", 42100, "billion_usd"),
        ("Total Assets",       19800, "billion_usd"),
        ("Net Income",          7800, "billion_usd"),
        ("Total Revenue",     456800, "thousand_usd"),
        ("Operating Expenses", 234100, "thousand_usd"),
        ("Gross Profit",       128400, "thousand_usd"),
        ("Net Income",          45200, "thousand_usd"),
        ("Capital Expenditure", 89300, "thousand_usd"),
        ("Cash from Operations", 178000, "thousand_usd"),
        ("Total Assets",       892000, "thousand_usd"),
        ("Long-term Debt",     342000, "thousand_usd"),
        ("Total Equity",       560000, "thousand_usd"),
        ("R&D Expense",         67800, "thousand_usd"),
        ("Inventory",           34500, "billion_usd"),
        ("Accounts Receivable", 28900, "billion_usd"),
        ("Short-term Investments", 15600, "billion_usd"),
        ("Deferred Tax Assets",  9200, "billion_usd"),
        ("Other Long-term Liabilities", 7800, "billion_usd"),
    ]
    for label, val_m, ask_unit in mag_params:
        s = assign_split(i - 1)
        samples.append(make_magnitude_lookup(i, s, label, val_m, ask_unit))
        i += 1

    # ── Block 14: Aggregation ─── 30 samples ─────────────────────────────────
    agg_configs = [
        ("Revenue",               [3240, 3580, 3920, 4160], ["Q1 2022","Q2 2022","Q3 2022","Q4 2022"], "total"),
        ("Operating Cash Flow",   [2100, 2800, 2400, 3100], ["Q1","Q2","Q3","Q4"], "total"),
        ("Capital Expenditure",   [420, 380, 460, 510],     ["Q1","Q2","Q3","Q4"], "total"),
        ("Net Income",            [1100, 1350, 1200, 1500], ["Q1","Q2","Q3","Q4"], "total"),
        ("R&D Expense",           [780, 810, 840, 890],     ["Q1","Q2","Q3","Q4"], "total"),
        ("Revenue",               [4100, 4380, 4720, 5040], ["Q1 2023","Q2 2023","Q3 2023","Q4 2023"], "total"),
        ("SG&A Expense",          [1800, 1920, 1850, 2000], ["Q1","Q2","Q3","Q4"], "total"),
        ("Free Cash Flow",        [680, 920, 780, 1100],    ["Q1","Q2","Q3","Q4"], "total"),
        ("Revenue",               [3240, 3580, 3920, 4160], ["Q1","Q2","Q3","Q4"], "average"),
        ("Capital Expenditure",   [420, 380, 460, 510],     ["Q1","Q2","Q3","Q4"], "average"),
        ("Net Income",            [1100, 1350, 1200, 1500], ["Q1","Q2","Q3","Q4"], "average"),
        ("Operating Cash Flow",   [2100, 2800, 2400, 3100], ["Q1","Q2","Q3","Q4"], "average"),
        ("Revenue",               [3240, 3580, 3920, 4160], ["Q1","Q2","Q3","Q4"], "max"),
        ("Operating Cash Flow",   [2100, 2800, 2400, 3100], ["Q1","Q2","Q3","Q4"], "max"),
        ("Free Cash Flow",        [680, 920, 780, 1100],    ["Q1","Q2","Q3","Q4"], "max"),
        ("Capital Expenditure",   [420, 380, 460, 510],     ["Q1","Q2","Q3","Q4"], "max"),
        ("Net Income",            [1100, 1350, 1200, 1500], ["Q1","Q2","Q3","Q4"], "min"),
        ("R&D Expense",           [780, 810, 840, 890],     ["Q1","Q2","Q3","Q4"], "min"),
        ("Revenue",               [3240, 3580, 3920, 4160], ["Q1","Q2","Q3","Q4"], "min"),
        ("SG&A Expense",          [1800, 1920, 1850, 2000], ["Q1","Q2","Q3","Q4"], "min"),
        ("Depreciation Expense",  [340, 355, 360, 370],     ["Q1","Q2","Q3","Q4"], "total"),
        ("Interest Expense",      [210, 215, 218, 220],     ["Q1","Q2","Q3","Q4"], "total"),
        ("Tax Expense",           [480, 540, 510, 600],     ["Q1","Q2","Q3","Q4"], "total"),
        ("Stock Repurchase",      [800, 950, 700, 1100],    ["Q1","Q2","Q3","Q4"], "total"),
        ("Dividends Paid",        [280, 280, 290, 290],     ["Q1","Q2","Q3","Q4"], "total"),
        ("Gross Profit",          [1800, 1980, 2100, 2250], ["Q1","Q2","Q3","Q4"], "total"),
        ("Operating Expenses",    [2100, 2200, 2150, 2300], ["Q1","Q2","Q3","Q4"], "average"),
        ("Gross Profit",          [1800, 1980, 2100, 2250], ["Q1","Q2","Q3","Q4"], "max"),
        ("Tax Expense",           [480, 540, 510, 600],     ["Q1","Q2","Q3","Q4"], "min"),
        ("Interest Expense",      [210, 215, 218, 220],     ["Q1","Q2","Q3","Q4"], "average"),
    ]
    for label, vals, quarters, agg in agg_configs:
        s = assign_split(i - 1)
        samples.append(make_aggregation(i, s, label, vals, quarters, agg))
        i += 1

    # ── Block 15: Sign errors ─── 35 samples ─────────────────────────────────
    sign_params = [
        ("Loss from discontinued operations",     -156.0,  "million_usd"),
        ("Net loss attributable to shareholders", -151.0,  "million_usd"),
        ("Free cash flow deficit",                -420.0,  "million_usd"),
        ("Operating loss",                        -234.0,  "million_usd"),
        ("Impairment charge on goodwill",         -345.0,  "million_usd"),
        ("Restructuring charge",                  -189.0,  "million_usd"),
        ("Foreign exchange loss",                  -78.0,  "million_usd"),
        ("Derivative loss",                       -112.0,  "million_usd"),
        ("Write-off of intangible assets",        -267.0,  "million_usd"),
        ("Net change in cash (outflow)",          -330.0,  "million_usd"),
        ("Pension obligation increase",           -445.0,  "million_usd"),
        ("Deferred tax liability",                -198.0,  "million_usd"),
        ("Impairment loss on PP&E",               -560.0,  "million_usd"),
        ("Other comprehensive loss",               -89.0,  "million_usd"),
        ("Income tax provision (loss year)",      -320.0,  "million_usd"),
        ("EPS decline",                             -1.23, "usd"),
        ("DPO change (decrease)",                   -6.6,  "unitless"),
        ("Stock price decline from 52-week high", -25.47, "percent"),
        ("Operating cash flow deficit",           -890.0,  "million_usd"),
        ("Capital loss on investments",           -134.0,  "million_usd"),
        ("Warranty reserve increase (net)",       -210.0,  "million_usd"),
        ("Environmental remediation charge",      -175.0,  "million_usd"),
        ("Legal settlement charge",               -320.0,  "million_usd"),
        ("Inventory write-down",                  -145.0,  "million_usd"),
        ("Accounts receivable write-off",          -67.0,  "million_usd"),
        ("Asset retirement obligation",           -230.0,  "million_usd"),
        ("Realized loss on debt extinguishment",  -142.0,  "million_usd"),
        ("Net loss on asset disposal",             -98.0,  "million_usd"),
        ("Deferred revenue decrease",             -180.0,  "million_usd"),
        ("Cumulative translation adjustment",     -312.0,  "million_usd"),
        ("Minority interest loss",                 -56.0,  "million_usd"),
        ("Software impairment",                   -234.0,  "million_usd"),
        ("Goodwill write-down (partial)",         -780.0,  "million_usd"),
        ("Net actuarial loss (pensions)",         -198.0,  "million_usd"),
        ("Loss on equity investments",             -89.0,  "million_usd"),
    ]
    for label, val, unit in sign_params:
        s = assign_split(i - 1)
        samples.append(make_sign_loss(i, s, label, val, unit))
        i += 1

    # ── Block 16: EBITDA margin (scale + aggregation) ─── 15 samples ─────────
    ebitda_params = [
        (34500, 5175, 1380), (78900, 11046, 2367), (22100, 3094, 884),
        (95000, 14250, 3800), (41200, 5768, 1648), (67800, 9762, 2712),
        (18900, 2646, 945),  (112000, 15680, 4480), (38500, 5390, 1540),
        (58000, 8120, 2320), (24700, 3458, 988),   (89000, 12460, 3560),
        (31200, 4368, 1248), (71500, 10010, 2860),  (47000, 6580, 1880),
    ]
    for rev, ebit, da in ebitda_params:
        s = assign_split(i - 1)
        samples.append(make_ebitda_margin(i, s, rev, ebit, da))
        i += 1

    # ── Block 17: Quick Ratio ─── 10 samples ─────────────────────────────────
    qr_params = [
        (3240, 1890, 4560, 9870), (1800, 900, 2400, 5600),
        (4200, 2100, 5800, 12800), (900, 450, 1200, 2800),
        (6100, 3200, 8400, 18000), (2400, 1200, 3200, 7200),
        (1200, 600, 1600, 3600),   (5000, 2500, 6800, 14600),
        (3800, 1900, 5100, 11000), (7200, 3600, 9600, 20800),
    ]
    for cash, sti, ar, cl in qr_params:
        s = assign_split(i - 1)
        samples.append(make_quick_ratio(i, s, cash, sti, ar, cl))
        i += 1

    # ── Block 18: Dividend Yield ─── 10 samples ───────────────────────────────
    dy_params = [
        (3.20, 128.50), (1.80, 89.40), (4.50, 178.20), (0.96, 48.00),
        (2.40, 120.00), (6.00, 240.00), (1.20, 60.00), (3.60, 144.00),
        (0.80, 40.00),  (5.40, 216.00),
    ]
    for div, price in dy_params:
        s = assign_split(i - 1)
        samples.append(make_dividend_yield(i, s, div, price))
        i += 1

    # ── Block 19: Inventory Turnover ─── 10 samples ───────────────────────────
    it_params = [
        (23400, 4680), (14200, 2840), (38900, 5557), (9800, 2450),
        (52000, 6500), (18600, 3100), (7400, 1850), (31200, 5200),
        (12800, 2560), (45600, 5700),
    ]
    for cogs, inv in it_params:
        s = assign_split(i - 1)
        samples.append(make_inventory_turnover(i, s, cogs, inv))
        i += 1

    # ── Block 20: FCF (arithmetic, sign) ─── 15 samples ─────────────────────
    fcf_params = [
        (7800, 2400), (4200, 5100), (12000, 3800), (2900, 3600),
        (9400, 2800), (3600, 4200), (15000, 5000), (5200, 6000),
        (11200, 3400), (6800, 2200), (3200, 3900), (8600, 2600),
        (4400, 5200), (13000, 4100), (7200, 2100),
    ]
    for ocf, capex in fcf_params:
        s = assign_split(i - 1)
        samples.append(make_multi_step_fcf(i, s, ocf, capex))
        i += 1

    # ── Block 21: Net Cash All Activities ─── 10 samples ─────────────────────
    nca_params = [
        (2340, -1890, -780), (4100, -2800, -1200), (1800, -3200, -600),
        (3600, -1500, -900), (5200, -4100, -2000), (2800, -2100, -800),
        (7400, -3800, -1600), (1400, -2600, -500), (4800, -2400, -1100),
        (3200, -5100, -900),
    ]
    for op, inv, fin in nca_params:
        s = assign_split(i - 1)
        samples.append(make_net_cash_all(i, s, op, inv, fin))
        i += 1

    # ── Block 22: Book Value Per Share ─── 10 samples ────────────────────────
    bvps_params = [
        (24600, 480), (15800, 320), (38400, 640), (9200, 200),
        (52000, 800), (21000, 420), (12400, 280), (34800, 600),
        (18600, 360), (46000, 720),
    ]
    for eq, shares in bvps_params:
        s = assign_split(i - 1)
        samples.append(make_book_value_per_share(i, s, eq, shares))
        i += 1

    # ── Block 23: Effective Tax Rate ─── 10 samples ───────────────────────────
    etr_params = [
        (6200, 1426), (3800, 874), (9400, 2162), (2100, 483),
        (12800, 2944), (4600, 1058), (1800, 414), (7600, 1748),
        (3200, 736),  (11000, 2530),
    ]
    for pre_tax, tax in etr_params:
        s = assign_split(i - 1)
        samples.append(make_effective_tax_rate(i, s, pre_tax, tax))
        i += 1

    # ── Block 24: EPS Change ─── 10 samples ───────────────────────────────────
    eps_params = [
        (4.32, 3.87, "2021", "2022"), (2.80, 3.45, "2022", "2023"),
        (6.10, 5.42, "2022", "2023"), (1.90, 2.34, "2021", "2022"),
        (8.20, 7.61, "2022", "2023"), (3.40, 4.08, "2022", "2023"),
        (5.60, 4.90, "2021", "2022"), (2.10, 2.73, "2022", "2023"),
        (7.80, 6.89, "2022", "2023"), (4.00, 4.64, "2022", "2023"),
    ]
    for e1, e2, y1, y2 in eps_params:
        s = assign_split(i - 1)
        samples.append(make_eps_change(i, s, e1, e2, y1, y2))
        i += 1

    # ── Block 25: Segment totals ─── 10 samples ───────────────────────────────
    seg_params = [
        [("Cloud Services", 12.4), ("Enterprise Software", 8.9), ("Consumer Products", 5.2)],
        [("North America", 18.2), ("Europe", 9.4), ("Asia Pacific", 7.8), ("Other", 2.1)],
        [("Hardware", 34.2), ("Software", 28.6), ("Services", 15.8)],
        [("Financial Services", 8.4), ("Healthcare", 6.2), ("Technology", 11.3), ("Energy", 3.8)],
        [("Retail", 22.1), ("Wholesale", 14.6), ("Direct", 9.3)],
        [("Domestic", 41.2), ("International", 28.7)],
        [("Product A", 5.8), ("Product B", 7.2), ("Product C", 4.1), ("Product D", 3.3)],
        [("Upstream", 18.9), ("Midstream", 12.4), ("Downstream", 8.7)],
        [("Consumer", 31.4), ("Enterprise", 24.8), ("Government", 9.2)],
        [("Subscription", 14.6), ("Transaction", 8.9), ("Licensing", 6.3), ("Other", 2.8)],
    ]
    for segs in seg_params:
        s = assign_split(i - 1)
        samples.append(make_segment_total(i, s, segs))
        i += 1

    # ── Block 26: Multi-period sums ─── 10 samples ────────────────────────────
    mp_params = [
        ("Capital Expenditure",  [2021,2022,2023], [1240,1560,1890]),
        ("R&D Expense",          [2021,2022,2023], [2100,2450,2890]),
        ("Free Cash Flow",       [2020,2021,2022,2023], [1800,2400,3200,2750]),
        ("Dividends Paid",       [2020,2021,2022,2023], [900,1000,1100,1200]),
        ("Share Repurchases",    [2021,2022,2023], [2400,3200,2800]),
        ("Capital Expenditure",  [2019,2020,2021,2022,2023], [800,900,1100,1400,1800]),
        ("Depreciation",         [2021,2022,2023], [1400,1600,1800]),
        ("Interest Payments",    [2021,2022,2023], [780,820,860]),
        ("Tax Payments",         [2020,2021,2022,2023], [1200,1400,1600,1800]),
        ("Stock Compensation",   [2021,2022,2023], [1200,1500,1800]),
    ]
    for label, years, vals in mp_params:
        s = assign_split(i - 1)
        samples.append(make_multi_period_sum(i, s, label, years, vals))
        i += 1

    # ── Block 27: Rounding error / CoT drift ─── 10 samples ──────────────────
    re_params = [
        (8452, 9124, "2017", "2018"), (31200, 34800, "2021", "2022"),
        (48900, 52400, "2022", "2023"), (12800, 14200, "2021", "2022"),
        (78400, 84100, "2022", "2023"), (24600, 27300, "2021", "2022"),
        (56200, 61400, "2022", "2023"), (19800, 22100, "2021", "2022"),
        (92000, 98600, "2022", "2023"), (35400, 38900, "2021", "2022"),
    ]
    for r1, r2, y1, y2 in re_params:
        s = assign_split(i - 1)
        samples.append(make_rounding_error(i, s, r1, r2, y1, y2))
        i += 1

    # ── Block 28: Context confusion ─── 5 samples ─────────────────────────────
    for _ in range(5):
        s = assign_split(i - 1)
        samples.append(make_context_confusion(i, s))
        i += 1

    print(f"[Generator] {len(samples)} samples generated (target: 500)")
    return samples


def split_dataset(samples: List[Dict]) -> tuple:
    train = [s for s in samples if s["split"] == "train"]
    dev   = [s for s in samples if s["split"] == "dev"]
    test  = [s for s in samples if s["split"] == "test"]
    return train, dev, test


if __name__ == "__main__":
    import os
    os.makedirs("data/processed", exist_ok=True)

    samples = generate_all()
    train, dev, test = split_dataset(samples)

    print(f"  train={len(train)}  dev={len(dev)}  test={len(test)}  total={len(samples)}")

    for name, split in [("train", train), ("dev", dev), ("test", test)]:
        path = f"data/processed/{name}.json"
        with open(path, "w") as f:
            json.dump(split, f, indent=2)
        print(f"  Wrote {path}")

    with open("data/processed/all.json", "w") as f:
        json.dump(samples, f, indent=2)
    print("  Wrote data/processed/all.json")
