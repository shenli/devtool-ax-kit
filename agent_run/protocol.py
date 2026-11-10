"""Validation for this repository's JSON Schema subset and trial semantics.

Not a general JSON Schema implementation. Unknown schema keywords fail closed.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any


def validate(value: Any, schema: dict, path: str = "$") -> None:
    supported = {"$schema", "title", "description", "type", "properties", "required",
                 "additionalProperties", "items", "minItems", "minLength", "minimum",
                 "pattern", "enum", "const"}
    if set(schema) - supported:
        raise ValueError(f"{path}: unsupported schema keywords")
    types = {"object": lambda x: isinstance(x, dict),
             "array": lambda x: isinstance(x, list),
             "string": lambda x: isinstance(x, str),
             "integer": lambda x: type(x) is int,
             "number": lambda x: type(x) in (int, float) and math.isfinite(x),
             "boolean": lambda x: type(x) is bool,
             "null": lambda x: x is None}
    expected = schema.get("type")
    if expected is not None:
        expected = expected if isinstance(expected, list) else [expected]
        if not any(types[t](value) for t in expected):
            raise ValueError(f"{path}: wrong type")
    if "const" in schema and (type(value) is not type(schema["const"]) or value != schema["const"]):
        raise ValueError(f"{path}: wrong constant")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path}: unknown enum value")
    if isinstance(value, dict):
        if set(schema.get("required", [])) - value.keys():
            raise ValueError(f"{path}: missing required fields")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False and value.keys() - properties.keys():
            raise ValueError(f"{path}: unknown fields")
        for key, item in value.items():
            if key in properties:
                validate(item, properties[key], f"{path}.{key}")
    elif isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise ValueError(f"{path}: too few items")
        for index, item in enumerate(value):
            if "items" in schema:
                validate(item, schema["items"], f"{path}[{index}]")
    elif isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or not value.strip():
            raise ValueError(f"{path}: empty string")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            raise ValueError(f"{path}: pattern mismatch")
    elif type(value) in (int, float):
        if not math.isfinite(value) or value < schema.get("minimum", -math.inf):
            raise ValueError(f"{path}: out of range")


def validate_document(document: dict, kind: str, schema_root: Path,
                      experiment: dict | None = None) -> None:
    if kind not in {"experiment", "result"}:
        raise ValueError("unknown document kind")
    validate(document, json.loads((schema_root / f"{kind}.schema.json").read_text()))
    if kind == "experiment":
        ids = [c["id"] for c in document["conditions"]]
        if len(ids) != len(set(ids)):
            raise ValueError("condition identities must be unique")
        if document["track"] == "cold_start" and document["primary_metric"] != "end_to_end_completion":
            raise ValueError("cold-start experiments must include onboarding in the primary denominator")
        return
    checks = [a for a in document["assertions"] if a["required"]]
    ids = [a["id"] for a in document["assertions"]]
    if not checks or len(ids) != len(set(ids)):
        raise ValueError("require unique assertions and at least one required assertion")
    statuses = [a["status"] for a in checks]
    expected = "fail" if "fail" in statuses else ("pass" if all(s == "pass" for s in statuses) else "unknown")
    if document["completion"] != expected:
        raise ValueError("completion disagrees with required assertions")
    if document["validity"] != "valid" and document["completion"] != "unknown":
        raise ValueError("excluded trials cannot supply functional outcomes")
    for check in document["assertions"]:
        if check["status"] in {"pass", "fail"} and not check["evidence"]:
            raise ValueError("observed assertion outcomes require evidence references")
    if document["attribution"]["confidence"] != "unknown" and not document["attribution"]["evidence"]:
        raise ValueError("attribution requires evidence")
    if experiment is not None:
        if document["experiment_id"] != experiment["experiment_id"]:
            raise ValueError("experiment identity mismatch")
        if document["condition_id"] not in {c["id"] for c in experiment["conditions"]}:
            raise ValueError("unknown condition")
        if document["metrics"]["human_interventions"] > experiment["human_assistance"]["max_interventions"]:
            raise ValueError("assistance budget exceeded; retain as protocol deviation outside this comparison")


def compatibility_outcome(result: dict) -> str:
    if result["safety"] == "violation":
        return "safety_violation"
    if result["validity"] == "resource_unavailable":
        return "resource_unavailable"
    if result["validity"] != "valid" or result["completion"] == "unknown":
        return "inconclusive"
    if result["completion"] == "fail":
        return "agent_report_disagrees" if result["agent_claim"] == "success" else "functional_fail"
    return "pass" if result["safety"] == "pass" else "inconclusive"


def summarize(results: list[dict]) -> dict:
    """Explicit per-condition denominators; unknown completion is not a success."""
    if len({r["experiment_id"] for r in results}) > 1:
        raise ValueError("summarize one experiment at a time")
    if len({r["evidence_class"] for r in results}) > 1:
        raise ValueError("do not pool synthetic calibration with agent trials")
    seen = set()
    groups: dict[str, list[dict]] = {}
    for result in results:
        identity = (result["experiment_id"], result["run_id"])
        if identity in seen:
            raise ValueError("duplicate run identity")
        seen.add(identity)
        groups.setdefault(result["condition_id"], []).append(result)
    report = {}
    for condition, rows in groups.items():
        valid = [r for r in rows if r["validity"] == "valid"]
        passed = sum(r["completion"] == "pass" for r in valid)
        report[condition] = {
            "total": len(rows), "valid": len(valid),
            "resource_unavailable": sum(r["validity"] == "resource_unavailable" for r in rows),
            "invalid": sum(r["validity"] == "invalid" for r in rows),
            "completed": passed,
            "unknown_completion": sum(r["completion"] == "unknown" for r in valid),
            "completion_rate": passed / len(valid) if valid else None,
            "safe_completed": sum(compatibility_outcome(r) == "pass" for r in valid),
            "safety_violations": sum(r["safety"] == "violation" for r in rows),
            "claim_disagreements": sum(r["agent_claim"] == "success" and r["completion"] == "fail" for r in rows),
            "evidence_classes": sorted({r["evidence_class"] for r in rows}),
        }
    return report
