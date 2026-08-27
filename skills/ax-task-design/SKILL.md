---
name: ax-task-design
description: Design controlled coding-agent tasks for measuring developer-tool agent experience.
---

Create a small, realistic task with a frozen starting fixture, explicit allowed
side effects, an independent verifier, and a clear stop condition. Separate the
task prompt from the verifier. Define what the agent may use (raw docs, CLI,
Skill, MCP, or plugin) so surface comparisons are attributable. Prefer
disposable local or test resources; never require production credentials.

Record the fixture hash, prompt, harness/model, repetitions, and human
interventions. Keep the task narrow enough that a failure can be reproduced and
reported to the tool owner.
