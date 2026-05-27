# DefendableCloud Assignment Library v1.0

## Purpose

The Assignment Library is the eval prompt repository for DefendableCloud. It lives between Flight Sheets (the orchestration layer) and Agent Submissions (the work product). Every assignment in this library is designed for deterministic audit: math checks, schema validation, evidence verification, and rule-based referee flags.

**Core doctrine:** DefendableCloud Eval is not AI judging AI. It is agent work tested against a declared rulebook.

The referee has:
- schemas
- required sections
- formulas
- thresholds
- evidence requirements
- citation requirements
- flag rules
- human approval gates

The referee throws flags. The human owns the final trust decision.

## Workflow

```
Flight Sheet
  -> Assignment (from this library)
    -> Agent Prompt (sent to AI agent)
      -> Agent Submission (structured JSON)
        -> Ruleset Audit (deterministic checks)
          -> Referee Flags (honey / jelly / propolis)
            -> Human Approval Gate
              -> Receipt
```

## File Tree

```
assignment-library/
  README.md                          # This file
  assignments.yaml                   # 50 assignments across 10 lanes
  schema.assignment.json             # JSON Schema for assignment validation
  referee_flag_catalog.yaml          # 60+ reusable flags with deterministic checks
  formula_catalog.yaml               # 35+ reusable formulas across domains
  seed_flight_sheet_mapping.yaml     # Maps 5 seeded Flight Sheets to assignments
  examples/
    cre_memo_assignment.yaml         # Example: CRE NOI and Cap Rate
    dataset_quality_assignment.yaml  # Example: Dataset Schema Validation
    compute_benchmark_assignment.yaml# Example: GPU Spec Verification
    document_draft_assignment.yaml   # Example: Document Header Completeness
    general_agent_work_assignment.yaml# Example: Schema Compliance Test
```

## Assignment Structure

Every assignment contains 17 required fields:

| Field | Description |
|-------|-------------|
| `assignment_id` | Unique versioned identifier (e.g., `cre_memo_noi_cap_rate_v1`) |
| `name` | Human-readable name |
| `lane` | Eval lane (one of 10) |
| `version` | Semver version |
| `purpose` | What this assignment tests and why |
| `operator_instructions` | How the human operator runs this eval |
| `agent_prompt` | The prompt sent to the AI agent (enforces structured JSON) |
| `required_inputs` | What inputs the agent needs |
| `expected_outputs` | What outputs the agent must produce |
| `required_output_schema` | JSON Schema the output must conform to |
| `deterministic_checks` | Machine-verifiable checks the referee runs |
| `math_checks` | Formula validation rules (if applicable) |
| `evidence_checks` | Evidence reference validation rules |
| `flag_rules` | Which flags to raise and when |
| `severity_mapping` | honey / jelly / propolis definitions |
| `receipt_type` | Type of receipt generated |
| `recommended_human_review` | required / recommended / optional |
| `sample_submission_shape` | Example of a valid agent submission |

## Lanes (10)

| Lane | Code | Assignments | Description |
|------|------|-------------|-------------|
| General AI Agent Work Eval | A | 5 | Schema, reasoning, instruction following, evidence, errors |
| CRE / Real Estate Memo Eval | B | 8 | NOI, cap rate, DSCR, LTV, cash-on-cash, EGI, equity multiple, rent roll, risk |
| Dataset Quality Eval | C | 7 | Schema, missing values, duplicates, class balance, provenance, train/test, safety |
| Compute Benchmark Eval | D | 7 | GPU specs, benchmark scores, thermal, efficiency, bandwidth, latency, readiness |
| Document Draft Eval | E | 5 | Headers, actions, facts, tone, exhibits |
| Financial / Math Reasoning Eval | F | 5 | Margins, ratios, EBITDA, NPV, WACC, compound interest |
| Evidence Extraction Eval | G | 5 | Entities, numerical facts, claim-evidence pairing, contradictions, temporal |
| Compliance / Policy Checklist Eval | H | 3 | Regulatory, internal policy, data privacy |
| Client Deliverable Readiness Eval | I | 3 | Branding, confidentiality, actionability |
| Repair / Fine-Tune Candidate Eval | J | 2 | Systematic failures, fine-tune ROI |
| **Total** | | **50** | |

## Severity Mapping

The referee classifies every finding into one of three severity levels:

| Severity | Meaning | Action |
|----------|---------|--------|
| **Honey** | No critical flags. All required fields present. All checks passed. | Eligible for human approval. |
| **Jelly** | Non-critical flags exist. Missing optional evidence. Minor math or formatting issues. | Usable with repair. Human review recommended. |
| **Propolis** | Critical field missing. Formula mismatch on material number. Unsupported material claim. Required evidence missing. Schema failure. | **Human approval blocked.** Must be fixed before proceeding. |

## How Flight Sheets Select Assignments

Flight Sheets are defined in `seed_flight_sheet_mapping.yaml`. Each Flight Sheet:

1. Has a unique `flight_sheet_id`
2. Targets one or more lanes
3. Lists specific `assignment_ids` to execute
4. Specifies `execution_mode`: `sequential` or `parallel`
5. Defines `pass_criteria`: severity cap, minimum honey count, propolis tolerance
6. Configures `receipt_config`: receipt type, human review requirement, aggregation method

To run a Flight Sheet:

