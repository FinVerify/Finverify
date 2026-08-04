from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


BENCH_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = BENCH_ROOT / "data" / "verification" / "sources"
MANIFEST_PATH = BENCH_ROOT / "data" / "verification" / "source_manifest.json"

EXPECTED_ARTIFACTS = 12
EXPECTED_COMPANIES = 6


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)

    return digest.hexdigest()


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def main() -> None:
    if not MANIFEST_PATH.exists():
        fail(f"Manifest does not exist: {MANIFEST_PATH}")

    with MANIFEST_PATH.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    artifacts = manifest.get("artifacts")

    if not isinstance(artifacts, list):
        fail("'artifacts' must be a list")

    if manifest.get("artifact_count") != EXPECTED_ARTIFACTS:
        fail(
            f"Manifest artifact_count is {manifest.get('artifact_count')}; "
            f"expected {EXPECTED_ARTIFACTS}"
        )

    if len(artifacts) != EXPECTED_ARTIFACTS:
        fail(
            f"Manifest contains {len(artifacts)} artifact records; "
            f"expected {EXPECTED_ARTIFACTS}"
        )

    source_ids = [artifact.get("source_id") for artifact in artifacts]
    relative_paths = [artifact.get("relative_path") for artifact in artifacts]
    tickers = {artifact.get("ticker") for artifact in artifacts}

    if len(source_ids) != len(set(source_ids)):
        fail("Duplicate source_id detected")

    if len(relative_paths) != len(set(relative_paths)):
        fail("Duplicate relative_path detected")

    if None in source_ids:
        fail("Artifact missing source_id")

    if None in relative_paths:
        fail("Artifact missing relative_path")

    if None in tickers:
        fail("Artifact missing ticker")

    if manifest.get("company_count") != EXPECTED_COMPANIES:
        fail(
            f"Manifest company_count is {manifest.get('company_count')}; "
            f"expected {EXPECTED_COMPANIES}"
        )

    if len(tickers) != EXPECTED_COMPANIES:
        fail(
            f"Manifest contains {len(tickers)} unique tickers; "
            f"expected {EXPECTED_COMPANIES}"
        )

    if manifest.get("hash_algorithm") != "SHA-256":
        fail("hash_algorithm must be SHA-256")

    actual_source_files = {
        path.relative_to(BENCH_ROOT).as_posix()
        for path in SOURCE_ROOT.rglob("*")
        if path.is_file()
    }

    manifest_source_files = set(relative_paths)

    missing = sorted(manifest_source_files - actual_source_files)
    extra = sorted(actual_source_files - manifest_source_files)

    hash_mismatches = []
    size_mismatches = []

    for artifact in artifacts:
        relative_path = artifact["relative_path"]
        path = BENCH_ROOT / relative_path

        if not path.exists():
            continue

        actual_size = path.stat().st_size
        expected_size = artifact.get("byte_size")

        if actual_size != expected_size:
            size_mismatches.append(
                {
                    "path": relative_path,
                    "expected": expected_size,
                    "actual": actual_size,
                }
            )

        actual_hash = sha256_file(path)
        expected_hash = artifact.get("sha256")

        if actual_hash.lower() != str(expected_hash).lower():
            hash_mismatches.append(
                {
                    "path": relative_path,
                    "expected": expected_hash,
                    "actual": actual_hash,
                }
            )

    print("PHASE 9B SOURCE MANIFEST VALIDATION")
    print("-----------------------------------")
    print(f"Manifest artifacts:     {len(artifacts)}/{EXPECTED_ARTIFACTS}")
    print(f"Companies:              {len(tickers)}/{EXPECTED_COMPANIES}")
    print(f"Missing artifacts:      {len(missing)}")
    print(f"Extra artifacts:        {len(extra)}")
    print(f"Hash mismatches:         {len(hash_mismatches)}")
    print(f"Byte-size mismatches:    {len(size_mismatches)}")

    if missing:
        print("\nMissing:")
        for item in missing:
            print(f"  - {item}")

    if extra:
        print("\nExtra:")
        for item in extra:
            print(f"  - {item}")

    if hash_mismatches:
        print("\nHash mismatches:")
        for item in hash_mismatches:
            print(f"  - {item}")

    if size_mismatches:
        print("\nByte-size mismatches:")
        for item in size_mismatches:
            print(f"  - {item}")

    if missing or extra or hash_mismatches or size_mismatches:
        print("\nFINAL: FAIL")
        sys.exit(1)

    print("\nFINAL: PASS")


if __name__ == "__main__":
    main()