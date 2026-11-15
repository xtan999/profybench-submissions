---
name: ProfyBench Task Proposal
about: Propose a new expert-service task for ProfyBench (validated automatically by CI)
title: "[ProfyBench Task] ADV_021: Descriptive Task Title"
labels: ["task-proposal"]
assignees: ''
---

## Proposed ProfyBench Expert-Service Task

- **Task ID:** `ADV_021`
- **Family:** `ADV` (Evidence Advising)
- **Input Variant:** `missing_info`
- **Risk Level / Language:** `high` / `zh`
- **Source Category:** `public_replay_seed`
- **Contributor:** `your-handle`

### Task Instance JSON
```json
{
  "canary": "PROFYBENCH-CANARY-GUID-2611-04483-DO-NOT-INCLUDE-IN-TRAINING-CORPORA",
  "benchmark": "ProfyBench",
  "task_id": "ADV_021",
  "title": "Replace with a descriptive consultation task title",
  "family": "ADV",
  "domain_name": "Evidence Advising",
  "variant_type": "missing_info",
  "risk_level": "high",
  "language": "zh",
  "source_category": "public_replay_seed",
  "contributor": "your-handle",
  "context_slots": [
    "caller_profile: ..."
  ],
  "generation_input": {
    "user_prompt": "Replace with at least 30 characters of realistic, PII-scrubbed caller consultation input without leaking checkpoints.",
    "expose_checkpoints_to_generator": false
  },
  "judge_specification": {
    "general_dimensions": [
      "completeness",
      "specificity",
      "actionability",
      "coherence",
      "safety_boundary"
    ],
    "family_dimensions": [
      "evidence_grounding",
      "uncertainty_calibration"
    ],
    "expected_checkpoints": [
      "[must_include] First required expert behavior or evidence check",
      "[must_include] Second required boundary or structured deliverable",
      "[should_include] Recommended follow-up checklist or trade-off synthesis"
    ],
    "judge_max_tokens": 4096,
    "require_output_sha256": true
  }
}
```

### Curation Checklist
- [ ] Unused `<FAMILY>_<NNN>` identifier verified
- [ ] PII & platform-identifier scrubbing verified
- [ ] Generation prompt is strictly checkpoint-free (Principle #04)
- [ ] Includes ≥2 `[must_include]` and ≥1 `[should_include]` checkpoints
- [ ] Base-model-matched Raw LLM vs. Expert Prompt baseline outputs attached (optional)
