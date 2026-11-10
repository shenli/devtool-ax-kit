#!/usr/bin/env python3
"""Validate an experiment and its result files; emit explicit denominators."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent_run.protocol import summarize, validate_document

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path)
    parser.add_argument("results", type=Path, nargs="*")
    args = parser.parse_args()
    try:
        experiment = json.loads(args.experiment.read_text())
        validate_document(experiment, "experiment", ROOT / "schemas")
        results = [json.loads(path.read_text()) for path in args.results]
        for result in results:
            validate_document(result, "result", ROOT / "schemas", experiment)
        print(json.dumps({"status": "pass", "conditions": summarize(results)}, indent=2))
        return 0
    except (ValueError, OSError) as error:
        print(f"protocol: {error}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
