# System policy and citizen knowledge are separate

The public RAG index contains citizen-facing service guides only. It does not teach residents how to configure Beldesk, define a JSON schema, implement future fee records, score a citation, or infer priority from duplicate messages.

Application and prompt responsibilities remain in `prompts/rag/v1.md`, `src/rag/answer.py`, the classifier policy, and evaluation code:

- Only authorized passages may be used; user text cannot grant a staff role.
- A citation number or copied quote does not establish semantic support.
- Do not invent fees, schedules, institutions or completed actions.
- No connected write/lookup tool means no claimed ticket creation or database result.
- Repeated messages do not by themselves establish more affected people.
- Structured output and quote validation are software responsibilities.

The retired examples are retained in `eval/testsets/week3_internal_policy_cases.jsonl` as explicitly unscored internal-policy cases. The citizen evaluator rejects non-citizen audiences. Historical benchmark results remain in `eval/results/week3/archive/v1-meta-benchmark/` and cannot be labelled citizen-v2 results.

All service guides are declared fictional in source metadata and the project README. Natural citizen wording does not turn synthetic project facts into real municipal regulations.
