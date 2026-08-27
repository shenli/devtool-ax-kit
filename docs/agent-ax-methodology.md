# Agent AX methodology

DevTool AX Kit measures how developer-tool surfaces shape an agent's ability
to complete real work reliably. The unit of study is a controlled task plus its
fixture, agent surface, harness, sandbox, verifier, and human interventions.

## Dimensions

- **Legibility:** can the agent discover relevant instructions, state,
  interfaces, logs, and constraints?
- **Recoverability:** can it identify an ambiguous effect and resume without
  guessing or duplicating a write?
- **Verifiability:** does an independent evaluator agree with the agent's
  success claim, including boundary and restart cases?
- **Attention cost:** how many retries, clarifications, approvals, and manual
  repairs does the workflow require?
- **Safety containment:** are credentials, side effects, and resource scope
  bounded and auditable?

## System model

Keep three layers distinct in reports:

1. **Session:** append-only trajectory, checkpoints, receipts, and replay data.
2. **Harness:** the loop routing model decisions to tools and managing context,
   retries, and verification.
3. **Sandbox:** the workspace and external test resources the agent can touch.

This separation helps distinguish model/task, harness, tool-interface, and
external-infrastructure failures.

## Experimental pattern

Use a generator–evaluator loop: the agent performs a narrowly specified task;
an evaluator outside its editable workspace checks observable behavior. Compare
agent surfaces while holding the fixture, verifier, budget, and task intent
constant. Repeat enough to distinguish a pattern from a one-off.

## External-effect lifecycle

For service-backed tasks, record: `provision → receipt → credential delivery → agent run → independent verify → cleanup`. Classify each trial as `pass`, `functional_fail`, `agent_report_disagrees`, `resource_unavailable`, or `safety_violation`; never count unavailable resources as functional results. Use unique identities and deliberate timing/concurrency trials for boundary-sensitive contracts.

## Further reading

- OpenAI, [Harness engineering](https://openai.com/index/harness-engineering/)
- Anthropic, [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- Anthropic, [Scaling Managed Agents](https://www.anthropic.com/engineering/managed-agents)
- Anthropic, [Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- Anthropic, [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [SWE-chat interaction dataset](https://arxiv.org/abs/2604.20779)
