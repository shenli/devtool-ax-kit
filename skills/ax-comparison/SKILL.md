---
name: ax-comparison
description: Compare developer-tool surfaces with controlled repeated AX trials and explicit denominators.
---

Inputs: frozen manifest, validated per-trial results and evidence. Use the
[experiment protocol](../../docs/experiment-protocol.md) for design and analysis.

1. Hold task intent, fixture, evaluator, budget and assistance constant. Name raw
   docs/CLI, official Skill, MCP or plugin conditions explicitly; record actual use.
   If information or harness changes too, label the combined comparison.
2. Pair conditions by task/fixture, randomize order using the frozen seed and reset
   state between trials. Stop at the declared limit, not when a preferred result appears.
3. Show per-condition total/valid/unavailable/invalid counts, unknown completion,
   functional and safe completion, claim disagreement, cost, latency and human effort.
   Distinguish cold-start completion from success on configured resources.
4. For inferential claims use the predeclared uncertainty method and independent
   sampling unit. Show small samples and non-reproductions; do not rank noise.
   Keep synthetic calibration separate from agent trials.
5. Attribute using the shared taxonomy, evidence and confidence. A surface
   association alone does not establish a vendor defect. Preserve alternatives.

Deliver the result matrix, denominators, effect estimate/uncertainty when justified,
protocol deviations and evidence links. The built-in protocol validator summarizes
counts only; do not present it as a statistical significance test.
After a proposed improvement, use held-out tasks before claiming general gains.
