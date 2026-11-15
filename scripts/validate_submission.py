#!/usr/bin/env python3
"""ProfyBench 5-Gate Task Submission Validator.

Validates standalone task JSON files or extracts the ```json ... ``` specification
from a GitHub Issue Markdown body and enforces all 5 ProfyBench Curation Gates:
  1. Family ID format (<FAMILY>_<NNN>) & non-collision with the 85 core tasks
  2. Prompt substance (>= 30 chars) & email/phone PII scrubbing
  3. Structured rubric checkpoints (>= 2 [must_include] + >= 1 [should_include], >= 8 chars)
  4. Strict generation-judge checkpoint non-leakage
  5. Family diagnostic rubric dimensions & anti-contamination Canary GUID
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

CANARY_STRING = "PROFYBENCH-CANARY-GUID-2611-04483-DO-NOT-INCLUDE-IN-TRAINING-CORPORA"

FAMILY_DIMENSIONS: dict[str, list[str]] = {
    "ADV": ["evidence_grounding", "uncertainty_calibration"],
    "EDU": ["pedagogical_structure", "artifact_completeness"],
    "MKT": ["platform_fit", "audience_specific_rewriting"],
    "MMW": ["workflow_decomposition", "text_image_consistency"],
    "PER": ["style_fidelity", "long_turn_coherence"],
}

CORE_COUNTS: dict[str, int] = {
    "ADV": 20,
    "EDU": 20,
    "MKT": 20,
    "MMW": 15,
    "PER": 10,
}

EXISTING_CORE_IDS: set[str] = {
    f"{fam}_{idx:03d}"
    for fam, count in CORE_COUNTS.items()
    for idx in range(1, count + 1)
}

GENERAL_DIMENSIONS = [
    "completeness",
    "specificity",
    "actionability",
    "coherence",
    "safety_boundary",
]

EMAIL_PII_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_PII_RE = re.compile(
    r"(?:\+?86[-.\s]?)?1[3-9]\d[-.\s]?\d{4}[-.\s]?\d{4}\b|"
    r"(?:\+?1[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]\d{3}[-.\s]\d{4}\b"
)
JSON_FENCE_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def validate_instance(data: dict[str, Any]) -> list[dict[str, Any]]:
    family = str(data.get("family", "")).strip()
    task_id = str(data.get("task_id", "")).strip()
    title = str(data.get("title", "")).strip()

    # Gate 1: Family ID convention & uniqueness
    fam_known = family in FAMILY_DIMENSIONS
    id_format_ok = fam_known and bool(re.match(rf"^{re.escape(family)}_\d{{3}}$", task_id))
    collides = task_id in EXISTING_CORE_IDS
    gate1_ok = id_format_ok and not collides
    suggested_id = f"{family}_{CORE_COUNTS.get(family, 20) + 1:03d}" if fam_known else "ADV_021"
    if gate1_ok:
        gate1_detail = f"Valid unused `{family}` task identifier `{task_id}`."
    elif collides:
        gate1_detail = f"`{task_id}` already exists in the 85-task core benchmark; use `{suggested_id}` or higher."
    else:
        gate1_detail = f"`task_id` must match `<FAMILY>_<3 digits>` for `ADV|EDU|MKT|MMW|PER` (e.g., `{suggested_id}`)."

    # Gate 2: Prompt substance & PII scrubbing
    gen_input = data.get("generation_input") if isinstance(data.get("generation_input"), dict) else {}
    user_prompt = str(gen_input.get("user_prompt", "")).strip()
    has_email = bool(EMAIL_PII_RE.search(user_prompt))
    has_phone = bool(PHONE_PII_RE.search(user_prompt))
    gate2_ok = len(user_prompt) >= 30 and not has_email and not has_phone
    if gate2_ok:
        gate2_detail = f"Prompt length {len(user_prompt)} chars; zero raw email or phone PII patterns detected."
    elif has_email or has_phone:
        gate2_detail = "Detected raw email address or phone number in `generation_input.user_prompt`."
    else:
        gate2_detail = f"`generation_input.user_prompt` has {len(user_prompt)} chars (minimum 30 required)."

    # Gate 3: Structured rubric checkpoints
    judge_spec = data.get("judge_specification") if isinstance(data.get("judge_specification"), dict) else {}
    raw_cps = judge_spec.get("expected_checkpoints")
    checkpoints = [str(c).strip() for c in raw_cps] if isinstance(raw_cps, list) else []
    must_count = sum(1 for c in checkpoints if c.startswith("[must_include]"))
    should_count = sum(1 for c in checkpoints if c.startswith("[should_include]"))
    all_tagged = len(checkpoints) > 0 and all(
        (c.startswith("[must_include]") or c.startswith("[should_include]"))
        and len(re.sub(r"^\[(must_include|should_include)\]\s*", "", c).strip()) >= 8
        for c in checkpoints
    )
    gate3_ok = all_tagged and must_count >= 2 and should_count >= 1
    if gate3_ok:
        gate3_detail = f"Validated {must_count} `[must_include]` and {should_count} `[should_include]` checkpoints."
    else:
        gate3_detail = (
            "Every checkpoint must start with `[must_include]` or `[should_include]` "
            "followed by >= 8 chars (minimum 2 must + 1 should)."
        )

    # Gate 4: Generation-Judge Non-Leakage
    expose_flag = gen_input.get("expose_checkpoints_to_generator")
    prompt_lower = user_prompt.lower()
    tag_leaked = "[must_include]" in prompt_lower or "[should_include]" in prompt_lower
    body_leaked = False
    for cp in checkpoints:
        stripped = re.sub(r"^\[(must_include|should_include)\]\s*", "", cp, flags=re.IGNORECASE).strip().lower()
        if len(stripped) >= 18 and stripped in prompt_lower:
            body_leaked = True
            break
    gate4_ok = (expose_flag is False) and not tag_leaked and not body_leaked
    if gate4_ok:
        gate4_detail = "`expose_checkpoints_to_generator` is `false` and zero checkpoints leaked into `user_prompt`."
    else:
        gate4_detail = (
            "Checkpoint leakage or invalid `expose_checkpoints_to_generator` flag detected in `generation_input`."
        )

    # Gate 5: Family dimensions, schema fields & anti-contamination canary
    expected_fam_dims = FAMILY_DIMENSIONS.get(family, [])
    actual_fam_dims = judge_spec.get("family_dimensions")
    actual_gen_dims = judge_spec.get("general_dimensions")
    canary_ok = data.get("canary") == CANARY_STRING and data.get("benchmark") == "ProfyBench"
    variant_ok = data.get("variant_type") in {"complete", "missing_info", "adversarial"}
    risk_ok = data.get("risk_level") in {"low", "medium", "high"}
    lang_ok = data.get("language") in {"zh", "en"}
    dims_ok = fam_known and actual_fam_dims == expected_fam_dims and actual_gen_dims == GENERAL_DIMENSIONS
    gate5_ok = canary_ok and dims_ok and variant_ok and risk_ok and lang_ok and len(title) >= 6
    if gate5_ok:
        gate5_detail = (
            f"Bound to `{expected_fam_dims[0]}`, `{expected_fam_dims[1]}`, valid metadata, and Canary GUID."
        )
    else:
        gate5_detail = (
            "Mismatch in `canary`, `benchmark`, `title` (>=6 chars), `variant_type`/`risk_level`/`language`, "
            f"or `family_dimensions` (expected {expected_fam_dims})."
        )

    return [
        {"gate": "1. Family ID & Uniqueness", "ok": gate1_ok, "detail": gate1_detail},
        {"gate": "2. Prompt Substance & PII Scrubbing", "ok": gate2_ok, "detail": gate2_detail},
        {"gate": "3. Structured Rubric Checkpoints", "ok": gate3_ok, "detail": gate3_detail},
        {"gate": "4. Generation-Judge Non-Leakage", "ok": gate4_ok, "detail": gate4_detail},
        {"gate": "5. Family Dimensions & Canary GUID", "ok": gate5_ok, "detail": gate5_detail},
    ]


def format_markdown_report(source_label: str, data: dict[str, Any] | None, parse_error: str | None) -> tuple[bool, str]:
    if parse_error or data is None:
        lines = [
            "### ProfyBench Automated Curation Gate Report",
            "",
            "**Status:** ❌ **Needs Revision (JSON Extraction Failed)**",
            "",
            f"> {parse_error}",
            "",
            "Please include a valid ```` ```json ... ``` ```` task instance block generated from the ProfyBench Task Builder.",
        ]
        return False, "\n".join(lines)

    checks = validate_instance(data)
    passed_count = sum(1 for c in checks if c["ok"])
    all_ok = passed_count == len(checks)
    status_badge = (
        f"✅ **All {len(checks)}/{len(checks)} Curation Gates Passed**"
        if all_ok
        else f"⚠️ **{passed_count}/{len(checks)} Curation Gates Passed — Revision Needed**"
    )

    lines = [
        "### ProfyBench Automated Curation Gate Report",
        "",
        f"**Status:** {status_badge}",
        f"- **Source:** `{source_label}`",
        f"- **Task ID / Family / Variant:** `{data.get('task_id', 'N/A')}` · `{data.get('family', 'N/A')}` · `{data.get('variant_type', 'N/A')}`",
        "",
        "| Gate | Result | Diagnostic Detail |",
        "| --- | --- | --- |",
    ]
    for chk in checks:
        icon = "✅ Pass" if chk["ok"] else "❌ Fail"
        lines.append(f"| {chk['gate']} | {icon} | {chk['detail']} |")

    return all_ok, "\n".join(lines)


def validate_issue_body(body: str) -> tuple[bool, str]:
    match = JSON_FENCE_RE.search(body or "")
    if not match:
        return format_markdown_report(
            "GitHub Issue Body",
            None,
            "No ```json ... ``` fenced block was found in the issue body.",
        )
    raw_json = match.group(1)
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        return format_markdown_report(
            "GitHub Issue Body",
            None,
            f"Invalid JSON syntax inside ```json``` block: {exc}",
        )
    if not isinstance(parsed, dict):
        return format_markdown_report("GitHub Issue Body", None, "Top-level JSON value must be an object.")
    return format_markdown_report("GitHub Issue Proposal", parsed, None)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ProfyBench task JSON files or Issue bodies.")
    parser.add_argument("files", nargs="*", help="JSON file paths to validate")
    parser.add_argument(
        "--from-issue-env",
        action="store_true",
        help="Read GitHub Issue body from the ISSUE_BODY environment variable",
    )
    parser.add_argument("--markdown-out", help="Optional path to write Markdown validation report")
    args = parser.parse_args()

    if args.from_issue_env:
        body = os.environ.get("ISSUE_BODY", "")
        ok, report = validate_issue_body(body)
        print(report)
        if args.markdown_out:
            Path(args.markdown_out).write_text(report + "\n", encoding="utf-8")
        return 0 if ok else 1

    if not args.files:
        parser.error("Provide one or more JSON files or pass --from-issue-env.")

    overall_ok = True
    reports: list[str] = []
    for file_arg in args.files:
        path = Path(file_arg)
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
            ok, report = format_markdown_report(str(path), parsed, None)
        except Exception as exc:  # noqa: BLE001
            ok, report = format_markdown_report(str(path), None, str(exc))
        overall_ok = overall_ok and ok
        reports.append(report)

    combined = "\n\n---\n\n".join(reports)
    print(combined)
    if args.markdown_out:
        Path(args.markdown_out).write_text(combined + "\n", encoding="utf-8")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
