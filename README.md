# ProfyBench — Community Task Submissions

Official community task proposal & curation repository for **ProfyBench**, an offline expert-service benchmark spanning 5 production consultation families (`ADV`, `EDU`, `MKT`, `MMW`, `PER`) and 3 caller input variants (`complete`, `missing_info`, `adversarial`).

- **Paper:** [CogniLife: Continuous Cognitive Distillation for Deployed Multi-Expert Agent Marketplaces](https://arxiv.org/abs/2611.04483)
- **Live Platform:** [app.profy.cn](https://app.profy.cn/zh/home)

---

## How to Contribute a New Task (如何提交新评测任务)

### Option A — Submit a Pre-Filled Issue (Recommended / 推荐：一键提交 GitHub Issue)
1. Author and validate your task in the **ProfyBench Interactive Task Builder** (`/contribute`), or click **[New Task Proposal Issue](../../issues/new?template=task_proposal.md)** directly in this repository.
2. Ensure all **5 Curation Gates** pass (`<FAMILY>_<NNN>` unused ID, PII scrubbing, structured `[must_include]` / `[should_include]` checkpoints, strict generation–judge checkpoint non-leakage, and family diagnostic dimensions + Canary GUID).
3. Submit the Issue. Our GitHub Actions bot automatically runs `scripts/validate_submission.py` against your JSON block and posts a 5-gate verification report on the Issue.

### Option B — Submit a Pull Request (通过 PR 批量提交 JSON)
1. Place your validated JSON specification(s) under `submissions/<FAMILY>/<TASK_ID>.json` (see [`examples/ADV_021.example.json`](./examples/ADV_021.example.json) and [`schema/profybench-task.schema.json`](./schema/profybench-task.schema.json)).
2. Validate locally with Python 3 (zero external dependencies):
   ```bash
   python3 scripts/validate_submission.py submissions/ADV/ADV_021.json
   ```
3. Open a Pull Request targeting `main`.

---

## ProfyBench 5 Curation Gates (五道质量与反泄漏门禁)

| Gate | Requirement |
| --- | --- |
| **1. Family ID & Uniqueness** | Matches `<FAMILY>_<3 digits>` (`ADV`, `EDU`, `MKT`, `MMW`, `PER`) and does not collide with the 85 core benchmark task IDs (`ADV_001`–`ADV_020`, `EDU_001`–`EDU_020`, `MKT_001`–`MKT_020`, `MMW_001`–`MMW_015`, `PER_001`–`PER_010`). |
| **2. Substance & PII Scrubbing** | `generation_input.user_prompt` contains ≥ 30 characters of realistic consultation context and zero raw personal email addresses or phone numbers. |
| **3. Structured Rubric Checkpoints** | `judge_specification.expected_checkpoints` contains ≥ 2 `[must_include]` and ≥ 1 `[should_include]` items, each with ≥ 8 characters of concrete criteria. |
| **4. Generation–Judge Non-Leakage** | `expose_checkpoints_to_generator` is `false`, and neither checkpoint tags nor verbatim checkpoint descriptions leak into `generation_input.user_prompt`. |
| **5. Family Dimensions & Canary** | Binds the exact 2 diagnostic rubric dimensions for the chosen family plus the anti-contamination Canary GUID (`PROFYBENCH-CANARY-GUID-2611-04483-DO-NOT-INCLUDE-IN-TRAINING-CORPORA`). |

## Family Diagnostic Dimensions

| Family | Domain | Family Rubric Dimensions | Official Core Slots | Next Community ID |
| --- | --- | --- | --- | --- |
| `ADV` | Evidence Advising | `evidence_grounding`, `uncertainty_calibration` | `ADV_001` – `ADV_020` | `ADV_021+` |
| `EDU` | Education | `pedagogical_structure`, `artifact_completeness` | `EDU_001` – `EDU_020` | `EDU_021+` |
| `MKT` | Marketing | `platform_fit`, `audience_specific_rewriting` | `MKT_001` – `MKT_020` | `MKT_021+` |
| `MMW` | Multimodal Workflow | `workflow_decomposition`, `text_image_consistency` | `MMW_001` – `MMW_015` | `MMW_016+` |
| `PER` | Personalization | `style_fidelity`, `long_turn_coherence` | `PER_001` – `PER_010` | `PER_011+` |