```python
import yaml

# Load mapping
with open('seed_flight_sheet_mapping.yaml') as f:
    mapping = yaml.safe_load(f)

# Find flight sheet
fs = next(fs for fs in mapping['flight_sheets'] if fs['flight_sheet_id'] == 'fs_cre_memo_v1')

# Load assignments
with open('assignments.yaml') as f:
    library = yaml.safe_load(f)

# Resolve assignment objects
assignments = [
    a for a in library['assignments']
    if a['assignment_id'] in fs['assignment_ids']
]

# Execute (returns agent submissions)
submissions = [execute_assignment(a) for a in assignments]

# Run referee audit
audit_results = referee.audit(submissions, fs['pass_criteria'])

# Human approval gate
if audit_results['max_severity'] != 'propolis':
    receipt = generate_receipt(audit_results, fs['receipt_config'])
```

## How Referee Flags Map to Assignment Outputs

The referee_flag_catalog.yaml contains 60+ reusable flags. Each flag has:

- `flag_id`: Unique identifier (e.g., `schema_failed`)
- `name`: Human-readable description
- `severity`: honey / jelly / propolis
- `description`: When this flag triggers
- `deterministic_check_type`: The type of automated check

Flag types:

| Category | Flags | Check Type |
|----------|-------|------------|
| Schema & Structure | schema_failed, required_field_missing, malformed_json | json_schema_validate, field_presence_check |
| Math & Calculation | material_formula_mismatch, formula_inputs_missing, units_mismatch | formula_reconcile_check, input_presence_check |
| Evidence & Claims | unsupported_material_claim, fabricated_evidence, evidence_reference_invalid | evidence_reference_check, evidence_existence_check |
| Input Disclosure | missing_inputs_not_disclosed, inputs_used_incomplete | missing_input_disclosure_check |
| Assumptions & Risk | assumption_not_labeled, material_risk_omitted | assumption_label_check |
| Self-Check | self_check_false_positive, self_check_missing | self_check_reconcile |
| CRE-Specific | cap_rate_out_of_range, dscr_below_threshold, ltv_above_threshold | range_check, threshold_check |
| Dataset-Specific | duplicate_rate_above_threshold, train_test_leak, hash_manifest_mismatch | threshold_check, overlap_check, hash_verify_check |
| Compute-Specific | thermal_above_threshold, vram_insufficient, benchmark_below_expected | threshold_check, range_check |
| Document-Specific | recipient_missing, requested_action_missing, tone_check_failed | field_presence_check |
| Compliance-Specific | compliance_item_failed, regulatory_reference_missing | checklist_coverage_check |
| Client Deliverable | branding_missing, confidentiality_notice_missing | field_presence_check |
| Repair / Fine-Tune | systematic_bias_detected, repair_candidate_identified | pattern_check |

## Formula Catalog

The `formula_catalog.yaml` contains 35+ reusable formulas organized by domain:

| Domain | Formulas | Examples |
|--------|----------|----------|
| CRE | 10 | noi, cap_rate, dscr, ltv, price_per_unit, cash_on_cash, egi, equity_multiple, irr |
| Finance | 11 | gross_margin, net_margin, roe, roa, current_ratio, quick_ratio, debt_to_equity, ebitda, wacc, npv, compound_interest |
| Compute | 9 | benchmark_score_per_watt, tflops_per_watt, gpu_utilization, memory_bandwidth_utilization, latency_p99, throughput, inference_tokens_per_second |
| Dataset | 5 | duplicate_rate, missing_value_rate, class_balance_ratio, schema_compliance_rate, outlier_rate |
| Cost | 4 | cost_per_token, cost_per_1k_tokens, cost_per_request, token_efficiency |

Each formula includes: variables with types, units, domain, and default tolerances.

## Receipt Types

| Type | Used When | Human Review |
|------|-----------|--------------|
| `eval_receipt` | Standard eval result | Required |
| `audit_receipt` | Multi-lane full audit | Required |
| `repair_receipt` | Repair candidate analysis | Recommended |
| `compliance_receipt` | Compliance checklist eval | Required |

## Integration Notes

### For Vault Operators

1. Import `assignments.yaml` into the vault's assignment registry
2. Import `referee_flag_catalog.yaml` into the flag engine
3. Import `formula_catalog.yaml` into the math validation engine
4. Import `seed_flight_sheet_mapping.yaml` into the Flight Sheet manager
5. Use `schema.assignment.json` to validate any custom assignments before import

### For Agent Developers

1. Your agent will receive an `agent_prompt` from an assignment
2. The prompt requires structured JSON output
3. Follow `required_output_schema` exactly
4. Include all `required_inputs` in `inputs_used` or `missing_inputs`
5. Every claim must have an `evidence_reference`
6. Every calculation must show `formula`, `inputs`, and `result`
7. All assumptions must be labeled in the `assumptions` array
8. Complete `self_check` honestly (false positives are flagged)

### For Human Reviewers

1. The referee runs all `deterministic_checks` automatically
2. Flags are raised per `flag_rules` with severity
3. If any `propolis` flag exists, approval is blocked
4. `jelly` flags require review but may be approved with notes
5. `honey` means all automated checks passed and is eligible for fast approval
6. The receipt records the final decision with all flags and evidence

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-27 | Initial release. 50 assignments across 10 lanes. |

## License

Internal DefendableCloud product component. Not for external distribution.
