"""
Imports real test cases from CSV or JSON into the golden dataset schema,
replacing the "demo data only" limitation. Validates every row against
the same TestCase model the eval engine uses, so a malformed import fails
loudly at import time rather than silently at eval time.

CSV columns expected (header row required):
    id, input, expected_category, expected_summary, expected_difficulty, notes

JSON expected shape: either the full {"cases": [...]} golden-dataset shape,
or a bare list of case objects with the same fields as the CSV columns.

Usage:
    python -m src.dataset_importer --file my_cases.csv --output golden_dataset/dataset_v2.json
    python -m src.dataset_importer --file my_cases.json --output golden_dataset/dataset_v2.json --merge golden_dataset/dataset_v1.json
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from src.models import TestCase


class DatasetImportError(Exception):
    pass


def _rows_from_csv(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def _rows_from_json(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "cases" in data:
        return data["cases"]
    if isinstance(data, list):
        return data
    raise DatasetImportError(
        "JSON input must be either a bare list of case objects or "
        '{"cases": [...]} matching the golden dataset shape.'
    )


def parse_cases(path: str | Path) -> list[TestCase]:
    path = Path(path)
    if not path.exists():
        raise DatasetImportError(f"File not found: {path}")

    if path.suffix.lower() == ".csv":
        raw_rows = _rows_from_csv(path)
    elif path.suffix.lower() == ".json":
        raw_rows = _rows_from_json(path)
    else:
        raise DatasetImportError(f"Unsupported file type '{path.suffix}' — use .csv or .json")

    cases: list[TestCase] = []
    errors: list[str] = []
    seen_ids: set[str] = set()

    for i, row in enumerate(raw_rows, start=1):
        row = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
        row.setdefault("notes", "")
        row.setdefault("expected_difficulty", "medium")
        try:
            case = TestCase(**row)
        except ValidationError as e:
            errors.append(f"Row {i} (id={row.get('id', '?')}): {e.errors()[0]['msg']}")
            continue

        if case.id in seen_ids:
            errors.append(f"Row {i}: duplicate case id '{case.id}'")
            continue
        seen_ids.add(case.id)
        cases.append(case)

    if errors:
        raise DatasetImportError(
            f"{len(errors)} row(s) failed validation:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    return cases


def import_dataset(input_path: str | Path, output_path: str | Path,
                    merge_with: str | Path | None = None, dataset_version: str = "imported") -> dict:
    """Parses + validates the input file, optionally merges with an
    existing dataset (new cases appended, duplicate IDs from the new file
    win), and writes the result. Returns a summary dict for the caller
    (CLI or API) to report back."""
    new_cases = parse_cases(input_path)

    if merge_with:
        existing_path = Path(merge_with)
        if not existing_path.exists():
            raise DatasetImportError(f"Merge target not found: {existing_path}")
        with open(existing_path, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
        existing_cases = [TestCase(**c) for c in existing_data["cases"]]
        by_id = {c.id: c for c in existing_cases}
        added, updated = 0, 0
        for c in new_cases:
            if c.id in by_id:
                updated += 1
            else:
                added += 1
            by_id[c.id] = c
        final_cases = list(by_id.values())
    else:
        final_cases = new_cases
        added, updated = len(new_cases), 0

    output = {
        "dataset_version": dataset_version,
        "created": "imported",
        "notes": f"Imported from {Path(input_path).name}" + (f", merged with {Path(merge_with).name}" if merge_with else ""),
        "cases": [json.loads(c.model_dump_json()) for c in final_cases],
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    return {
        "output_path": str(output_path),
        "total_cases": len(final_cases),
        "added": added,
        "updated": updated,
    }


def main():
    parser = argparse.ArgumentParser(description="Import a golden dataset from CSV or JSON")
    parser.add_argument("--file", required=True, help="Path to the CSV or JSON file to import")
    parser.add_argument("--output", required=True, help="Where to write the resulting golden dataset JSON")
    parser.add_argument("--merge", default=None, help="Optional existing dataset JSON to merge into")
    parser.add_argument("--version", default="imported", help="dataset_version label to write")
    args = parser.parse_args()

    try:
        summary = import_dataset(args.file, args.output, merge_with=args.merge, dataset_version=args.version)
    except DatasetImportError as e:
        print(f"[dataset_importer] FAILED: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[dataset_importer] Wrote {summary['total_cases']} cases to {summary['output_path']} "
          f"({summary['added']} added, {summary['updated']} updated).")


if __name__ == "__main__":
    main()
