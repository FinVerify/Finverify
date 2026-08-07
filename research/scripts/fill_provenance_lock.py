"""Populate the pre-execution provenance lock without running experiments.

Only provenance/runtime fields are updated. Scientific protocol fields are
read but never rewritten. The implementation SHA-256 is a deterministic hash
of sorted research ``.py`` and ``.ini`` files, excluding generated caches and
the provenance lock itself.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCK = ROOT / "research" / "protocols" / "PREEXECUTION_PROVENANCE_LOCK.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _implementation_sha256() -> str:
    digest = hashlib.sha256()
    lock = (ROOT / "research" / "protocols" / "PREEXECUTION_PROVENANCE_LOCK.json").resolve()
    files = sorted(
        path for path in (ROOT / "research").rglob("*")
        if path.is_file() and path.suffix in {".py", ".ini"} and path.resolve() != lock
        and "__pycache__" not in path.parts
    )
    for path in files:
        relative = path.relative_to(ROOT).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        data = path.read_bytes()
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def _package_version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return "unavailable"


def _environment() -> dict[str, str]:
    try:
        import torch
        cuda = torch.version.cuda or "none"
        gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none"
        torch_version = torch.__version__
    except Exception:
        cuda, gpu, torch_version = "unavailable", "unavailable", _package_version("torch")
    return {
        "python": platform.python_version(),
        "torch": torch_version,
        "transformers": _package_version("transformers"),
        "peft": _package_version("peft"),
        "bitsandbytes": _package_version("bitsandbytes"),
        "cuda": str(cuda),
        "gpu": str(gpu),
        "platform": platform.platform(),
        "operating_system": platform.system(),
    }


def _load_examples(path: Path) -> list[Mapping[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        examples = payload
    elif isinstance(payload, dict):
        examples = next((payload[key] for key in ("data", "examples", "dev") if isinstance(payload.get(key), list)), None)
        if examples is None:
            raise ValueError(f"dataset JSON does not contain a list split: {path}")
    else:
        raise ValueError(f"dataset JSON must be a list or split object: {path}")
    if not all(isinstance(example, Mapping) for example in examples):
        raise ValueError(f"dataset examples must be objects: {path}")
    return examples


def _counts(path: Path, eligibility) -> tuple[int, int]:
    examples = _load_examples(path)
    return len(examples), sum(1 for example in examples if eligibility(example)[0])


def _git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _require_revision(value: str, label: str) -> None:
    if not value or value.startswith("<"):
        raise ValueError(f"{label} must be supplied as an immutable revision")


def _validate_candidate(payload: Mapping[str, Any], lock_path: Path, dataset: str) -> None:
    if dataset not in {"finqa", "tatqa"}:
        raise ValueError(f"unsupported dataset: {dataset}")
    required = {
        "metadata": ("schema_version",),
        "protocol": ("file", "sha256"),
        dataset: ("repository", "revision", "dev_file", "sha256", "raw_examples", "eligible_examples"),
        "model": ("base_model", "revision", "tokenizer_revision"),
        "adapter": ("repository", "revision"),
        "environment": ("python", "torch", "transformers", "peft", "bitsandbytes", "cuda", "gpu", "platform", "operating_system"),
        "implementation": ("branch", "commit", "implementation_sha256"),
        "execution": ("status", "raw_ledger_generated", "intervention_ledger_generated", "statistics_completed"),
    }
    missing = []
    for section, fields in required.items():
        values = payload.get(section, {})
        for field in fields:
            value = values.get(field)
            if value is None or value == "" or (isinstance(value, str) and value.startswith("<")):
                missing.append(f"{section}.{field}")
    if payload.get("implementation", {}).get("codex_completed") is not True:
        missing.append("implementation.codex_completed")
    if payload.get("execution", {}).get("status") != "PRE_EXECUTION":
        raise ValueError("execution.status must remain PRE_EXECUTION")
    if any(payload.get("execution", {}).get(field) is not False for field in ("raw_ledger_generated", "intervention_ledger_generated", "statistics_completed")):
        raise ValueError("execution flags must remain false before execution")
    digest = str(payload[dataset]["sha256"])
    if not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
        raise ValueError(f"{dataset}.sha256 must be a SHA-256 digest")
    if not isinstance(payload[dataset]["raw_examples"], int) or not isinstance(payload[dataset]["eligible_examples"], int):
        raise ValueError(f"{dataset} example counts must be integers")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", str(payload["implementation"]["implementation_sha256"])):
        raise ValueError("implementation.implementation_sha256 must be a SHA-256 digest")
    protocol_path = lock_path.parent / str(payload["protocol"]["file"])
    if not protocol_path.is_file() or _sha256(protocol_path).lower() != str(payload["protocol"]["sha256"]).lower():
        raise ValueError("protocol file/hash does not match the lock")
    if missing:
        raise ValueError("required provenance fields remain empty: " + ", ".join(missing))


def fill_lock(args: argparse.Namespace) -> dict[str, Any]:
    from research.ledger.generate import finqa_eligible, tatqa_eligible

    lock_path = Path(args.lock).resolve()
    original = json.loads(lock_path.read_text(encoding="utf-8"))
    payload = copy.deepcopy(original)
    if args.dataset == "finqa":
        dataset_file = Path(args.finqa_file).resolve() if args.finqa_file else None
        dataset_repository, dataset_revision = args.finqa_repository, args.finqa_revision
        eligibility = finqa_eligible
    elif args.dataset == "tatqa":
        dataset_file = Path(args.tatqa_file).resolve() if args.tatqa_file else None
        dataset_repository, dataset_revision = args.tatqa_repository, args.tatqa_revision
        eligibility = tatqa_eligible
    else:
        raise ValueError(f"unsupported dataset: {args.dataset}")
    if dataset_file is None or not dataset_file.is_file():
        raise FileNotFoundError(f"{args.dataset} dataset file must exist")
    for value, label in ((dataset_revision, f"{args.dataset} revision"),
                         (args.base_model_revision, "base-model revision"), (args.tokenizer_revision, "tokenizer revision"),
                         (args.adapter_revision, "adapter revision")):
        _require_revision(value, label)
    if not dataset_repository:
        raise ValueError(f"{args.dataset} repository must be supplied")
    implementation_commit = args.implementation_commit or _git_commit()
    if not re.fullmatch(r"[0-9a-fA-F]{40}", implementation_commit):
        raise ValueError("implementation commit must be a 40-character commit SHA")

    payload["metadata"]["frozen"] = False
    raw_count, eligible_count = _counts(dataset_file, eligibility)
    payload[args.dataset].update({"repository": dataset_repository, "revision": dataset_revision,
                                  "dev_file": str(dataset_file), "sha256": _sha256(dataset_file),
                                  "raw_examples": raw_count, "eligible_examples": eligible_count})
    payload["model"]["revision"] = args.base_model_revision
    payload["model"]["tokenizer_revision"] = args.tokenizer_revision
    payload["adapter"]["revision"] = args.adapter_revision
    payload["environment"] = _environment()
    payload["implementation"].update({"commit": implementation_commit, "codex_completed": True,
                                       "implementation_sha256": _implementation_sha256()})

    _validate_candidate(payload, lock_path, args.dataset)
    payload["metadata"]["frozen"] = True
    _validate_candidate(payload, lock_path, args.dataset)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", default=str(DEFAULT_LOCK))
    parser.add_argument("--dataset", required=True, choices=("finqa", "tatqa"))
    parser.add_argument("--finqa-file")
    parser.add_argument("--tatqa-file")
    parser.add_argument("--finqa-repository")
    parser.add_argument("--finqa-revision")
    parser.add_argument("--tatqa-repository")
    parser.add_argument("--tatqa-revision")
    parser.add_argument("--base-model-revision", required=True)
    parser.add_argument("--tokenizer-revision", required=True)
    parser.add_argument("--adapter-revision", required=True)
    parser.add_argument("--implementation-commit")
    args = parser.parse_args()
    payload = fill_lock(args)
    Path(args.lock).write_text(json.dumps(payload, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    print(f"updated {Path(args.lock)}; metadata.frozen=true")


if __name__ == "__main__":
    main()
