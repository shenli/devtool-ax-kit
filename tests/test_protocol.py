import copy
import json
import unittest
from pathlib import Path

from agent_run.protocol import compatibility_outcome, summarize, validate_document

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"


class ProtocolTest(unittest.TestCase):
    def setUp(self):
        self.experiment = json.loads((ROOT / "taskpacks/databases/experiment.json").read_text())
        self.result = {
            "schema_version": 1, "experiment_id": self.experiment["experiment_id"],
            "run_id": "run-1", "condition_id": "reference-local", "evidence_class": "synthetic",
            "validity": "valid", "completion": "pass", "agent_claim": "none", "safety": "pass",
            "stage": "verify", "reason": "independently verified",
            "attribution": {"layer": "indeterminate", "confidence": "unknown", "evidence": []},
            "assertions": [{"id": "readback", "required": True, "status": "pass",
                            "expected": "one row", "observed": "one row", "evidence": ["receipt:1"]}],
            "metrics": {"elapsed_seconds": 1, "tool_calls": 1, "human_interventions": 0, "cost_usd": None},
            "cleanup": "pass",
        }

    def validate(self, result):
        validate_document(result, "result", SCHEMAS, self.experiment)

    def test_schema_and_success_require_evidence(self):
        validate_document(self.experiment, "experiment", SCHEMAS)
        self.validate(self.result)
        for change in ("missing_evidence", "missing_check", "wrong_completion", "typo"):
            row = copy.deepcopy(self.result)
            if change == "missing_evidence":
                row["assertions"][0]["evidence"] = []
            elif change == "missing_check":
                row["assertions"][0]["status"] = "not_run"
            elif change == "wrong_completion":
                row["completion"] = "fail"
            else:
                row["completon"] = "pass"
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.validate(row)

    def test_onboarding_failure_is_not_removed_from_denominator(self):
        failed = copy.deepcopy(self.result)
        failed.update(run_id="run-2", completion="fail", stage="access", reason="confirmed product barrier")
        failed["assertions"][0].update(status="fail", observed="access denied")
        self.validate(failed)
        unavailable = copy.deepcopy(self.result)
        unavailable.update(run_id="run-3", validity="resource_unavailable", completion="unknown")
        unavailable["assertions"][0].update(status="not_run", observed="evaluator sandbox unavailable", evidence=[])
        self.validate(unavailable)
        report = summarize([self.result, failed, unavailable])["reference-local"]
        self.assertEqual((report["total"], report["valid"], report["resource_unavailable"]), (3, 2, 1))
        self.assertEqual(report["completion_rate"], 0.5)

    def test_unknown_stays_unknown_and_safety_is_orthogonal(self):
        row = copy.deepcopy(self.result)
        row["safety"] = "violation"
        self.validate(row)
        self.assertEqual(compatibility_outcome(row), "safety_violation")
        report = summarize([row])["reference-local"]
        self.assertEqual(report["completed"], 1)
        self.assertEqual(report["safe_completed"], 0)
        row["completion"] = "unknown"
        row["safety"] = "unknown"
        row["assertions"][0]["status"] = "error"
        self.validate(row)
        self.assertEqual(compatibility_outcome(row), "inconclusive")
        self.assertEqual(summarize([row])["reference-local"]["completion_rate"], 0)

    def test_claim_disagreement_and_protocol_guards(self):
        row = copy.deepcopy(self.result)
        row.update(completion="fail", agent_claim="success")
        row["assertions"][0]["status"] = "fail"
        self.validate(row)
        self.assertEqual(compatibility_outcome(row), "agent_report_disagrees")
        with self.assertRaises(ValueError):
            summarize([row, row])
        row["metrics"]["human_interventions"] = 1
        with self.assertRaises(ValueError):
            self.validate(row)
        self.experiment["primary_metric"] = "conditional_functional_success"
        with self.assertRaises(ValueError):
            validate_document(self.experiment, "experiment", SCHEMAS)

    def test_types_and_unknown_conditions_fail_validation(self):
        for key, value in (("cost_usd", float("nan")), ("tool_calls", True)):
            row = copy.deepcopy(self.result)
            row["metrics"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.validate(row)
        row = copy.deepcopy(self.result)
        row["condition_id"] = "not-in-manifest"
        with self.assertRaises(ValueError):
            self.validate(row)

    def test_synthetic_and_live_results_cannot_be_pooled(self):
        row = copy.deepcopy(self.result)
        row.update(run_id="run-2", evidence_class="agent_trial")
        with self.assertRaisesRegex(ValueError, "pool"):
            summarize([self.result, row])
        row["evidence_class"] = "synthetic"
        row["experiment_id"] = "another-experiment"
        with self.assertRaisesRegex(ValueError, "one experiment"):
            summarize([self.result, row])
