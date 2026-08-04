from __future__ import annotations

import hashlib
import json
from pathlib import Path


BENCH_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = BENCH_ROOT / "data" / "verification" / "sources"
OUTPUT_PATH = BENCH_ROOT / "data" / "verification" / "source_manifest.json"

ACQUISITION_COMMIT = "e01860c3380c53d2e1a2bbc20f3356176dcf7084"


ARTIFACT_METADATA = {
    "aapl/aapl_q4_fy2024_earnings_release.html": {
        "source_id": "AAPL-01",
        "company": "Apple Inc.",
        "ticker": "AAPL",
        "reporting_period": "Q4 FY2024",
        "document_type": "earnings_release",
        "source_authority": "Apple Newsroom",
        "provenance_class": "B",
    },
    "aapl/aapl_q4_fy2024_financial_statements.pdf": {
        "source_id": "AAPL-02",
        "company": "Apple Inc.",
        "ticker": "AAPL",
        "reporting_period": "Q4 and FY2024",
        "document_type": "consolidated_financial_statements",
        "source_authority": "Apple",
        "provenance_class": "A",
    },
    "gs/gs_q4_fy2024_earnings_results.html": {
        "source_id": "GS-01",
        "company": "The Goldman Sachs Group, Inc.",
        "ticker": "GS",
        "reporting_period": "Q4 and FY2024",
        "document_type": "earnings_results",
        "source_authority": "Goldman Sachs",
        "provenance_class": "B",
    },
    "gs/gs_q4_fy2024_results_presentation.pdf": {
        "source_id": "GS-02",
        "company": "The Goldman Sachs Group, Inc.",
        "ticker": "GS",
        "reporting_period": "Q4 and FY2024",
        "document_type": "earnings_presentation",
        "source_authority": "Goldman Sachs",
        "provenance_class": "A",
    },
    "jpm/jpm_q4_fy2024_earnings_presentation.pdf": {
        "source_id": "JPM-01",
        "company": "JPMorgan Chase & Co.",
        "ticker": "JPM",
        "reporting_period": "Q4 and FY2024",
        "document_type": "earnings_presentation",
        "source_authority": "JPMorgan Chase & Co.",
        "provenance_class": "A",
    },
    "jpm/jpm_q4_fy2024_earnings_supplement.pdf": {
        "source_id": "JPM-02",
        "company": "JPMorgan Chase & Co.",
        "ticker": "JPM",
        "reporting_period": "Q4 and FY2024",
        "document_type": "earnings_supplement",
        "source_authority": "JPMorgan Chase & Co.",
        "provenance_class": "A",
    },
    "msft/msft_q2_fy2025_earnings_performance.mhtml": {
        "source_id": "MSFT-01",
        "company": "Microsoft Corporation",
        "ticker": "MSFT",
        "reporting_period": "Q2 FY2025",
        "document_type": "earnings_performance",
        "source_authority": "Microsoft Investor Relations",
        "provenance_class": "B",
    },
    "msft/msft_q2_fy2025_earnings_transcript.html": {
        "source_id": "MSFT-02",
        "company": "Microsoft Corporation",
        "ticker": "MSFT",
        "reporting_period": "Q2 FY2025 and Q3 FY2025 outlook",
        "document_type": "earnings_call_transcript",
        "source_authority": "Microsoft Investor Relations",
        "provenance_class": "B",
    },
    "nvda/nvda_q4_fy2025_cfo_commentary.pdf": {
        "source_id": "NVDA-01",
        "company": "NVIDIA Corporation",
        "ticker": "NVDA",
        "reporting_period": "Q4 and FY2025",
        "document_type": "cfo_commentary",
        "source_authority": "NVIDIA Investor Relations",
        "provenance_class": "A",
    },
    "nvda/nvda_q4_fy2025_earnings_release.html": {
        "source_id": "NVDA-02",
        "company": "NVIDIA Corporation",
        "ticker": "NVDA",
        "reporting_period": "Q4 and FY2025",
        "document_type": "earnings_release",
        "source_authority": "NVIDIA Investor Relations",
        "provenance_class": "B",
    },
    "tsla/tsla_fy2024_10k.html": {
        "source_id": "TSLA-01",
        "company": "Tesla, Inc.",
        "ticker": "TSLA",
        "reporting_period": "FY2024",
        "document_type": "form_10_k",
        "source_authority": "SEC EDGAR",
        "provenance_class": "B",
    },
    "tsla/tsla_q4_fy2024_shareholder_update.pdf": {
        "source_id": "TSLA-02",
        "company": "Tesla, Inc.",
        "ticker": "TSLA",
        "reporting_period": "Q4 and FY2024",
        "document_type": "shareholder_update",
        "source_authority": "Tesla Investor Relations",
        "provenance_class": "A",
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def main() -> None:
    actual_files = sorted(
        path
        for path in SOURCE_ROOT.rglob("*")
        if path.is_file()
    )

    actual_relative_paths = {
        path.relative_to(SOURCE_ROOT).as_posix()
        for path in actual_files
    }

    expected_relative_paths = set(ARTIFACT_METADATA)

    missing = sorted(expected_relative_paths - actual_relative_paths)
    extra = sorted(actual_relative_paths - expected_relative_paths)

    if missing or extra:
        raise RuntimeError(
            "Source corpus does not match the expected 12-artifact acquisition.\n"
            f"Missing: {missing}\n"
            f"Extra: {extra}"
        )

    artifacts = []

    for relative_path in sorted(ARTIFACT_METADATA):
        path = SOURCE_ROOT / relative_path
        metadata = ARTIFACT_METADATA[relative_path]

        artifacts.append(
            {
                **metadata,
                "relative_path": f"data/verification/sources/{relative_path}",
                "file_format": path.suffix.lower().lstrip("."),
                "byte_size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    manifest = {
        "manifest_version": "1.0",
        "corpus_name": "FinVerifyBench Verification Primary Source Corpus",
        "acquisition_commit": ACQUISITION_COMMIT,
        "canonical_representation": (
            "Exact tracked source-artifact bytes represented by the repository "
            "after acquisition commit e01860c3380c53d2e1a2bbc20f3356176dcf7084."
        ),
        "artifact_count": len(artifacts),
        "company_count": len({artifact["ticker"] for artifact in artifacts}),
        "hash_algorithm": "SHA-256",
        "provenance_note": (
            "Pre-commit acquisition hashes for text-formatted artifacts differ "
            "from the canonical committed representation, consistent with Git "
            "text normalization during commit. The immutable tracked bytes "
            "represented after the acquisition commit are designated as the "
            "canonical corpus representation for all subsequent experiments. "
            "This statement does not assert that line-ending normalization was "
            "independently proven as the sole cause of the discrepancy."
        ),
        "artifacts": artifacts,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT_PATH.write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(f"Manifest written: {OUTPUT_PATH}")
    print(f"Artifacts: {manifest['artifact_count']}")
    print(f"Companies: {manifest['company_count']}")


if __name__ == "__main__":
    main()