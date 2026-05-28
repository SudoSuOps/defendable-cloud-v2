# defendablecloud-cli

`defendable` — drive the DefendableCloud proof vault from your terminal.

Every command maps to an API endpoint locked by Pydantic. The CLI surface IS the doctrine.

> The referee is a rulebook, not a judge. To the shed.

## Install

```bash
pip install defendablecloud-cli
# or, from this monorepo:
pip install -e ./cli
```

After install, the `defendable` binary is on your `PATH`.

## Quickstart — end to end in 6 commands

```bash
# 1. sign in (magic link)
defendable auth login --email you@org.com
# check your inbox, copy the token= value from the URL, then:
defendable auth verify <TOKEN-FROM-EMAIL>

# 2. pick a flight sheet (the declared rulebook)
defendable flight-sheets ls --lane agent

# 3. create a project + a run
defendable projects create --name "IC reviews"
# capture the project id from the output, then:
defendable runs new --project <project-id> --flight-sheet cre_memo_dscr_ltv_v1

# 4. attach evidence + the agent's submission
defendable evidence add <run-id> --kind note --label "deal terms" --content "loan 8.6M ..."
defendable submission add <run-id> --output-file ./agent-output.json --agent claude-code --model claude-opus

# 5. run the rulebook + finalize
defendable audit run <run-id>
defendable audit finalize <run-id>

# 6. approve + generate the receipt + share
defendable approval set <run-id> --decision approved --note "ship it"
defendable receipt generate <run-id>
# the share URL is in the output — anyone can verify it:
defendable verify <share-url-or-token>
```

## Command reference

### Auth

```
defendable auth login --email <email>            request magic-link sign-in
defendable auth verify <token>                   trade token for JWT
defendable auth status                           show signed-in user
defendable auth logout                           forget local credentials
```

### Projects

```
defendable projects ls                           list your org's projects
defendable projects create --name <name>         create a project
```

### Flight Sheets

```
defendable flight-sheets ls [--lane <lane>]      list active flight sheets
defendable flight-sheets show <slug-or-id>       show one + its rules
```

### Runs

```
defendable runs ls [--project <id>] [--limit N]
defendable runs new --project <id> --flight-sheet <slug-or-id>
                    [--agent-profile <id>] [--title <text>]
defendable runs show <run-id>                    full run detail (composite)
defendable runs submission <run-id>              the latest agent submission
defendable runs checks <run-id>                  all applied rules
defendable runs flags <run-id>                   the thrown flags (Findings)
defendable runs verdict <run-id>                 the latest verdict
```

### Evidence

```
defendable evidence add <run-id> --kind <k> --label <l> [--content <text>]
defendable evidence upload <run-id> --file <path> [--label <l>]
```

`kind` ∈ `note · url · observation · tool_output · model_output · log · file`.

### Submission

```
defendable submission add <run-id> --output-file <path>
                                   [--agent <name>] [--model <name>] [--provider <p>]
# or pipe from stdin:
cat output.json | defendable submission add <run-id> --output-text -
```

### Audit · Approval · Receipt

```
defendable audit run <run-id>                    apply the rulebook
defendable audit grade <run-id> <check-id> <pass|flag>     # checklist rules only
defendable audit finalize <run-id>               mint the verdict

defendable approval set <run-id> --decision <approved|rejected|escalated>

defendable receipt generate <run-id>             mint the hash-chained receipt
```

### Ledger

```
defendable ledger ls                             walk the per-org chain
defendable ledger verify                         check hash + parent linkage
```

### Public verify (no auth)

```
defendable verify <share-url-or-token>           hash-check any receipt
```

## Output

Every command prints a rich human-readable view by default; pass `--json` for machine-readable output:

```bash
defendable runs ls --json | jq '.[] | select(.verdict == "fail")'
```

## Configuration

| Setting | How to set |
|---|---|
| API base URL | `--api https://...` flag, or `DEFENDABLE_API` env, or saved profile |
| JWT bearer | `DEFENDABLE_TOKEN` env (overrides saved), or `defendable auth verify` |
| Profile directory | `DEFENDABLE_HOME` env (default `~/.defendable`) |

Credentials are stored at `~/.defendable/credentials.json` with mode 0600.

## Versioning

This CLI is wire-locked against the DefendableCloud API doctrine schemas (`FlightSheet`, `Submission`, `Check`, `Finding`, `Verdict`, `Approval`, `Receipt`, `LedgerEntry`, `Severity`, `RuleSeverity`, `IncidentKind`). A future PR that drops or renames one of those will fail the API's `tests/test_openapi.py` contract test before it ships.

```
defendable --version
```

## Develop

```bash
pip install -e './cli[dev]'
pytest cli/tests              # 19 smoke tests · no creds required
```

### End-to-end test against the live API

`cli/tests/e2e/test_run_lifecycle.py` drives the full Defendable Run lifecycle as a single test:

```
auth status → projects (find-or-create) → flight-sheets ls → runs new
  → evidence add → submission add → audit run → grade open rules
  → audit finalize → runs verdict (assert severity ∈ {honey, jelly, propolis})
  → approval set → receipt generate → verify (hash check) → ledger ls + verify
```

The test SKIPS cleanly if no credentials are available — `pytest cli/tests` is always safe to run.

**To run it against `api.defendablecloud.com`:**

```bash
# Easiest: sign in via the CLI itself, then pytest reads your stored JWT.
defendable auth login --email you@org.com
defendable auth verify <TOKEN-FROM-EMAIL>
pytest cli/tests/e2e -v

# Or supply a JWT directly (CI pattern):
export DEFENDABLE_E2E_TOKEN="eyJ..."
pytest cli/tests/e2e -v

# Override the API base if testing against a non-prod environment:
export DEFENDABLE_E2E_API="https://api.staging.defendablecloud.com"
pytest cli/tests/e2e -v
```

The e2e test uses an isolated `DEFENDABLE_HOME` so it never touches `~/.defendable/credentials.json`. Artifacts (one project, one Run, one receipt per run) accumulate in your org; the API is append-only by design.

---

© 2026 Swarm and Bee LLC · DBA Swarm & Bee AI · `build@defendableos.com` · to the shed.
