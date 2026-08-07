"""Run intervention ledger generation without opening a gold artifact."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .blind_dvl import BlindInterventionInput, blind_verify
from ..ledger.provenance import jsonl_bytes, write_once


def run(raw_path: str | Path, output_path: str | Path) -> str:
    records = []
    with Path(raw_path).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            result = blind_verify(BlindInterventionInput(
                example_id=str(raw["example_id"]), question=raw["question"],
                context=raw["context"], raw_generation=raw["raw_generation"],
                parsed_prediction=raw.get("parsed_prediction")))
            row = asdict(result)
            row["correction_log"] = [asdict(item) for item in result.correction_log]
            records.append(row)
    return write_once(output_path, jsonl_bytes(records))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(run(args.raw, args.output))


if __name__ == "__main__":
    main()
