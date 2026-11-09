# Weekly report

<!-- Copy this file to reports/week-N.md in your repository. Keep every heading, in this order.
At most 1,500 words, not counting the scoreboard block and the tables. See section 7 of the handbook.
Write "none this week" instead of deleting a section. -->

| Field | Value |
|---|---|
| Team | |
| Use case | UC_ |
| Week | |
| Repository | |
| Commit tag | week-N |
| Presenter | |
| Members and roles | Name (data and retrieval lead); Name (agent and tools lead); Name (evaluation and safety lead) |

## 1. Summary

<!-- At most 100 words: what changed this week, and the single most important number. -->

## 2. Deliverables

<!-- One row for every deliverable ID of this week (handbook section 4).
Status: done, partial or not done. Evidence: a path in the repository, or a link. -->

| ID | Status | Evidence | Note |
|---|---|---|---|
| W_.1 | | | |
| W_.2 | | | |

## 3. Scoreboard

<!-- Keep every key. Use null for metrics you don't measure yet. Never estimate a number you didn't measure.
Every number must come from a script in the repository, at the commit tagged for this week. -->

```json
{
  "week": 0,
  "test_set_size": null,
  "e2e_accuracy":       {"value": null, "ci95": null, "n": null, "script": null},
  "abstention_correct": {"value": null, "ci95": null, "n": null, "script": null},
  "unsupported_claims": {"value": null, "n": null, "script": null},
  "hit_at_5":           {"value": null, "n": null, "script": null},
  "mrr":                {"value": null, "n": null, "script": null},
  "task_success":       {"value": null, "n": null, "script": null},
  "pass_k":             {"k": null, "value": null, "n": null, "script": null},
  "injection_success":  {"value": null, "n": null, "script": null},
  "cost_per_task_usd":  null,
  "latency_p50_s":      null,
  "spend_week_usd":     null,
  "spend_total_usd":    null
}
```

Changes to any test set this week: none

## 4. Experiments

<!-- One block per experiment. One change per experiment. -->

### Experiment 1: (title)

- **Hypothesis:**
- **Change:**
- **Result:** (numbers, with n and a 95% interval or a paired test)
- **Decision:** (keep, revert, or investigate further)

## 5. Failure analysis

<!-- Your top 3 failures this week. Root cause: prompt, retrieval, generation, tool design, loop, data, security or evaluation. -->

| # | Input (short) | What happened | Root cause | Fix (done or planned) |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

## 6. Response to last week's feedback

<!-- Every point of last week's feedback. Week 1: write "none this week". -->

| Feedback point | What we changed | Evidence |
|---|---|---|
| | | |

## 7. Product track

<!-- Required in weeks 1, 3 and 5 (see handbook section 4). Otherwise write "none this week". -->

## 8. Contributions

<!-- Every member. Commits or files must be checkable in the repository. -->

| Member | Role | What they did this week | Commits or files | Hours |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |

## 9. AI tools used

| Tool | Used for |
|---|---|
| | |

## 10. Next week

| Priority | Metric it should move | Expected change |
|---|---|---|
| 1 | | |
| 2 | | |
| 3 | | |